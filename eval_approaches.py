"""Vergleich dreier Retrieval-Strategien auf 20 zufälligen Pflicht-Firma-Paaren.

Approach 0 (Baseline):  verification_criterion als Query
Approach 1 (Enriched):  LLM-generierter retrieval_text (semantisch nah am Berichtstext)
Approach 2 (GT-based):  GT-Text einer anderen Firma als Query (2 Läufe: 2a und 2b)

Ausgabe:
  eval_output/approach_comparison.csv    — Detailergebnisse pro Sample und Ansatz
  eval_output/approach_summary.txt       — Zusammenfassungstabelle

Voraussetzung:
  generate_enriched_requirements.py muss zuerst laufen (einmalig).
"""
from __future__ import annotations

import csv
import json
import logging
import os
import random
import sys
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

from eval_retrieval import chunk_hit_at_k, max_recall_at_k, union_coverage_at_k

from retrieval_eval.approaches_setup import (  # noqa: E402
    N_SAMPLES, SEED, TOP_N,
    _load_csv, _metrics, _safe_retrieve,
    load_requirements_baseline, load_requirements_enriched, setup_pipeline,
)


# ── Hauptauswertung ───────────────────────────────────────────────────────────

def run_comparison(n_samples: int = N_SAMPLES, seed: int = SEED) -> None:
    out_dir  = _ROOT / "eval_output"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "approach_comparison.csv"
    sum_path = out_dir / "approach_summary.txt"

    gt_pflichten  = _load_csv(_ROOT / "gt_output" / "df2_pflichten.csv")
    reqs_baseline = load_requirements_baseline()
    reqs_enriched = load_requirements_enriched()

    # GT-Index: rcode → {company → text_combined}
    gt_by_rcode: dict[str, dict[str, str]] = {}
    for row in gt_pflichten:
        gt_by_rcode.setdefault(row["rcode"], {})[row["company"]] = row["text_combined"]

    rng     = random.Random(seed)
    samples = rng.sample(gt_pflichten, min(n_samples, len(gt_pflichten)))
    logger.info("%d Stichproben ausgewählt (seed=%d).", len(samples), seed)

    module = setup_pipeline()

    fieldnames = [
        "Nr", "Pflicht", "Firma", "GT_erfuellung",
        # Approach 0
        "A0_query_preview",
        "A0_Hit@1", "A0_Hit@3", "A0_Hit@5", "A0_mr5", "A0_uc5",
        # Approach 1
        "A1_query_preview",
        "A1_Hit@1", "A1_Hit@3", "A1_Hit@5", "A1_mr5", "A1_uc5",
        # Approach 2a (GT Firma 1)
        "A2a_gt_company",
        "A2a_Hit@1", "A2a_Hit@3", "A2a_Hit@5", "A2a_mr5", "A2a_uc5",
        # Approach 2b (GT Firma 2)
        "A2b_gt_company",
        "A2b_Hit@1", "A2b_Hit@3", "A2b_Hit@5", "A2b_mr5", "A2b_uc5",
    ]

    all_rows: list[dict] = []

    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(samples, 1):
            company    = row["company"]
            rcode      = row["rcode"]
            gt_text    = row["text_combined"]
            title_de   = row.get("title_de", rcode)
            erfuellung = row.get("erfuellung", "")

            logger.info("[%d/%d] %s | %s", i, len(samples), company, rcode)

            req_b = reqs_baseline.get(rcode, {})
            req_e = reqs_enriched.get(rcode, {})

            # ── Approach 0: verification_criterion ───────────────────────────
            q0   = req_b.get("verification_criterion", title_de)
            raw0 = _safe_retrieve(module, q0, company, TOP_N)
            m0   = _metrics(raw0, gt_text)
            logger.info("  A0: Hit@5=%d  mr5=%.3f  query=%s…", m0["Hit@5"], m0["mr5"], q0[:50])

            # ── Approach 1: LLM-generierter retrieval_text ───────────────────
            q1   = req_e.get("retrieval_text") or q0   # Fallback auf Baseline
            raw1 = _safe_retrieve(module, q1, company, TOP_N)
            m1   = _metrics(raw1, gt_text)
            logger.info("  A1: Hit@5=%d  mr5=%.3f  query=%s…", m1["Hit@5"], m1["mr5"], q1[:50])

            # ── Approach 2: GT-Text anderer Firmen ───────────────────────────
            other = [
                (c, t) for c, t in gt_by_rcode.get(rcode, {}).items()
                if c != company and t.strip()
            ]
            # Reproduzierbare Auswahl: Sub-RNG pro Sample
            rng2 = random.Random(seed * 1000 + i)
            rng2.shuffle(other)
            gt_others = other[:2]

            c2a = c2b = ""
            m2a = m2b = {"Hit@1": "", "Hit@3": "", "Hit@5": "", "mr5": "", "uc5": ""}

            if len(gt_others) >= 1:
                c2a, t2a = gt_others[0]
                raw2a = _safe_retrieve(module, t2a, company, TOP_N)
                m2a   = _metrics(raw2a, gt_text)
                logger.info("  A2a [%s]: Hit@5=%s  mr5=%s", c2a, m2a["Hit@5"], m2a["mr5"])

            if len(gt_others) >= 2:
                c2b, t2b = gt_others[1]
                raw2b = _safe_retrieve(module, t2b, company, TOP_N)
                m2b   = _metrics(raw2b, gt_text)
                logger.info("  A2b [%s]: Hit@5=%s  mr5=%s", c2b, m2b["Hit@5"], m2b["mr5"])

            csv_row = {
                "Nr":              i,
                "Pflicht":         f"[{rcode}] {title_de}",
                "Firma":           company,
                "GT_erfuellung":   erfuellung,
                "A0_query_preview": q0[:80],
                "A0_Hit@1": m0["Hit@1"], "A0_Hit@3": m0["Hit@3"], "A0_Hit@5": m0["Hit@5"],
                "A0_mr5":   m0["mr5"],   "A0_uc5":   m0["uc5"],
                "A1_query_preview": q1[:80],
                "A1_Hit@1": m1["Hit@1"], "A1_Hit@3": m1["Hit@3"], "A1_Hit@5": m1["Hit@5"],
                "A1_mr5":   m1["mr5"],   "A1_uc5":   m1["uc5"],
                "A2a_gt_company": c2a,
                "A2a_Hit@1": m2a["Hit@1"], "A2a_Hit@3": m2a["Hit@3"], "A2a_Hit@5": m2a["Hit@5"],
                "A2a_mr5":   m2a["mr5"],   "A2a_uc5":   m2a["uc5"],
                "A2b_gt_company": c2b,
                "A2b_Hit@1": m2b["Hit@1"], "A2b_Hit@3": m2b["Hit@3"], "A2b_Hit@5": m2b["Hit@5"],
                "A2b_mr5":   m2b["mr5"],   "A2b_uc5":   m2b["uc5"],
            }
            writer.writerow(csv_row)
            all_rows.append(csv_row)
            f.flush()

    # ── Zusammenfassung ───────────────────────────────────────────────────────

    def avg(col: str) -> str:
        vals = [float(r[col]) for r in all_rows if r.get(col) not in ("", None)]
        return f"{sum(vals)/len(vals):.3f}" if vals else "n/a"

    def pct_hit(col: str) -> str:
        vals = [float(r[col]) for r in all_rows if r.get(col) not in ("", None)]
        return f"{sum(vals)/len(vals):.0%}" if vals else "n/a"

    approach_labels = [
        ("A0", "Approach 0 — verification_criterion (Baseline)"),
        ("A1", "Approach 1 — LLM retrieval_text (angereichert)"),
        ("A2a", "Approach 2a — GT-Text Firma 1"),
        ("A2b", "Approach 2b — GT-Text Firma 2"),
    ]

    col_w   = 30
    sep     = "=" * (col_w + 4 * 11)
    divider = "-" * (col_w + 4 * 11)

    lines = [
        sep,
        f"  Retrieval-Ansatz-Vergleich  (n={len(all_rows)}, seed={seed})",
        sep,
        "",
        f"  {'Metrik':<{col_w-2}}{'A0':>11}{'A1':>11}{'A2a':>11}{'A2b':>11}",
        "  " + divider,
        f"  {'Hit@1':<{col_w-2}}{pct_hit('A0_Hit@1'):>11}{pct_hit('A1_Hit@1'):>11}{pct_hit('A2a_Hit@1'):>11}{pct_hit('A2b_Hit@1'):>11}",
        f"  {'Hit@3':<{col_w-2}}{pct_hit('A0_Hit@3'):>11}{pct_hit('A1_Hit@3'):>11}{pct_hit('A2a_Hit@3'):>11}{pct_hit('A2b_Hit@3'):>11}",
        f"  {'Hit@5':<{col_w-2}}{pct_hit('A0_Hit@5'):>11}{pct_hit('A1_Hit@5'):>11}{pct_hit('A2a_Hit@5'):>11}{pct_hit('A2b_Hit@5'):>11}",
        f"  {'avg max_recall_top5':<{col_w-2}}{avg('A0_mr5'):>11}{avg('A1_mr5'):>11}{avg('A2a_mr5'):>11}{avg('A2b_mr5'):>11}",
        f"  {'avg union_cov_top5':<{col_w-2}}{avg('A0_uc5'):>11}{avg('A1_uc5'):>11}{avg('A2a_uc5'):>11}{avg('A2b_uc5'):>11}",
        "  " + divider,
        "",
        "  Approach 0  - verification_criterion (abstrakte Pruefbeschreibung)",
        "  Approach 1  - LLM-generierter retrieval_text (exemplarischer Berichtstext)",
        "  Approach 2a - GT-Text einer anderen Firma (Lauf 1)",
        "  Approach 2b - GT-Text einer anderen Firma (Lauf 2)",
        sep,
    ]
    summary_text = "\n".join(lines)
    print("\n" + summary_text)
    sum_path.write_text(summary_text + "\n", encoding="utf-8")

    logger.info("CSV:     %s", out_path)
    logger.info("Summary: %s", sum_path)


if __name__ == "__main__":
    run_comparison()
