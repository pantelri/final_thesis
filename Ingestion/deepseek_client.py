"""
deepseek_client.py

Wrapper für die OpenRouter API (OpenAI-kompatibel).
Teilt einen langen Markdown-Chunk per LLM in kleinere Sub-Chunks auf.

Modell     : google/gemma-4-31b-it
Quantisier.: min. 8-Bit  (int8 / fp8 / fp16 / bf16)
Priorität  : Preis (günstigster verfügbarer Provider)
SDK        : openai (OpenAI-kompatibler Endpunkt)
Schlüssel  : OPENROUTER_API_KEY (Umgebungsvariable, wird von außen übergeben)
"""

import logging
from openai import OpenAI

logger    = logging.getLogger(__name__)
MODEL     = "google/gemma-4-31b-it"
SEPARATOR = "---CHUNK---"
BASE_URL  = "https://openrouter.ai/api/v1"

# OpenRouter Provider-Präferenzen:
#   sort="price"         → günstigster Provider zuerst
#   quantizations        → nur min. 8-Bit erlaubt (kein int4/fp4)
_PROVIDER_PREFS = {
    "sort": "price",
    "quantizations": ["int8", "fp8", "fp16", "bf16"],
}


# ---------------------------------------------------------------------------
# Interne Hilfsfunktionen
# ---------------------------------------------------------------------------

def _build_prompt(chunk: dict, target_words: int) -> str:
    heading_lines = ["#" * lvl + " " + txt for lvl, txt in chunk["breadcrumbs"]]
    heading_lines.append("#" * chunk["level"] + " " + chunk["heading"])

    return (
        "Du erhältst einen Abschnitt aus einem deutschen Jahresabschluss-Dokument (HGB).\n"
        "Teile den Textinhalt sinnvoll in kleinere Teilabschnitte auf.\n\n"
        "STRIKTE REGELN:\n"
        "1. KEIN Inhalt darf verloren gehen. Jeder Satz, jede Zahl, jede Information "
        "muss vollständig erhalten bleiben.\n"
        "2. Teile NUR an sinnvollen inhaltlichen Grenzen auf (z. B. zwischen Absätzen). "
        "Niemals mitten in einem Satz oder einer Tabelle trennen.\n"
        f"3. Jeder Teilabschnitt soll maximal {target_words} Wörter enthalten.\n"
        f"4. Trenne die Teilabschnitte ausschließlich mit dieser Zeichenkette auf einer "
        f"eigenen Zeile:\n{SEPARATOR}\n"
        "5. Gib NUR den aufgeteilten Inhalt zurück. Keine Erklärungen oder Kommentare.\n"
        "6. Füge die Überschriften NICHT in die Ausgabe ein.\n\n"
        "Überschriften-Kontext (nur zur Information, nicht ausgeben):\n"
        + "\n".join(heading_lines)
        + "\n\nAufzuteilender Inhalt:\n---\n"
        + chunk["content"]
        + "\n---"
    )


def _parse(response_text: str, original: dict) -> list[dict]:
    parts = [p.strip() for p in response_text.split(SEPARATOR) if p.strip()]
    if not parts:
        logger.warning("Parsing fehlgeschlagen – Original bleibt: '%s'", original["heading"])
        return [original]
    return [
        {
            "level":       original["level"],
            "heading":     original["heading"],
            "breadcrumbs": original["breadcrumbs"],
            "content":     part,
            "word_count":  len(part.split()),
        }
        for part in parts
    ]


# ---------------------------------------------------------------------------
# Öffentliche Funktion
# ---------------------------------------------------------------------------

def split_chunk(chunk: dict, target_words: int, api_key: str) -> list[dict]:
    """
    Teilt einen langen Chunk per OpenRouter (Gemma 4 31B) in Sub-Chunks auf.

    Args:
        chunk        : Chunk-Dict mit 'level', 'heading', 'breadcrumbs', 'content'
        target_words : Max. Wortanzahl je Sub-Chunk (= Median über alle Chunks)
        api_key      : OpenRouter API-Schlüssel

    Returns:
        Liste von Sub-Chunk-Dicts (gleiche Struktur wie Eingabe-Chunk)
    """
    client = OpenAI(api_key=api_key, base_url=BASE_URL)
    prompt = _build_prompt(chunk, target_words)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"provider": _PROVIDER_PREFS},
    )

    text = response.choices[0].message.content or ""
    logger.info("Gemma Antwort erhalten (%d Zeichen).", len(text))
    return _parse(text, chunk)
