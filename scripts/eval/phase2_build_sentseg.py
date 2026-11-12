"""Phase 2 (segmentation B) — build sentence-aware chunks.

Same heading-split + atomic-table policy and the same size/overlap budget as the
existing sliding-window corpus (MAX_CHARS=701, ~84-char overlap), but text gaps
are packed from whole SENTENCES (segmentation.segment_passage) so a chunk
boundary never falls mid-sentence. Chunk text stays a verbatim md substring;
char offsets are preserved.

Output: Output/chunks/chunks_sentseg.jsonl  (mirrors chunks.jsonl schema)
Run: python -m scripts.eval.phase2_build_sentseg
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from Ingestion.chunk_headings import split_by_headings
from Ingestion.chunk_tables import extract_tables_and_gaps
from Ingestion.chunk_text import MAX_CHARS, _OVERLAP

from scripts.eval._common import MD_DIR, ROOT
from scripts.eval._spans import _strip_map

# Reuse the exact GT segmenter from the annotation app.
sys.path.insert(0, str(ROOT / "annotation_app" / "scripts"))
from segmentation import normalize_text, segment_passage  # noqa: E402

OUT_JSONL = ROOT / "Output" / "chunks" / "chunks_sentseg.jsonl"


def _sentence_tiles(gap_text: str) -> list[tuple[int, int]]:
    """Tile gap_text into consecutive sentence-aligned spans covering [0, len).

    Sentence START offsets are located by sequential alphanumeric matching (the
    segmenter normalizes text, so exact substring search fails). The located
    starts become cut points; the union of the returned tiles is the ENTIRE gap,
    so no character (and no sentence) is ever dropped. Each tile is verbatim md.
    """
    elements = [t for _typ, t in segment_passage(normalize_text(gap_text))]
    proj, idx_map = _strip_map(gap_text)          # alnum projection + index map
    starts: list[int] = []
    cursor = 0
    for el in elements:
        needle, _ = _strip_map(el)
        if not needle:
            continue
        pos = proj.find(needle, cursor)
        if pos == -1:
            pos = proj.find(needle)
            if pos == -1:
                continue
        starts.append(idx_map[pos])
        cursor = pos + len(needle)

    n = len(gap_text)
    if not starts:
        return [(0, n)]                            # nothing located -> keep all text
    # Cut points: gap start, then each sentence start (after the first), then EOF.
    cuts = [0] + [s for s in starts[1:] if 0 < s < n] + [n]
    cuts = sorted(set(cuts))
    return [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1) if cuts[i + 1] > cuts[i]]


def _pack(spans: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Greedily pack sentence spans into <=MAX_CHARS chunks with ~_OVERLAP overlap.

    A single sentence longer than MAX_CHARS is emitted alone (never split).
    """
    if not spans:
        return []
    chunks: list[tuple[int, int]] = []
    i = 0
    n = len(spans)
    while i < n:
        start = spans[i][0]
        j = i
        while j + 1 < n and (spans[j + 1][1] - start) <= MAX_CHARS:
            j += 1
        end = spans[j][1]
        chunks.append((start, end))
        if j >= n - 1:
            break
        # overlap: next chunk begins at the first sentence whose end exceeds
        # (end - _OVERLAP); guarantee forward progress.
        nxt = i + 1
        for k in range(i, j + 1):
            if spans[k][1] > end - _OVERLAP:
                nxt = k
                break
        i = max(nxt, i + 1)
    return chunks


