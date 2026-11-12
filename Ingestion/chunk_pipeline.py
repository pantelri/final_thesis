"""Full chunking pipeline for German HGB Jahresabschluss MD files.

Pipeline per document:
  1. Split by Markdown headings (absolute char offsets tracked throughout)
  2. Extract tables as atomic chunks (never split)
  3. Rechunk remaining text to ≤701 chars with ~12 % overlap
  4. LLM-split any text chunk still >701 chars (Gemma via OpenRouter)
  5. Verify: size ≤ 701 and content verbatim in source MD; auto-fix failures
  6. Export combined chunks.jsonl + chunks.csv

Usage:
    python -m Ingestion.chunk_pipeline          # all MD files
    python -m Ingestion.chunk_pipeline Amazon_2024   # single company
"""
from __future__ import annotations
import logging
import os
import sys
from pathlib import Path

from Ingestion.chunk_headings import split_by_headings
from Ingestion.chunk_tables   import extract_tables_and_gaps
from Ingestion.chunk_text     import rechunk_text, MAX_CHARS
from Ingestion.chunk_llm      import split_overlong_chunk
from Ingestion.chunk_verify   import verify_and_fix
from Ingestion.chunk_export   import append_jsonl, append_csv

logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s %(name)s: %(message)s')
logger = logging.getLogger(__name__)

_ROOT    = Path(__file__).parent.parent
MD_DIR   = _ROOT / "Output" / "md_files"
OUT_DIR  = _ROOT / "Output" / "chunks"
JSONL_OUT = OUT_DIR / "chunks.jsonl"
CSV_OUT   = OUT_DIR / "chunks.csv"


def process_company(
    md_path:   Path,
    company:   str,
    api_key:   str,
) -> list[dict]:
    """Run the full pipeline for one company's MD file. Returns verified chunks."""
    md_text = md_path.read_text(encoding='utf-8')
    logger.info("[%s] %d chars", company, len(md_text))

    # Step 1: Heading split
    sections = split_by_headings(md_text)

    # Step 2 + 3: Table extraction + text rechunking
    raw: list[dict] = []
    for section in sections:
        tables, gaps = extract_tables_and_gaps(section)
        raw.extend(tables)
        for gap in gaps:
            raw.extend(rechunk_text(gap))

    # Step 4: LLM for overlong text chunks
    after_llm: list[dict] = []
    for chunk in raw:
        if not chunk['is_table'] and len(chunk['text']) > MAX_CHARS:
            after_llm.extend(split_overlong_chunk(chunk, api_key))
        else:
            after_llm.append(chunk)

    # Step 5: Verify + auto-fix
    verified, warnings = verify_and_fix(after_llm, md_text, company)
    logger.info("[%s] %d chunks  (%d fixes)", company, len(verified), len(warnings))

    return verified


def run(companies: list[str] | None = None, api_key: str | None = None) -> None:
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY nicht gesetzt.")

    md_paths = (
        [MD_DIR / f"{c}.md" for c in companies]
        if companies
        else sorted(MD_DIR.glob("*.md"))
    )

    # Clear combined output files
    JSONL_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSONL_OUT.write_text("", encoding='utf-8')

    first = True
    for md_path in md_paths:
        company = md_path.stem
        if not md_path.exists():
            logger.error("Datei nicht gefunden: %s", md_path)
            continue
        chunks = process_company(md_path, company, api_key)
        append_jsonl(chunks, company, JSONL_OUT)
        append_csv(chunks, company, CSV_OUT, write_header=first)
        first = False
        logger.info("[%s] exportiert → %s", company, OUT_DIR)

    logger.info("Fertig. Output: %s", OUT_DIR)


if __name__ == "__main__":
    args = sys.argv[1:] or None
    run(companies=args)
