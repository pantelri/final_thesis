"""
LLM-backed passage suggestions for the "text too short" annotation flow.

Sends the annotator's free-text note about what is missing, the passage shown
so far, and the FULL markdown of the annual report to an OpenRouter model
(Kimi K3 by default) and returns candidate passages the annotator can choose from.

Configuration via environment (see .env.example):
  OPENROUTER_API_KEY   – required; OpenRouter API key
  SUGGEST_LLM_MODEL    – OpenRouter model slug (default: moonshotai/kimi-k3)
  SUGGEST_LLM_BASE_URL – default https://openrouter.ai/api/v1
  MD_DIR               – default /data/Output/md_files
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import httpx

_DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
# Default since 2026-11-11 (author decision); override via SUGGEST_LLM_MODEL in .env.
_DEFAULT_MODEL = "moonshotai/kimi-k3"
_DEFAULT_MD_DIR = "/data/Output/md_files"
_TIMEOUT_S = 240.0   # reasoning model + full report can take > 2 min


class SuggestError(Exception):
    """Raised when suggestions cannot be obtained (config, network, or parsing)."""


def get_suggest_config() -> tuple[str, str, str]:
    """Return (model, base_url, api_key) from env, with safe defaults."""
    model = os.environ.get("SUGGEST_LLM_MODEL") or _DEFAULT_MODEL
    base_url = os.environ.get("SUGGEST_LLM_BASE_URL") or _DEFAULT_BASE_URL
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    return model, base_url, api_key


def load_md(company_id: str) -> str:
    """Read the full markdown of a company's annual report."""
    md_dir = Path(os.environ.get("MD_DIR") or _DEFAULT_MD_DIR)
    md_path = md_dir / f"{company_id}.md"
    if not md_path.exists():
        raise SuggestError(f"Markdown-Datei nicht gefunden: {md_path}")
    return md_path.read_text(encoding="utf-8")


def build_prompt(missing_text: str, shown_text: str, md_text: str) -> str:
    return (
        "Der Prüfer bearbeitet einen deutschen Jahresabschluss (HGB) und hält den ihm "
        "angezeigten Textabschnitt für ZU KURZ.\n\n"
        f"Was dem Prüfer noch fehlt (Freitext):\n---\n{missing_text}\n---\n\n"
        f"Bisher angezeigter Abschnitt:\n---\n{shown_text}\n---\n\n"
        f"Vollständiger Jahresabschluss (Markdown):\n---\n{md_text}\n---\n\n"
        "Aufgabe: Finde im vollständigen Jahresabschluss die passenden Textstellen "
        "(Absätze, Tabellen oder Erklärungen), die die fehlenden Informationen enthalten. "
        "Gib jede Fundstelle möglichst wörtlich wieder.\n\n"
        "Antworte AUSSCHLIESSLICH mit gültigem JSON in genau dieser Form:\n"
        '{"suggestions": [{"text": "<wörtliche Textstelle>", '
        '"source": "<Überschrift/Abschnitt/Seite, falls erkennbar>", '
        '"reason": "<kurze Begründung, warum passend>"}]}\n'
        "Wenn nichts Passendes gefunden wird, gib eine leere Liste zurück. "
        "Kein Fließtext, keine Markdown-Codeblöcke außerhalb des JSON."
    )


def _parse(raw: str) -> list[dict]:
    raw = (raw or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    if not raw:
        raise SuggestError("Leere Antwort vom LLM.")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SuggestError(f"JSON-Parsing fehlgeschlagen: {exc}") from exc
    suggestions = data.get("suggestions", []) if isinstance(data, dict) else []
    # Keep only well-formed entries with non-empty text.
    return [
        {
            "text": str(s.get("text", "")).strip(),
            "source": str(s.get("source", "")).strip(),
            "reason": str(s.get("reason", "")).strip(),
        }
        for s in suggestions
        if isinstance(s, dict) and str(s.get("text", "")).strip()
    ]


def request_suggestions(missing_text: str, shown_text: str, company_id: str) -> list[dict]:
    """Blocking call to OpenRouter. Run via nicegui.run.io_bound from handlers."""
    model, base_url, api_key = get_suggest_config()
    if not api_key:
        raise SuggestError("LLM nicht konfiguriert. Bitte OPENROUTER_API_KEY setzen.")

    md_text = load_md(company_id)
    prompt = build_prompt(missing_text, shown_text, md_text)

    system_msg = (
        "Du bist ein präziser Assistent für die Prüfung von HGB-Offenlegungspflichten. "
        "Du findest passende Textstellen in einem Jahresabschluss und gibst sie wörtlich "
        "als JSON zurück. Kein Fließtext, kein Markdown außerhalb des JSON."
    )

    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=_TIMEOUT_S,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise SuggestError(
            f"LLM-Anfrage fehlgeschlagen ({exc.response.status_code}): "
            f"{exc.response.text[:300]}"
        ) from exc
    except httpx.HTTPError as exc:
        raise SuggestError(f"Netzwerkfehler bei LLM-Anfrage: {exc}") from exc

    try:
        content = resp.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, ValueError) as exc:
        raise SuggestError(f"Unerwartetes Antwortformat vom LLM: {exc}") from exc

    return _parse(content)
