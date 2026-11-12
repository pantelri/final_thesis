"""Reshape the server admin export (2-class fulfillment GT) into the frozen
`_db_export` annotations schema, written as `annotations_binary.csv`.

The admin CSV (`Output/Export-ALL-26-06-30/annotations.csv`) is a superset with
joined company/obligation columns; the harness loader expects the lean
annotation-only schema. Items/obligations/companies are unchanged, so only the
annotations table is refreshed; the binary GT becomes a sibling file selected via
`_load_gt.gt_master(binary=True)`.

After the 2026-06-30 relabeling: is_fulfilled is now yes/no only (the 27 former
'partially' rows were re-decided). Run once after pulling a new export.
"""
from pathlib import Path

import pandas as pd

from scripts.eval._common import RESULTS

SRC = RESULTS.parent / "Output" / "Export-ALL-26-06-30" / "annotations.csv"
DST = RESULTS / "_db_export" / "annotations_binary.csv"
SCHEMA = ["annotation_id", "item_id", "annotator_id", "is_relevant",
          "length_judgment", "is_applicable", "is_fulfilled",
          "comment", "missing_info", "submitted_at"]
PRUEFER_A = 1


def main() -> None:
    df = pd.read_csv(SRC, dtype=str, keep_default_na=False, na_values=[])
    df = df[df["annotator_id"] == str(PRUEFER_A)]
    out = df[SCHEMA].copy()

    n = len(out)
    ful = out["is_fulfilled"].replace("", pd.NA)
    assert n == 182, f"expected 182 Pruefer-A items, got {n}"
    assert not (ful == "partially").any(), "binary GT still contains 'partially'"
    DST.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(DST, index=False)
    print(f"Wrote {DST}  ({n} rows)")
    print("is_fulfilled:", out["is_fulfilled"].replace("", "(blank)").value_counts().to_dict())
    print("is_applicable:", out["is_applicable"].value_counts().to_dict())


if __name__ == "__main__":
    main()
