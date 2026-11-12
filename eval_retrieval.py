"""Retrieval-Evaluation: SQuAD-F1 + Chunk-Level-Metriken + Offset-Spot-Check.

Ausgaben:
  eval_output/retrieval_eval_results.csv   – Haupt-Ergebnistabelle
  eval_output/raw_topk_{i}_{…}.json        – Rohe Top-k + Subspan-Overlaps vor Review-Loop
  eval_output/offset_spot_check.json       – Substring-Alignment-Prüfung (3 Fälle)
"""
from __future__ import annotations

import csv
import json
import logging
import os
import random
import re
import sys
from collections import Counter
from functools import partial
from pathlib import Path

_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

from retrieval_eval.metrics import (  # noqa: E402,F401 — re-exported for eval_approaches.py
    _STOPWORDS, _normalize_tokens, _subspan_recall_in_chunk, _token_f1,
    chunk_hit_at_k, max_recall_at_k, max_subspan_f1, squad_f1,
    subspan_overlaps, union_coverage_at_k,
)
from retrieval_eval.diagnostics import (  # noqa: E402
    agent_delta, oracle_rank_for_case, run_offset_spot_check,
)


# ── Laden ─────────────────────────────────────────────────────────────────────

def _load_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_requirements() -> dict[str, dict]:
    req_file = _ROOT / "Requirements" / "offenlegungspflichten_gefiltert.json"
    data = json.loads(req_file.read_text(encoding="utf-8"))
    reqs = data.get("requirements", data) if isinstance(data, dict) else data
    return {r["id"]: r for r in reqs}


# ── Pipeline-Setup ────────────────────────────────────────────────────────────

def setup_pipeline():
    from Ingestion.embed_pipeline import (
        COLLECTION_NAME, MODELS, _make_client, embed_query, open_collection,
    )
    from Retrieval import RetrievalReviewModule

    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY nicht gesetzt.")

    for model_key in ("qwen3", "gemini"):
        try:
            collection = open_collection(model_key, COLLECTION_NAME)
            logger.info("Collection '%s' (%d Chunks).", model_key, collection.count())
            break
        except Exception:
            logger.warning("Collection '%s' nicht gefunden.", model_key)
    else:
        raise SystemExit("Keine ChromaDB-Collection gefunden.")

    or_client = _make_client(api_key)
    embed_fn  = partial(embed_query, model_id=MODELS[model_key], client=or_client)
    return RetrievalReviewModule(collection=collection, embed_fn=embed_fn)


# ── Hauptauswertung ───────────────────────────────────────────────────────────

