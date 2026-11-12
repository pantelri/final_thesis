from __future__ import annotations

import json
import logging
import os
import re

from openai import OpenAI

logger = logging.getLogger(__name__)

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
_DEFAULT_MODEL       = "qwen/qwen3-max"

_ENV_MODEL      = "REVIEW_LLM_MODEL"
_ENV_BASE_URL   = "REVIEW_LLM_BASE_URL"
_ENV_API_KEY    = "REVIEW_LLM_API_KEY"
_ENV_MAX_ROUNDS = "REVIEW_MAX_ROUNDS"
_DEFAULT_MAX_ROUNDS = 5


class ReviewLLMError(Exception):
    """Raised when the Review LLM returns an unparseable or invalid response."""


def get_llm_config() -> tuple[str, str, str, int]:
    """Return (model, base_url, api_key, max_rounds) from env, with safe defaults."""
    model     = os.environ.get(_ENV_MODEL)    or _DEFAULT_MODEL
    base_url  = os.environ.get(_ENV_BASE_URL) or _OPENROUTER_BASE_URL
    api_key   = os.environ.get(_ENV_API_KEY)  or os.environ.get("OPENROUTER_API_KEY", "")
    max_rounds = int(os.environ.get(_ENV_MAX_ROUNDS, _DEFAULT_MAX_ROUNDS))
    return model, base_url, api_key, max_rounds


def build_review_prompt(
    query:       str,
    round_num:   int,
    history:     list[str],
    span_text:   str,
    n_remaining: int,
) -> str:
    history_text = (
        "\n".join(f"  {h}" for h in history)
        if history else "  (keine bisherigen Aktionen)"
    )
    return (
        f"== Runde {round_num} ==\n\n"
        f"Compliance-Anfrage: {query}\n\n"
        f"Aktionsverlauf:\n{history_text}\n\n"
        f"Aktueller Textabschnitt ({len(span_text)} Zeichen):\n"
        f"---\n{span_text}\n---\n\n"
        f"Warteschlange: {n_remaining} weitere Ergebnis(se) verfügbar.\n\n"
        "Wähle genau eine Aktion:\n"
        '- "add_next_result"           → nächstes Retrievalergebnis an den Abschnitt anhängen\n'
        '- "trim_incomplete_sentence"  → unvollständiges Satzfragment am "start" oder "end" entfernen '
        '(ergänze "trim_position": "start"|"end")\n'
        '- "remove_sentence"           → exakten Satz entfernen '
        '(ergänze "sentence_to_remove": "<exakter Text>")\n'
        '- "expand_neighbor"           → benachbarten Chunk im selben Dokument laden '
        '(ergänze "direction": "previous"|"next")\n'
        '- "finalize"                  → Abschnitt beantwortet die Anfrage ausreichend\n\n'
        "Antworte ausschließlich mit JSON:\n"
        '{"action": "...", "reasoning": "...", '
        '/* nur aktionsspezifische Felder ergänzen */ }'
    )


def call_review_llm(model: str, base_url: str, api_key: str, prompt: str) -> dict:
    """Send *prompt* to the Review LLM and return the parsed JSON response.

    Raises:
        ReviewLLMError: If api_key is missing, response is empty, or JSON is invalid.
    """
    if not api_key:
        raise ReviewLLMError(
            "LLM nicht konfiguriert. Bitte OPENROUTER_API_KEY setzen."
        )

    client = OpenAI(api_key=api_key, base_url=base_url)

    system_msg = (
        "Du bist ein präziser Textverfeinerungs-Assistent für die Prüfung von HGB-Offenlegungspflichten. "
        "Deine einzige Aufgabe ist es, zu entscheiden, wie ein Textabschnitt aus einem deutschen "
        "Jahresabschluss verfeinert werden soll.\n"
        "WICHTIG: Antworte ausschließlich mit einem gültigen JSON-Objekt. "
        "Kein Fließtext, keine Markdown-Blöcke, keine Erklärungen außerhalb des JSON."
    )

    response = client.chat.completions.create(
        model    = model,
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    raw = (response.choices[0].message.content or "").strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$",          "", raw)

    if not raw:
        raise ReviewLLMError("Leere Antwort vom Review-LLM.")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Review-LLM – unparsierbare Antwort: %s", raw[:500])
        raise ReviewLLMError(f"JSON-Parsing fehlgeschlagen: {exc}") from exc
