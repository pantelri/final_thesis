"""
Reformat the R19 "Anlagenspiegel" passages into clean Markdown tables.

ONLY formatting is changed (pipes, line breaks, bold column headers, splitting
the concatenated sub-tables, removing extraction artifacts). Number VALUES are
never altered — enforced by a number-conservation check that diffs the multiset
of numeric tokens between the old and cleaned text.

  docker exec -w /app annotation_app-app-1 python -m scripts.clean_anlagenspiegel [--item ID ...] [--apply]

Default is a dry-run check. CLEAN holds the hand-reformatted passages keyed by
annotation_items.id.
"""
import argparse
import re
from collections import Counter

from sqlalchemy import text as sql

from app.database import SessionLocal
from app.models import AnnotationItem, ElementType, PassageSentence
from .segmentation import segment_passage

NUM = re.compile(r"-?\d[\d.]*(?:,\d+)?")


def numbers(text: str) -> Counter:
    """Multiset of numeric tokens (values, dates and list ordinals alike)."""
    return Counter(NUM.findall(text))


def check(old: str, new: str):
    """Return (added, removed): numbers present only in new / only in old."""
    no, nn = numbers(old), numbers(new)
    added = nn - no       # in cleaned but not original -> typo/invention (must be empty)
    removed = no - nn     # in original but not cleaned -> dropped duplicates/garbage (review)
    return added, removed


# Hand-reformatted passages, keyed by annotation_items.id (data module).
from .anlagenspiegel_data import ALLOW_ADDED, CLEAN


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--item", type=int, nargs="*")
    args = ap.parse_args()

    db = SessionLocal()
    items = sorted(CLEAN) if not args.item else [i for i in sorted(CLEAN) if i in set(args.item)]
    bad = 0
    for iid in items:
        item = db.get(AnnotationItem, iid)
        old, new = item.passage_text, CLEAN[iid]
        added, removed = check(old, new)
        for tok in ALLOW_ADDED.get(iid, set()):
            added.pop(tok, None)
        print("=" * 90)
        print(f"item {iid}  {item.company_id}  added={sum(added.values())}  removed={sum(removed.values())}")
        if added:
            bad += 1
            print(f"   !! INVENTED/CHANGED numbers (must be empty): {dict(added)}")
        if removed:
            print(f"   .. removed (dup/garbage, review): {dict(removed)}")
        if args.apply:
            item.passage_text = new
            db.query(PassageSentence).filter_by(item_id=iid).delete()
            db.flush()
            for idx, (etype, etext) in enumerate(segment_passage(new)):
                db.add(PassageSentence(
                    item_id=iid, idx=idx,
                    element_type=ElementType.sentence if etype == "sentence" else ElementType.table,
                    text=etext))

    print("=" * 90)
    print(f"items: {len(items)}   with invented numbers: {bad}")
    if args.apply and bad == 0:
        db.commit()
        print(">>> COMMITTED.")
    else:
        db.rollback()
        print(">>> DRY-RUN / not committed." + ("" if bad == 0 else " Fix invented numbers first."))
    db.close()


if __name__ == "__main__":
    main()
