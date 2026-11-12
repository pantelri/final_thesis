"""Phase 1b — Canonical retrieval/evidence GT snapshot + span derivation + rebuild check.

- Reads the curated evidence GT (passage_sentences) from the frozen DB export.
- Locates each element's md char span (whitespace-robust matcher).
- Writes results/retrieval_gt_snapshot.csv (frozen, chunk-independent span GT).
- Diffs vs the stale df2_pflichten.csv to confirm rebuild_passages edits are present.
- Writes results/retrieval_gt_rebuild_check.csv + console summary.

Run: python -m scripts.eval.phase1b_retrieval_gt
"""
from __future__ import annotations

import pandas as pd

from scripts.eval._common import MD_DIR, RESULTS, STALE_PFLICHTEN_CSV, write_csv
from scripts.eval._load_gt import (
    gt_master, load_irrelevant, load_sentences, load_suggested,
)
from scripts.eval._spans import _strip_map, locate


def _nows(s: str) -> str:
    """Alphanumeric-only projection (matches the span locator's normalization)."""
    return _strip_map(s or "")[0]


def build_snapshot() -> pd.DataFrame:
    sents = load_sentences()
    items = gt_master()[["item_id", "company_id", "obligation_id", "relevance",
                         "is_relevant", "passage_start", "passage_end"]]
    df = sents.merge(items, on="item_id", how="left", validate="many_to_one")

    rows = []
    for r in df.itertuples(index=False):
        # Drop '[...]' non-contiguous separators (passage_builder joiners, not evidence).
        if _strip_map(r.text)[0] == "":
            continue
        md_path = str(MD_DIR / f"{r.company_id}.md")
        hint = int(r.passage_start) if pd.notna(r.passage_start) else None
        loc = locate(md_path, r.text, hint_start=hint)
        cs, ce, status = loc["char_start"], loc["char_end"], loc["status"]
        if cs is None:
            # Restructured tables / reformatted sentences are not verbatim md substrings.
            # Fall back to the item char-envelope so the element still carries a usable span.
            cs = int(r.passage_start) if pd.notna(r.passage_start) else None
            ce = int(r.passage_end) if pd.notna(r.passage_end) else None
            status = "envelope_fallback"
        rows.append({
            "item_id": r.item_id,
            "company_id": r.company_id,
            "obligation_id": r.obligation_id,
            "is_relevant": r.is_relevant,
            "relevance": r.relevance,
            "element_idx": int(r.idx),
            "element_type": r.element_type,
            "char_start": cs,
            "char_end": ce,
            "span_status": status,
            "n_chars": (ce - cs) if cs is not None and ce is not None else 0,
            "text": r.text,
        })
    return pd.DataFrame(rows)


def rebuild_check(snap: pd.DataFrame) -> list[dict]:
    """Confirm rebuild_passages edits are present in the DB vs stale df2_pflichten."""
    irr = load_irrelevant()
    sug = load_suggested()
    out = []

    # (1) additions present: each suggested passage's md span should overlap a current GT span
    snap_int = snap.copy()
    snap_int["item_id"] = snap_int["item_id"].astype(int)
    snap_int["char_start"] = pd.to_numeric(snap_int["char_start"], errors="coerce")
    snap_int["char_end"] = pd.to_numeric(snap_int["char_end"], errors="coerce")
    spans_by_item: dict[int, list[tuple[int, int]]] = {}
    for it, g in snap_int.dropna(subset=["char_start", "char_end"]).groupby("item_id"):
        spans_by_item[it] = list(zip(g["char_start"].astype(int), g["char_end"].astype(int)))
    items_df = gt_master().set_index("item_id")
    add_present = 0
    for r in sug.itertuples(index=False):
        it = int(r.item_id)
        comp = items_df.loc[str(it), "company_id"] if str(it) in items_df.index else None
        if comp is None:
            continue
        loc = locate(str(MD_DIR / f"{comp}.md"), r.passage_text)
        if loc["char_start"] is None:
            continue
        s, e = loc["char_start"], loc["char_end"]
        if any(s < ce and cs < e for cs, ce in spans_by_item.get(it, [])):
            add_present += 1
    out.append({"metric": "suggested_passages_total", "value": len(sug)})
    out.append({"metric": "suggested_passages_overlapping_current_GT", "value": add_present})

    # (2) removals recorded
    out.append({"metric": "irrelevant_elements_total", "value": len(irr)})
    out.append({"metric": "items_with_irrelevant_edits", "value": irr["item_id"].nunique()})
    out.append({"metric": "items_with_suggested_edits", "value": sug["item_id"].nunique()})

    # (3) diff vs stale df2_pflichten (per company x obligation combined GT text)
    stale = pd.read_csv(STALE_PFLICHTEN_CSV, dtype=str, keep_default_na=False)
    stale["key"] = stale["company"] + "|" + stale["rcode"]
    stale_text = {k: _nows(t) for k, t in zip(stale["key"], stale["text_combined"])}

    cur = snap.copy()
    cur["key"] = cur["company_id"] + "|" + cur["obligation_id"]
    cur_text = cur.groupby("key")["text"].apply(lambda s: _nows(" ".join(s))).to_dict()

    keys = set(stale_text) | set(cur_text)
    changed = same = 0
    for k in keys:
        if stale_text.get(k, "") == cur_text.get(k, ""):
            same += 1
        else:
            changed += 1
    out.append({"metric": "stale_vs_current_pairs_compared", "value": len(keys)})
    out.append({"metric": "pairs_text_changed_vs_stale", "value": changed})
    out.append({"metric": "pairs_text_identical_to_stale", "value": same})
    return out


def main() -> None:
    snap = build_snapshot()
    cols = ["item_id", "company_id", "obligation_id", "is_relevant", "relevance",
            "element_idx", "element_type", "char_start", "char_end", "span_status",
            "n_chars", "text"]
    snap = snap[cols]
    snap.to_csv(RESULTS / "retrieval_gt_snapshot.csv", index=False, encoding="utf-8")

    checks = rebuild_check(snap)
    write_csv(RESULTS / "retrieval_gt_rebuild_check.csv", checks, ["metric", "value"])

    # ---- summary ----
    located = snap[snap["char_start"].notna()]
    status = snap["span_status"].value_counts().to_dict()
    items_with_gt = snap[snap["element_type"].isin(["sentence", "table"])]["item_id"].nunique()
    print("=" * 70)
    print("Phase 1b — Retrieval/evidence GT snapshot")
    print("=" * 70)
    print(f"  GT elements total          : {len(snap)}")
    print(f"  located (span found)       : {len(located)}  ({len(located)/len(snap)*100:.1f}%)")
    print(f"  span_status counts         : {status}")
    print(f"  element_type counts        : {snap['element_type'].value_counts().to_dict()}")
    print(f"  distinct items with GT     : {items_with_gt} / 182")
    print(f"  items WITHOUT any GT element: {182 - items_with_gt}")
    print(f"  median span length (chars) : {located['n_chars'].median():.0f}")
    print("-" * 70)
    print("  Rebuild-applied check:")
    for c in checks:
        print(f"    {c['metric']:42} {c['value']}")
    print("-" * 70)
    print(f"  snapshot -> {RESULTS / 'retrieval_gt_snapshot.csv'}")
    notfound = snap[snap["span_status"] == "notfound"]
    if len(notfound):
        print(f"  WARNING: {len(notfound)} elements not located in md (see span_status='notfound')")


if __name__ == "__main__":
    main()
