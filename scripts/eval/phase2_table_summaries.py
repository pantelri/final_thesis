"""Phase 2 (llmdesc arm) — describe each atomic table chunk as German plain text.

Tables are embedded poorly as raw markdown (pipes/separators burn tokens; gemini-
embedding-001's 2048-token limit silently truncates the largest tables) and match
natural-language obligation queries weakly. This step asks Qwen3.7-Max to write a
faithful plain-text description of each table; phase2_embed then embeds the
description (not the markdown) for table chunks. The verbatim md is kept as the
chunk text/offsets, so GT span overlap and verification are unaffected.

Tables are atomic and identical across segmentations, so the 127 unique tables are
summarized once, keyed by table text-hash, and reused for all llmdesc collections.

Output: Output/chunks/table_summaries.jsonl  (one record per unique table)
Run: python -m scripts.eval.phase2_table_summaries
"""
from __future__ import annotations

import hashlib
import json

from scripts.eval._common import (
    CHUNKS_BY_SEG, TABLE_SUMMARIES_JSONL, TABLE_SUMMARY_MODEL,
)
from scripts.eval.lib.llm import ChatClient

CACHE = TABLE_SUMMARIES_JSONL.parent / "_table_summary_cache.jsonl"

SYSTEM = (
    "Du bist ein Assistent fuer Wirtschaftspruefer und beschreibst Tabellen aus "
    "deutschen HGB-Jahresabschluessen (Bilanz, GuV, Anlagenspiegel, Anhang, "
    "Lagebericht). Deine Beschreibung wird fuer die semantische Suche eingebettet, "
    "nicht der Tabelleninhalt selbst. Antworte ausschliesslich auf Deutsch in "
    "sachlichem Fliesstext, ohne die Tabelle als Markdown zu wiederholen."
)

USER_TMPL = (
    "Beschreibe den Inhalt der folgenden Tabelle praezise als Fliesstext. "
    "Befolge dabei strikt:\n"
    "1. Nenne zuerst den Tabellentyp (z. B. Bilanz, Gewinn- und Verlustrechnung, "
    "Anlagenspiegel, Rueckstellungsspiegel, Verbindlichkeitenspiegel, sonstige).\n"
    "2. Zaehle ALLE in der Tabelle vorhandenen Positionen namentlich auf "
    "(bei Bilanz/GuV alle Bilanz- bzw. GuV-Posten; beim Anlagenspiegel alle "
    "Anlagepositionen).\n"
    "3. Gib bei Bilanz-, GuV- oder Anlagenspiegel-Tabellen ausdruecklich an, ob "
    "latente Steuern und ob ein Geschaefts- oder Firmenwert (Goodwill) vorhanden "
    "sind ODER NICHT vorhanden sind (explizit verneinen, falls sie fehlen).\n"
    "4. Beschreibe die wesentlichen Veraenderungen gegenueber dem Vorjahr, sofern "
    "Vorjahreswerte enthalten sind.\n"
    "5. Erfinde keine Zahlen; bleibe der Tabelle treu. Fasse dich knapp "
    "(ein kurzer Absatz).\n\n"
    "Abschnitt (Ueberschriftenpfad): {heading}\n\n"
    "Tabelle (Markdown):\n{table}"
)


def _text_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def unique_tables() -> list[dict]:
    """All distinct atomic table chunks across segmentations, keyed by text-hash.
    Records keep company/heading/offsets of the first occurrence for traceability."""
    seen: dict[str, dict] = {}
    for jsonl in CHUNKS_BY_SEG.values():
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            ch = json.loads(line)
            if not ch.get("is_table"):
                continue
            h = _text_hash(ch["text"])
            if h not in seen:
                seen[h] = {
                    "text_hash": h, "company": ch["company"],
                    "heading_path": ch.get("heading_path", ""),
                    "char_start": ch["char_start"], "char_end": ch["char_end"],
                    "table_md": ch["text"],
                }
    return list(seen.values())


def main() -> None:
    tables = unique_tables()
    client = ChatClient(TABLE_SUMMARY_MODEL, CACHE, temperature=0.0, max_tokens=700)
    print(f"unique tables: {len(tables)}  model: {TABLE_SUMMARY_MODEL}")

    # (text_hash, system, user) per table; cached tables resolve instantly.
    items = [
        (t["text_hash"], SYSTEM,
         USER_TMPL.format(heading=t["heading_path"] or "(kein)", table=t["table_md"]))
        for t in tables
    ]

    def _progress(key, n, total):
        if n % 10 == 0 or n == total:
            print(f"  {n}/{total} summarized", flush=True)

    summaries = client.complete_many(items, max_workers=8, on_done=_progress)

    out = [{
        "text_hash": t["text_hash"], "company": t["company"],
        "heading_path": t["heading_path"], "char_start": t["char_start"],
        "char_end": t["char_end"], "summary": summaries[t["text_hash"]],
    } for t in tables]

    with open(TABLE_SUMMARIES_JSONL, "w", encoding="utf-8") as fh:
        for rec in out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    lens = [len(r["summary"]) for r in out]
    print(f"wrote {len(out)} summaries -> {TABLE_SUMMARIES_JSONL}")
    print(f"summary char-len min/median/max: {min(lens)} / {sorted(lens)[len(lens)//2]} / {max(lens)}")


if __name__ == "__main__":
    main()
