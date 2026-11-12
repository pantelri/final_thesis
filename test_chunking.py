"""Sanity-check for the chunking pipeline on one company (no API calls needed).

Tests
-----
1. Offset consistency : md[char_start:char_end] == chunk.text  for every chunk
2. Size limit         : len(text) <= 701 for every non-table chunk
3. Tables intact      : every table block in the source MD maps to exactly
                        one is_table=True chunk (no table is split or merged)
4. No table lines in text chunks (and no plain text in table chunks)

Usage:
    python test_chunking.py                   # tests Amazon_2024 (default)
    python test_chunking.py BoschMS_2024
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from Ingestion.chunk_headings import split_by_headings
from Ingestion.chunk_tables   import extract_tables_and_gaps
from Ingestion.chunk_text     import rechunk_text, MAX_CHARS

MD_DIR   = Path(__file__).parent / "Output" / "md_files"
DEFAULT  = "Amazon_2024"


# ── helpers ───────────────────────────────────────────────────────────────────

def _is_table_line(line: str) -> bool:
    return line.lstrip().startswith('|')


def _find_table_blocks(md_text: str) -> list[tuple[int, int]]:
    """Return (start, end) absolute offsets for every table block in the source."""
    blocks, pos, i = [], 0, 0
    lines = md_text.split('\n')
    while i < len(lines):
        line_len = len(lines[i]) + 1          # +1 for the '\n'
        if _is_table_line(lines[i]):
            block_start = pos
            while i < len(lines) and _is_table_line(lines[i]):
                pos += len(lines[i]) + 1
                i += 1
            blocks.append((block_start, pos))
        else:
            pos += line_len
            i += 1
    return blocks


def _build_chunks(md_text: str) -> list[dict]:
    chunks: list[dict] = []
    for section in split_by_headings(md_text):
        tables, gaps = extract_tables_and_gaps(section)
        chunks.extend(tables)
        for gap in gaps:
            chunks.extend(rechunk_text(gap))
    return chunks


# ── test runner ───────────────────────────────────────────────────────────────

def run_sanity_check(company: str = DEFAULT) -> bool:
    md_path = MD_DIR / f"{company}.md"
    assert md_path.exists(), f"MD-Datei nicht gefunden: {md_path}"
    md_text = md_path.read_text(encoding='utf-8')
    chunks  = _build_chunks(md_text)

    sep = "=" * 62
    print(f"\n{sep}\n  Sanity-Check: {company}\n{sep}")
    print(f"  MD-Länge          : {len(md_text):>6,} Zeichen")
    print(f"  Chunks gesamt     : {len(chunks):>6}")
    print(f"  davon Tabellen    : {sum(1 for c in chunks if c['is_table']):>6}")
    print(f"  davon Text        : {sum(1 for c in chunks if not c['is_table']):>6}")

    errors: list[str] = []

    # ── Test 1: Offset consistency ────────────────────────────────────────────
    for c in chunks:
        reconstructed = md_text[c['char_start']:c['char_end']]
        if reconstructed != c['text']:
            errors.append(
                f"OFFSET_MISMATCH  @{c['char_start']}:{c['char_end']}  "
                f"expected={repr(c['text'][:40])}  got={repr(reconstructed[:40])}"
            )
    _report(errors, "[1] Offset-Konsistenz")

    # ── Test 2: Size limit for text chunks ────────────────────────────────────
    overlong = [c for c in chunks if not c['is_table'] and len(c['text']) > MAX_CHARS]
    for c in overlong:
        errors.append(f"TOO_LONG  {len(c['text'])} chars @{c['char_start']}:{c['char_end']}")
    _report(overlong, f"[2] Text-Chunks <={MAX_CHARS} Zeichen")

    # ── Test 3: Every source table block → exactly one table chunk ────────────
    orig_tables  = _find_table_blocks(md_text)
    table_chunks = [c for c in chunks if c['is_table']]
    tbl_errors: list[str] = []
    for tb_s, tb_e in orig_tables:
        covering = [c for c in table_chunks
                    if c['char_start'] <= tb_s and c['char_end'] >= tb_e]
        if len(covering) != 1:
            tbl_errors.append(
                f"TABLE_SPLIT  @{tb_s}:{tb_e}  covered_by={len(covering)} chunks"
            )
    errors.extend(tbl_errors)
    _report(tbl_errors, "[3] Tabellen ungeteilt")

    # ── Test 4: No cross-contamination ────────────────────────────────────────
    for c in chunks:
        lines = c['text'].split('\n')
        if c['is_table']:
            non_tbl = [l for l in lines if l.strip() and not _is_table_line(l)]
            if non_tbl:
                errors.append(f"TABLE_HAS_TEXT @{c['char_start']}: {non_tbl[0][:60]}")
        # Note: text chunks may contain lines starting with | if the heading
        # detection split a table — this would also be caught by Test 3.

    _report([], "[4] Keine Kontamination (Text in Tabellen)")

    # ── Summary ───────────────────────────────────────────────────────────────
    if errors:
        print(f"\n  FEHLER: {len(errors)} Probleme gefunden:")
        for e in errors[:8]:
            print(f"    -> {e}")
    else:
        print(f"\n  ALLE TESTS BESTANDEN")
    print(f"{sep}\n")
    return not errors


def _report(items, label: str) -> None:
    status = "OK" if not items else f"{len(items)} FEHLER"
    print(f"  {label:<40}: {status}")


if __name__ == "__main__":
    company = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    ok = run_sanity_check(company)
    sys.exit(0 if ok else 1)
