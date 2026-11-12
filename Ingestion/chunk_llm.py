"""LLM-based splitting for text chunks that exceed MAX_CHARS after rechunking.

Uses Gemma via OpenRouter (same provider as deepseek_client.py).
The LLM must return the text VERBATIM, split only at natural sentence/paragraph
boundaries. Downstream verify_and_fix() rejects any output that modifies content.
"""
from __future__ import annotations
import logging
from openai import OpenAI

from Ingestion.chunk_text import MAX_CHARS

logger    = logging.getLogger(__name__)
MODEL     = "google/gemma-4-31b-it"
SEPARATOR = "---CHUNK---"
BASE_URL  = "https://openrouter.ai/api/v1"

_PROVIDER_PREFS = {
    "sort":          "price",
    "quantizations": ["int8", "fp8", "fp16", "bf16"],
}


def _build_prompt(text: str, heading_path: str) -> str:
    return (
        "Du erhältst einen Textabschnitt aus einem deutschen Jahresabschluss-Dokument.\n"
        f"Kontext: {heading_path or '(ohne Überschrift)'}\n\n"
        f"Teile den Text an natürlichen Satz- oder Absatzgrenzen so auf, "
        f"dass jeder Teil höchstens {MAX_CHARS} Zeichen hat.\n\n"
        "STRIKTE REGELN:\n"
        "1. Gib den Text WORTGETREU zurück – ändere NICHTS, keine Zusammenfassungen.\n"
        "2. Trenne NUR an Satz- oder Absatzgrenzen – NIEMALS mitten in einem Satz.\n"
        f"3. Trenne die Teile mit dieser Zeichenkette auf einer eigenen Zeile:\n"
        f"{SEPARATOR}\n"
        "4. Gib NUR den Inhalt zurück – keine Erklärungen oder Kommentare.\n\n"
        f"Aufzuteilender Text ({len(text)} Zeichen):\n---\n{text}\n---"
    )


def _parse(response: str, original: dict) -> list[dict]:
    parts = [p.strip() for p in response.split(SEPARATOR) if p.strip()]
    if not parts:
        logger.warning("LLM: leere Antwort – Original bleibt (%d chars)", len(original['text']))
        return [original]
    return [
        {
            'heading_path':  original['heading_path'],
            'char_start':    original['char_start'],
            'char_end':      original['char_end'],
            'text':          part,
            'is_table':      False,
            '_llm_produced': True,
        }
        for part in parts
    ]


def split_overlong_chunk(chunk: dict, api_key: str) -> list[dict]:
    """
    Call LLM to split a text chunk >MAX_CHARS at sentence/paragraph boundaries.
    Returns sub-chunks with _llm_produced=True for downstream verification.
    Falls back to the original chunk on API error.
    """
    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    prompt = _build_prompt(chunk['text'], chunk.get('heading_path', ''))

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            extra_body={"provider": _PROVIDER_PREFS},
        )
        text = resp.choices[0].message.content or ""
        logger.info("LLM split: %d → %d chars output for chunk @%d:%d",
                    len(chunk['text']), len(text),
                    chunk['char_start'], chunk['char_end'])
        return _parse(text, chunk)
    except Exception as exc:
        logger.error("LLM-Aufruf fehlgeschlagen (%s) – Original bleibt", exc)
        return [chunk]
