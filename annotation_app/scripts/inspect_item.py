#!/usr/bin/env python3
"""
Inspect an annotation item: obligation, company, full passage text,
and all passage_sentences in index order.

Use this to verify that:
  - Char-offsets from df1_spans were correctly transferred
  - Markdown tables appear as a single element of type 'table'
  - German sentence segmentation is sensible

Usage:
    cd annotation_app
    python -m scripts.inspect_item --item-id 1

    # List the first few items if you don't know an ID yet:
    python -m scripts.inspect_item --list 10
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.database import SessionLocal
from app.models import AnnotationItem, Company, Obligation, PassageSentence


def inspect(item_id: int) -> None:
    db = SessionLocal()
    try:
        item = db.get(AnnotationItem, item_id)
        if item is None:
            print(f"ERROR: No annotation_item with id={item_id}")
            sys.exit(1)

        obligation = db.get(Obligation, item.obligation_id)
        company = db.get(Company, item.company_id)
        sentences = (
            db.query(PassageSentence)
            .filter_by(item_id=item.id)
            .order_by(PassageSentence.idx)
            .all()
        )

        SEP = "─" * 72
        print("=" * 72)
        print(f"  ANNOTATION ITEM #{item.id}")
        print("=" * 72)
        print(f"  Gesellschaft    : {company.name if company else item.company_id}"
              f" ({item.company_id})")
        print(f"  Pflicht         : {item.obligation_id}"
              f" — {obligation.title_de if obligation else '?'}")
        if obligation:
            print(f"  Kategorie       : {obligation.category or '–'}")
            print(f"  Rechtsgrundlage : {obligation.legal_basis or '–'}")
        print(f"  Char-Offsets    : {item.passage_start} – {item.passage_end}")
        print(f"  Overlap-Set     : {item.in_overlap_set}")
        print(f"  Stratum         : {item.stratum or '–'}")
        print()

        print(SEP)
        print("  PASSAGE TEXT (vollständig)")
        print(SEP)
        print(item.passage_text)
        print()

        print(SEP)
        print(f"  PASSAGE SENTENCES  ({len(sentences)} Elemente nach Segmentierung)")
        print(SEP)
        for s in sentences:
            tag = "TABLE" if s.element_type.value == "table" else "SENT "
            offsets = (
                f"  chars {s.char_start}–{s.char_end}"
                if s.char_start is not None else ""
            )
            print(f"  [{s.idx:02d}] {tag}{offsets}")
            # Truncate for readability; use --full for complete output
            text = s.text
            if len(text) > 320:
                print(f"    {text[:320]}")
                print(f"    … ({len(text)} chars total, truncated for display)")
            else:
                # Indent multi-line text
                for line in text.split("\n"):
                    print(f"    {line}")
            print()

    finally:
        db.close()


def list_items(n: int) -> None:
    db = SessionLocal()
    try:
        items = db.query(AnnotationItem).order_by(AnnotationItem.id).limit(n).all()
        if not items:
            print("No annotation items in database.")
            return
        print(f"{'ID':>5}  {'Company':<25}  {'Obligation':<30}  {'Overlap'}")
        print("─" * 72)
        for it in items:
            ob = db.get(Obligation, it.obligation_id)
            title = (ob.title_de[:28] if ob else it.obligation_id)
            print(f"{it.id:>5}  {it.company_id:<25}  {title:<30}  {it.in_overlap_set}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect annotation items in the database"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--item-id", type=int, metavar="ID",
                       help="Show full details for this item ID")
    group.add_argument("--list", type=int, metavar="N", default=None,
                       help="List the first N items (ID, company, obligation)")
    args = parser.parse_args()

    if args.item_id is not None:
        inspect(args.item_id)
    else:
        list_items(args.list)


if __name__ == "__main__":
    main()
