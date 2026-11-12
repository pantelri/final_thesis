"""Phase 5 — data base for the error analysis / failure-mode chapter.

Collects every wrong item from every cached prediction file and lays the cases
out so a taxonomy can be assigned by hand. No categorisation is done here — the
labels are the author's to give.

Source: results/preds/*.csv (company_id, obligation_id, pred_label, gt_label,
correct, reason). The `reason` column is the model's own justification for that
item. Nothing is recomputed and no API is called; the `correct` column of the
preds is taken as scored by Phase 4a/4b.

Writes:
  results/error_cases.csv          one row per wrong item:
                                   stage, model, run, company_id, obligation_id,
                                   gt_label, pred_label, reason.
  results/error_taxonomy_seed.csv  the same cases grouped by
                                   (stage, gt_label, pred_label) with the case
                                   count and the three longest reasons of the
                                   group as examples.

`run` names the prediction file the case comes from (a model appears in several
Stage-3 runs: retrieval condition x context variant), so (stage, model) alone
would collapse distinct experimental arms into one row.

Reason texts are whitespace-normalised (newlines and runs of spaces collapse to
a single space) so the CSV stays one line per case; nothing else is altered.

Run: python -m scripts.eval.phase5_error_cases
"""
from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict

from scripts.eval._common import GEN_MODELS, PREDS, RESULTS, write_csv

# preds filename prefix -> stage label. Longest prefix wins.
STAGE_BY_PREFIX = {
    "relevance_": "stage1_relevance",
    "fulfillmentbin_": "stage3_fulfillment_binary",
    "fulfillment_": "stage3_fulfillment_ternary",
}
N_EXAMPLES = 3
CASE_FIELDS = ["stage", "model", "run", "company_id", "obligation_id",
               "gt_label", "pred_label", "reason"]
SEED_FIELDS = (["stage", "gt_label", "pred_label", "n", "n_runs", "n_models", "models"]
               + [f"example_reason_{i}" for i in range(1, N_EXAMPLES + 1)])


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def _stage_of(stem: str) -> str | None:
    for prefix in sorted(STAGE_BY_PREFIX, key=len, reverse=True):
        if stem.startswith(prefix):
            return STAGE_BY_PREFIX[prefix]
    return None


def _model_of(stem: str) -> str:
    """The GEN_MODELS key contained in the file stem ('' for non-LLM runs)."""
    return next((m for m in GEN_MODELS if m in stem), "")


def collect_cases() -> list[dict]:
    cases = []
    for path in sorted(PREDS.glob("*.csv")):
        stage = _stage_of(path.stem)
        if stage is None:
            print(f"  skipped (unknown stage): {path.name}")
            continue
        with open(path, encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        for r in rows:
            if r.get("correct", "").strip() != "0":
                continue
            cases.append({
                "stage": stage, "model": _model_of(path.stem), "run": path.stem,
                "company_id": r["company_id"], "obligation_id": r["obligation_id"],
                "gt_label": r["gt_label"], "pred_label": r["pred_label"],
                "reason": _norm(r.get("reason", "")),
            })
    cases.sort(key=lambda c: (c["stage"], c["run"], c["company_id"], c["obligation_id"]))
    return cases


def taxonomy_seed(cases: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for c in cases:
        groups[(c["stage"], c["gt_label"], c["pred_label"])].append(c)
    rows = []
    for key in sorted(groups, key=lambda k: (k[0], -len(groups[k]), k[1], k[2])):
        stage, gt, pred = key
        grp = groups[key]
        longest = sorted(grp, key=lambda c: len(c["reason"]), reverse=True)[:N_EXAMPLES]
        row = {"stage": stage, "gt_label": gt, "pred_label": pred, "n": len(grp),
               "n_runs": len({c["run"] for c in grp}),
               "n_models": len({c["model"] for c in grp}),
               "models": "|".join(sorted({c["model"] for c in grp if c["model"]}))}
        for i in range(N_EXAMPLES):
            row[f"example_reason_{i + 1}"] = longest[i]["reason"] if i < len(longest) else ""
        rows.append(row)
    return rows


def main() -> None:
    cases = collect_cases()
    if not cases:
        raise SystemExit("no wrong items found in results/preds/*.csv")
    seed = taxonomy_seed(cases)
    write_csv(RESULTS / "error_cases.csv", cases, CASE_FIELDS)
    write_csv(RESULTS / "error_taxonomy_seed.csv", seed, SEED_FIELDS)

    by_stage = Counter(c["stage"] for c in cases)
    n_empty = sum(1 for c in cases if not c["reason"])
    print(f"error cases: {len(cases)} over {len({c['run'] for c in cases})} runs")
    for stage, n in sorted(by_stage.items()):
        print(f"  {stage:28} {n:>5}")
    print(f"cases without a reason text: {n_empty}")
    print(f"taxonomy seed groups: {len(seed)}")
    print(f"\nwrote 2 CSVs to {RESULTS}")


if __name__ == "__main__":
    main()
