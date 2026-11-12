#!/usr/bin/env python3
"""Export the thesis' LLM judgments into the app (for the "Auswertungen" page).

Reads the prediction CSVs of the eval harness (../results/preds/) and writes one
flat file that is baked into the Docker image:

    annotation_app/data/model_judgments.csv
    columns: model_key, model_name, company_id, obligation_id, relevance, fulfillment

relevance   : relevant | not_relevant | unclear      (Stage 1, all 182 pairs)
fulfillment : fulfilled | not_fulfilled | ""          (Stage 3, GT-applicable pairs)

Fulfillment source per model: the binary 2-option run
(fulfillmentbin_<model>_predicted_k5_rank.csv) if it exists, otherwise the older
3-option run (fulfillment_<model>_predicted_statute_only.csv) with
partially -> not_fulfilled (thesis variant A).

Run on the host from source_code/ (no DB needed):
    python annotation_app/scripts/export_model_judgments.py
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # .../source_code
PREDS = ROOT / "results" / "preds"
OUT = Path(__file__).resolve().parents[1] / "data" / "model_judgments.csv"

MODEL_NAMES = {
    "claude_opus_4_8": "Claude Opus 4.8",
    "gemini_3_1_pro": "Gemini 3.1 Pro",
    "qwen_3_7_max": "Qwen 3.7 Max",
    "mimo_v2_5_pro": "MiMo v2.5 Pro",
    "claude_sonnet_5_5": "Claude Sonnet 5.5",
    "gemini_4_argon": "Gemini 4 Argon",
    "kimi_k3": "Kimi K3",
}
FUL_MAP = {"fulfilled": "fulfilled", "not_fulfilled": "not_fulfilled",
           "partially": "not_fulfilled"}


def _read(path: Path) -> dict[tuple[str, str], str]:
    with open(path, encoding="utf-8", newline="") as fh:
        return {(r["company_id"], r["obligation_id"]): r["pred_label"].strip()
                for r in csv.DictReader(fh)}


def main() -> None:
    rows = []
    for key, name in MODEL_NAMES.items():
        rel_path = PREDS / f"relevance_{key}.csv"
        if not rel_path.exists():
            print(f"  skip {key}: no {rel_path.name}")
            continue
        rel = _read(rel_path)
        ful_path = PREDS / f"fulfillmentbin_{key}_predicted_k5_rank.csv"
        if not ful_path.exists():
            ful_path = PREDS / f"fulfillment_{key}_predicted_statute_only.csv"
        ful = _read(ful_path) if ful_path.exists() else {}
        for (c, o), r in sorted(rel.items()):
            rows.append({"model_key": key, "model_name": name, "company_id": c,
                         "obligation_id": o, "relevance": r,
                         "fulfillment": FUL_MAP.get(ful.get((c, o), ""), "")})
        n_ful = sum(1 for v in ful.values() if v in FUL_MAP)
        print(f"  {key:18} relevance={len(rel):3}  fulfillment={n_ful:3}  ({ful_path.name if ful else '-'})")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["model_key", "model_name", "company_id",
                                           "obligation_id", "relevance", "fulfillment"])
        w.writeheader()
        w.writerows(rows)
    print(f"-> {OUT} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