def run_evaluation(n_samples: int = 10, seed: int = 42) -> None:
    out_dir  = _ROOT / "eval_output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "retrieval_eval_results.csv"

    gt_pflichten = _load_csv(_ROOT / "gt_output" / "df2_pflichten.csv")
    gt_spans     = _load_csv(_ROOT / "gt_output" / "df1_spans.csv")
    requirements = load_requirements()
    samples      = random.Random(seed).sample(gt_pflichten, min(n_samples, len(gt_pflichten)))

    logger.info("%d Stichproben ausgewählt.", len(samples))
    module = setup_pipeline()

    # GT-Spans-Index für Oracle-Check: (company, label) → [span_rows]
    gt_spans_index: dict[tuple[str, str], list[dict]] = {}
    for s in gt_spans:
        key = (s["company"], s["label"])
        gt_spans_index.setdefault(key, []).append(s)

    # ── Offset-Spot-Check (einmalig) ─────────────────────────────────────────
    spot_results = run_offset_spot_check(module, gt_spans, n=3)
    spot_path = out_dir / "offset_spot_check.json"
    spot_path.write_text(json.dumps(spot_results, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Offset-Spot-Check: %s", spot_path)

    fieldnames = [
        "Pflicht", "Firma",
        "Recall", "Precision", "F1", "F1_max_subspan",
        "Hit@1", "Hit@3", "Hit@5",
        "max_recall_top5", "union_cov_top5",
        "oracle_rank",
        "n_subspans", "retrieved_chars", "gt_chars",
        "dropped_by_agent", "added_by_expand",
        "Status_der_erfuellung_laut_GT",
        "Text_Retrieved", "Text_GT",
    ]

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(samples, 1):
            company    = row["company"]
            rcode      = row["rcode"]
            label      = row["label"]
            gt_text    = row["text_combined"]
            erfuellung = row["erfuellung"]
            title_de   = row.get("title_de", rcode)
            query      = requirements.get(rcode, {}).get("verification_criterion", title_de)

            logger.info("[%d/%d] %s | %s", i, len(samples), company, rcode)

            # ── Rohe Top-5 vor Review-Loop ────────────────────────────────────
            try:
                raw = module.retrieve_raw(query, filters={"company": company}, top_n=5)
            except Exception as exc:
                logger.error("Retrieve-Fehler: %s", exc)
                raw = []

            overlaps = subspan_overlaps(raw, gt_text)
            hit1  = chunk_hit_at_k(raw, gt_text, k=1)
            hit3  = chunk_hit_at_k(raw, gt_text, k=3)
            hit5  = chunk_hit_at_k(raw, gt_text, k=5)
            mr5   = max_recall_at_k(raw, gt_text, k=5)
            uc5   = union_coverage_at_k(raw, gt_text, k=5)

            # ── Oracle-Rank (nur bei Hit@5=0) ─────────────────────────────────
            oracle_info: list[dict] = []
            oracle_rank_best: int | None = None
            if not hit5:
                oracle_info = oracle_rank_for_case(module, company, label, gt_spans_index)
                ranks = [e["oracle_rank"] for e in oracle_info if e["oracle_rank"] is not None]
                oracle_rank_best = min(ranks) if ranks else None

            # ── Voller Pipeline-Lauf mit Review-Loop ─────────────────────────
            try:
                result    = module.run(query=query, filters={"company": company}, top_n=5)
                retrieved = result.final_text
            except Exception as exc:
                logger.error("Pipeline-Fehler: %s", exc)
                result    = None
                retrieved = ""

            # ── Agent-Delta ───────────────────────────────────────────────────
            delta = agent_delta(raw, result)
            logger.info(
                "  Agent: top5=%s  used=%s  dropped=%s  expanded=%s",
                delta["top5_ids"], delta["agent_ids"],
                delta["dropped_by_agent"], delta["added_by_expand"],
            )

            # ── SQuAD-Metriken ────────────────────────────────────────────────
            recall, precision, f1 = squad_f1(retrieved, gt_text)
            f1_max = round(max_subspan_f1(retrieved, gt_text), 4)
            n_sub  = len([s for s in gt_text.split("[...]") if s.strip()])

            logger.info(
                "  F1=%.3f  F1_max=%.3f  Hit@5=%d  mr5=%.3f  uc5=%.3f  oracle=%s",
                f1, f1_max, int(hit5), mr5, uc5, oracle_rank_best,
            )

            (out_dir / f"raw_topk_{i:02d}_{company}_{rcode}.json").write_text(
                json.dumps({
                    "sample": i, "company": company, "rcode": rcode, "query": query,
                    "top_k": raw,
                    "subspan_overlaps": overlaps,
                    "oracle_info": oracle_info,
                    "agent_delta": delta,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            writer.writerow({
                "Pflicht":                       f"[{rcode}] {title_de}",
                "Firma":                         company,
                "Recall":                        recall,
                "Precision":                     precision,
                "F1":                            f1,
                "F1_max_subspan":                f1_max,
                "Hit@1":                         int(hit1),
                "Hit@3":                         int(hit3),
                "Hit@5":                         int(hit5),
                "max_recall_top5":               mr5,
                "union_cov_top5":                uc5,
                "oracle_rank":                   oracle_rank_best if oracle_rank_best is not None else "",
                "n_subspans":                    n_sub,
                "retrieved_chars":               len(retrieved),
                "gt_chars":                      len(gt_text),
                "dropped_by_agent":              "|".join(delta["dropped_by_agent"]),
                "added_by_expand":               "|".join(delta["added_by_expand"]),
                "Status_der_erfuellung_laut_GT": erfuellung,
                "Text_Retrieved":                retrieved.replace("\n", " ").strip(),
                "Text_GT":                       gt_text.replace("\n", " ").strip(),
            })
            f.flush()

    # ── Summary ───────────────────────────────────────────────────────────────
    with out_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    def avg(col: str) -> float:
        vals = [float(r[col]) for r in rows if r[col] != ""]
        return sum(vals) / len(vals) if vals else 0.0

    print("\n" + "═" * 55)
    print(f"  Ø F1              : {avg('F1'):.3f}")
    print(f"  Ø F1_max_subspan  : {avg('F1_max_subspan'):.3f}")
    print(f"  Ø Recall          : {avg('Recall'):.3f}")
    print(f"  Ø Precision       : {avg('Precision'):.3f}")
    print(f"  Hit@1             : {avg('Hit@1'):.2f}")
    print(f"  Hit@3             : {avg('Hit@3'):.2f}")
    print(f"  Hit@5             : {avg('Hit@5'):.2f}")
    print(f"  Ø max_recall_top5 : {avg('max_recall_top5'):.3f}")
    print(f"  Ø union_cov_top5  : {avg('union_cov_top5'):.3f}")
    oracle_ranks = [int(r["oracle_rank"]) for r in rows if r["oracle_rank"] != ""]
    if oracle_ranks:
        print(f"  Oracle@1 (hit=0-Fälle): {sum(r<=1 for r in oracle_ranks)}/{len(oracle_ranks)}")
        print(f"  Oracle@5 (hit=0-Fälle): {sum(r<=5 for r in oracle_ranks)}/{len(oracle_ranks)}")
        print(f"  Ø oracle_rank           : {sum(oracle_ranks)/len(oracle_ranks):.1f}")
    print("═" * 55)
    logger.info("CSV:  %s", out_path)
    logger.info("Spot: %s", spot_path)
    logger.info("Raw:  %s/raw_topk_*.json", out_dir)


if __name__ == "__main__":
    run_evaluation(n_samples=10, seed=42)
