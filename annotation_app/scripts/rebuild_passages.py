"""
Rebuild annotation_items.passage_text from annotator feedback, positioned
against the ORIGINAL .md documents (verbatim substrings, in document order,
non-contiguous parts separated by [...]), then re-segment passage_sentences.

annotations / irrelevant_elements / suggested_passages are NEVER modified.
Default is DRY-RUN; pass --apply to write. Always pg_dump first.

  docker exec -w /app annotation_app-app-1 python -m scripts.rebuild_passages [--item ID ...] [--apply]
"""
import argparse
import sys
from pathlib import Path

from sqlalchemy import text as sql

from app.database import SessionLocal
from app.models import AnnotationItem, ElementType, PassageSentence
from .segmentation import normalize_text, segment_passage

# MDprocessing lives at the source_code root (mounted read-only at /data in the
# container, or two levels above this file on the host).
for _root in ("/data", str(Path(__file__).resolve().parents[2])):
    if (Path(_root) / "MDprocessing").is_dir() and _root not in sys.path:
        sys.path.insert(0, _root)
from MDprocessing import MdDocument                       # noqa: E402
from .passage_builder import build_passage                # noqa: E402

MD_DIR = Path("/data/Output/md_files")


def load_feedback(db, item_id):
    sentences = db.execute(sql(
        "SELECT idx, element_type, text FROM passage_sentences "
        "WHERE item_id=:i ORDER BY idx"), {"i": item_id}).all()
    irrelevant = {r[0] for r in db.execute(sql(
        "SELECT ie.sentence_idx FROM irrelevant_elements ie "
        "JOIN annotations a ON a.id = ie.annotation_id WHERE a.item_id=:i"), {"i": item_id})}
    suggested = db.execute(sql(
        "SELECT sp.passage_text, sp.source_ref FROM suggested_passages sp "
        "JOIN annotations a ON a.id = sp.annotation_id WHERE a.item_id=:i "
        "ORDER BY sp.id"), {"i": item_id}).all()
    return sentences, irrelevant, suggested


def reseg(db, item, new_text):
    item.passage_text = new_text
    db.query(PassageSentence).filter_by(item_id=item.id).delete()
    db.flush()
    for idx, (etype, etext) in enumerate(segment_passage(new_text)):
        db.add(PassageSentence(
            item_id=item.id, idx=idx,
            element_type=ElementType.sentence if etype == "sentence" else ElementType.table,
            text=etext))


def affected_items(db, only):
    ids = db.execute(sql(
        "SELECT DISTINCT a.item_id FROM annotations a "
        "WHERE a.id IN (SELECT annotation_id FROM irrelevant_elements) "
        "   OR a.id IN (SELECT annotation_id FROM suggested_passages) "
        "ORDER BY a.item_id")).scalars().all()
    return [i for i in ids if not only or i in set(only)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes (default: dry-run)")
    ap.add_argument("--item", type=int, nargs="*", help="restrict to specific item ids")
    ap.add_argument("--full", action="store_true", help="print full old/new text")
    args = ap.parse_args()

    db = SessionLocal()
    docs: dict[str, MdDocument] = {}
    total_flags = 0

    for it_id in affected_items(db, args.item):
        item = db.get(AnnotationItem, it_id)
        if item.company_id not in docs:
            docs[item.company_id] = MdDocument.from_file(MD_DIR / f"{item.company_id}.md")
        sentences, irrelevant, suggested = load_feedback(db, it_id)
        new_text, flags = build_passage(docs[item.company_id], sentences, irrelevant, suggested)
        new_text = normalize_text(new_text)

        print("=" * 100)
        print(f"item {it_id}  {item.company_id}  {item.obligation_id}  "
              f"removed={sorted(irrelevant)}  suggested={len(suggested)}")
        for f in flags:
            total_flags += 1
            print(f"   [FLAG] {f}")
        if args.full or args.item:
            print("--- OLD " + "-" * 92 + f"\n{item.passage_text}")
            print("--- NEW " + "-" * 92 + f"\n{new_text}")
        else:
            print("   NEW head: " + new_text[:200].replace("\n", "\\n"))

        if args.apply:
            reseg(db, item, new_text)

    print("=" * 100)
    print(f"total flags: {total_flags}")
    if args.apply:
        db.commit()
        print(">>> COMMITTED to database.")
    else:
        db.rollback()
        print(">>> DRY-RUN: no changes written. Re-run with --apply to commit.")
    db.close()


if __name__ == "__main__":
    main()
