#!/usr/bin/env python3
"""
Import reference data and annotation items from source files.

Usage:
    cd annotation_app
    python -m scripts.import_data --data-root /data

Options:
    --data-root PATH         Path to the source_code directory (default: DATA_ROOT env or parent)
    --overlap-fraction FLOAT Fraction of items per obligation for overlap set (default: 0.30)
    --min-per-obligation INT Minimum overlap items per obligation (default: 3)
    --seed INT               Random seed for reproducible overlap selection (default: 42)
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from app.database import SessionLocal
from scripts.db_import import import_annotation_items, import_companies, import_obligations


def main() -> None:
    parser = argparse.ArgumentParser(description="Import HGB annotation data")
    parser.add_argument(
        "--data-root",
        default=os.environ.get("DATA_ROOT", str(Path(__file__).parent.parent.parent)),
        help="Path to the source_code directory",
    )
    parser.add_argument("--overlap-fraction", type=float, default=0.30)
    parser.add_argument("--min-per-obligation", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    root = Path(args.data_root)
    paths = {
        "reqs_json": root / "Requirements" / "offenlegungspflichten_gefiltert.json",
        "md_dir":    root / "Output" / "md_files",
        "df2_path":  root / "gt_output" / "df2_pflichten.csv",
        "df1_path":  root / "gt_output" / "df1_spans.csv",
    }
    for name, p in paths.items():
        if not p.exists():
            print(f"ERROR: expected path not found: {p}")
            sys.exit(1)

    pdf_dir = root / "Input"
    print(f"Seed: {args.seed}  |  overlap_fraction: {args.overlap_fraction}"
          f"  |  min_per_obligation: {args.min_per_obligation}\n")

    db = SessionLocal()
    try:
        print("Importing obligations …")
        print(f"  → {import_obligations(db, paths['reqs_json'])} new obligations\n")

        print("Importing companies …")
        print(f"  → {import_companies(db, paths['md_dir'], pdf_dir)} new companies\n")

        print("Importing annotation items + passage sentences …")
        imp, skip, stats = import_annotation_items(
            db, paths["df2_path"], paths["df1_path"],
            args.overlap_fraction, args.min_per_obligation, args.seed,
        )
        print(f"  → {imp} items imported, {skip} skipped\n")
    finally:
        db.close()

    print("─" * 68)
    print(f"{'Pflicht':<8}  {'Titel':<38}  {'Einh.':>5}  {'Overlap':>7}")
    print("─" * 68)
    total_items = total_overlap = 0
    for rcode in sorted(stats):
        s = stats[rcode]
        title = (s["title"] or rcode)[:38]
        print(f"{rcode:<8}  {title:<38}  {s['total']:>5}  {s['overlap']:>7}")
        total_items += s["total"]
        total_overlap += s["overlap"]
    print("─" * 68)
    print(f"{'GESAMT':<8}  {'':38}  {total_items:>5}  {total_overlap:>7}")
    print("─" * 68)
    print(f"\nParameter: seed={args.seed}, fraction={args.overlap_fraction}, "
          f"min_per_obligation={args.min_per_obligation}")
    print("Done.")


if __name__ == "__main__":
    main()
