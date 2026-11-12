"""Write per-run prediction outputs for a classification stage.

Given a `stem` and rows (each carrying company_id, obligation_id, pred_label,
gt_label, correct, reason, raw), writes into results/preds/:
  <stem>.csv        the scored rows (no raw text)
  <stem>_raw.jsonl  one row per item: company/obligation/model/raw/label
  <stem>.md         run log: n, parse failures, accuracy, gt->pred confusion
Reusable across stages (relevance, fulfillment, ...).
"""
from __future__ import annotations

import json
from collections import Counter

from scripts.eval._common import PREDS, write_csv

CSV_COLS = ["company_id", "obligation_id", "pred_label", "gt_label", "correct", "reason"]


def write_predictions(stem: str, model_id: str, rows: list[dict]) -> None:
    write_csv(PREDS / f"{stem}.csv", [{k: r[k] for k in CSV_COLS} for r in rows], CSV_COLS)
    raw = [json.dumps({"company_id": r["company_id"], "obligation_id": r["obligation_id"],
                       "model": model_id, "raw": r["raw"], "label": r["pred_label"]},
                      ensure_ascii=False) for r in rows]
    (PREDS / f"{stem}_raw.jsonl").write_text("\n".join(raw) + "\n", encoding="utf-8")
    _write_md(stem, model_id, rows)


def _write_md(stem: str, model_id: str, rows: list[dict]) -> None:
    n_fail = sum(1 for r in rows if not r["pred_label"])
    scored = [r for r in rows if r["gt_label"] and r["pred_label"]]
    acc = sum(r["correct"] for r in scored) / len(scored) if scored else float("nan")
    conf = Counter((r["gt_label"], r["pred_label"]) for r in scored)
    lines = [f"# {stem}", "", f"- model: `{model_id}`",
             f"- pairs: {len(rows)}  scored: {len(scored)}  parse failures: {n_fail}",
             f"- **accuracy: {acc:.4f}**", "", "## confusion (gt -> pred)", "",
             "| gt | pred | n |", "|----|------|---|"]
    lines += [f"| {g} | {p} | {n} |" for (g, p), n in sorted(conf.items(), key=lambda x: -x[1])]
    (PREDS / f"{stem}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  -> {stem}: accuracy {acc:.4f}  (parse failures {n_fail})")