def build_company(company: str) -> list[dict]:
    md_text = (MD_DIR / f"{company}.md").read_text(encoding="utf-8")
    out: list[dict] = []
    seq = 0
    for section in split_by_headings(md_text):
        tables, gaps = extract_tables_and_gaps(section)
        # tables: atomic, identical policy to segmentation A
        for t in tables:
            out.append({
                "chunk_id": f"{company}_sent_{seq:04d}", "company": company,
                "heading_path": t["heading_path"], "char_start": t["char_start"],
                "char_end": t["char_end"], "is_table": True,
                "n_tokens": len(t["text"].split()), "text": t["text"],
            })
            seq += 1
        for gap in gaps:
            gtext, gstart = gap["text"], gap["char_start"]
            for ls, le in _pack(_sentence_tiles(gtext)):
                ctext = gtext[ls:le]
                if not ctext.strip():
                    continue
                out.append({
                    "chunk_id": f"{company}_sent_{seq:04d}", "company": company,
                    "heading_path": gap["heading_path"], "char_start": gstart + ls,
                    "char_end": gstart + le, "is_table": False,
                    "n_tokens": len(ctext.split()), "text": ctext,
                })
                seq += 1
    return out


def main() -> None:
    companies = sorted(p.stem for p in MD_DIR.glob("*.md"))
    all_chunks: list[dict] = []
    over = 0
    for c in companies:
        chunks = build_company(c)
        all_chunks.extend(chunks)
        over += sum(1 for ch in chunks if not ch["is_table"] and len(ch["text"]) > MAX_CHARS)

    # verify verbatim against md + full-coverage of all non-heading body text
    bad = 0
    uncovered_total = 0          # non-whitespace md chars not in any chunk and not a heading marker
    heading_chars = 0            # non-whitespace chars on '#'-heading lines (by-design in heading_path)
    per_company_cov: list[str] = []
    by_company: dict[str, list[dict]] = {}
    for ch in all_chunks:
        by_company.setdefault(ch["company"], []).append(ch)
    for c in companies:
        md = (MD_DIR / f"{c}.md").read_text(encoding="utf-8")
        covered = bytearray(len(md))
        for ch in by_company.get(c, []):
            if md[ch["char_start"]:ch["char_end"]] != ch["text"]:
                bad += 1
            for p in range(ch["char_start"], ch["char_end"]):
                covered[p] = 1
        # mark heading-marker lines (start with optional ws then '#')
        heading_mask = bytearray(len(md))
        for line_start in range(len(md)):
            if line_start == 0 or md[line_start - 1] == "\n":
                j = line_start
                while j < len(md) and md[j] in " \t":
                    j += 1
                if j < len(md) and md[j] == "#":
                    k = md.find("\n", line_start)
                    k = len(md) if k == -1 else k
                    for p in range(line_start, k):
                        heading_mask[p] = 1
        unc = sum(1 for p in range(len(md))
                  if not covered[p] and not md[p].isspace() and not heading_mask[p])
        hc = sum(1 for p in range(len(md)) if heading_mask[p] and not md[p].isspace())
        uncovered_total += unc
        heading_chars += hc
        if unc:
            per_company_cov.append(f"{c}: {unc} uncovered body chars")

    with open(OUT_JSONL, "w", encoding="utf-8") as fh:
        for ch in all_chunks:
            fh.write(json.dumps(ch, ensure_ascii=False) + "\n")

    lens = [len(ch["text"]) for ch in all_chunks]
    tbl = sum(1 for ch in all_chunks if ch["is_table"])
    print("=" * 70)
    print("Phase 2 — sentence-aware chunk build (segmentation B)")
    print("=" * 70)
    print(f"  companies              : {len(companies)}")
    print(f"  chunks total           : {len(all_chunks)}  (tables {tbl}, text {len(all_chunks)-tbl})")
    print(f"  char-len  min/median/max: {min(lens)} / {sorted(lens)[len(lens)//2]} / {max(lens)}")
    print(f"  text chunks > {MAX_CHARS} chars : {over}  (single oversized sentences kept whole)")
    print(f"  verbatim-mismatch chunks: {bad}  (must be 0)")
    print(f"  uncovered BODY chars    : {uncovered_total}  (must be 0 — no sentence dropped)")
    print(f"  heading-marker chars    : {heading_chars}  (excluded by design; live in heading_path)")
    for line in per_company_cov:
        print(f"    ! {line}")
    print(f"  output -> {OUT_JSONL}")
    if bad or uncovered_total:
        raise SystemExit("verbatim/coverage check failed")


if __name__ == "__main__":
    main()
