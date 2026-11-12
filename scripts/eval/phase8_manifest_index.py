"""Phase 8 — finalize the run manifest and write the results index.

Produces two provenance artifacts:
  * results/run_manifest.csv  — model versions, factorial design, seeds, winners,
    headline numbers (key figures pulled LIVE from the result CSVs so they cannot
    drift), git commit, timestamp.
  * results/INDEX.md          — maps each thesis subsection to its source CSV(s),
    LaTeX table(s) and figure(s), with a one-line takeaway each.

Run:  python -m scripts.eval.phase8_manifest_index
"""
from __future__ import annotations

import datetime as _dt

import pandas as pd

from scripts.eval._common import (RESULTS, GLOBAL_SEED, N_BOOTSTRAP, VERIFICATION_K,
                                  N_ITEMS, N_OBLIGATIONS, N_COMPANIES, git_commit, write_csv)


def _csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def _live_numbers() -> dict:
    """Headline figures read straight from the canonical CSVs."""
    w = _csv("retrieval_winner.csv").iloc[0]
    rel = _csv("relevance_metrics_per_model.csv").sort_values("accuracy", ascending=False).iloc[0]
    ful = _csv("fulfillment_metrics_per_model.csv")
    ful_ps = ful[(ful.retrieval == "predicted") & (ful.context == "statute_only")] \
        .sort_values("accuracy", ascending=False).iloc[0]
    f2 = _csv("fulfillment_f2_comparison_md.csv").set_index("pipeline")
    abl = _csv("ablation_configs.csv").set_index("config")
    dlt = _csv("ablation_deltas_bootstrap.csv").sort_values("delta", ascending=False).iloc[0]
    return {
        "win_emb": w.embedding, "win_recall": w.recall, "win_hit": w.hit, "win_mrr": w.mrr,
        "rel_model": rel.model, "rel_acc": rel.accuracy,
        "ful_model": ful_ps.model, "ful_acc": ful_ps.accuracy,
        "p1_acc": f2.loc["P1_2option_binary", "accuracy"],
        "p1_f2": f2.loc["P1_2option_binary", "f2_needs_review"],
        "e2e_full": abl.loc["full", "cumulative_acc"],
        "e2e_ceiling": abl.loc["oracle_rel_retr", "cumulative_acc"],
        "bottleneck": dlt.isolates, "bottleneck_delta": dlt.delta, "bottleneck_sig": dlt.significant,
    }


def build_manifest() -> list[dict]:
    n = _live_numbers()
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    R = []

    def row(section, key, value):
        R.append({"section": section, "key": key, "value": value})

    # ---- meta ----
    row("meta", "manifest_status", "FINAL (Phase 8)")
    row("meta", "git_commit", git_commit())
    row("meta", "recorded_utc", now)
    row("meta", "global_seed", GLOBAL_SEED)
    row("meta", "n_bootstrap", N_BOOTSTRAP)
    row("meta", "bootstrap", "Efron percentile, N=1000 @ seed 42; significant iff 95% CI excludes 0")
    row("meta", "interpreter", "conda env thesis2; run python -m scripts.eval.<module> from repo root")

    # ---- dataset / GT ----
    row("dataset", "grid", f"{N_ITEMS} items = {N_OBLIGATIONS} obligations x {N_COMPANIES} companies")
    row("dataset", "obligations", "R02,R03,R04,R10,R11,R12,R14,R15,R17,R19,R22,R23,R24")
    row("dataset", "relevance_population", "182 scored (relevant 141 / not_relevant 37 / unclear 4)")
    row("dataset", "retrieval_population", "170 pairs (is_relevant=true)")
    row("dataset", "fulfillment_population_ternary", "141 scored, 3-class (fulfilled 104 / partially 27 / not_fulfilled 10); majority 0.738")
    row("dataset", "fulfillment_population_binary", "140 scored, 2-class (fulfilled 122 / not_fulfilled 18); majority 0.871")
    row("dataset", "binary_relabel", "2026-06-30 admin export Output/Export-ALL-26-06-30; 27 'partially' re-decided; see scripts/eval/_refresh_gt_binary.py")

    # ---- retrieval (Stage 2) ----
    row("retrieval", "eval_set", "170 pairs (is_relevant=true)")
    row("retrieval", "factorial", "2 embedding x 2 segmentation x 2 table_rep x 4 query_variant x k{1,3,5,7}")
    row("retrieval", "embeddings", "gemini=google/gemini-embedding-001 (3072d); qwen3=qwen/qwen3-embedding-8b (4096d)")
    row("retrieval", "segmentations", "baseSeg (sliding-window, 1534 chunks); sentSeg (sentence-aware, 2007 chunks); 701-char budget / 84-char overlap")
    row("retrieval", "table_rep", "raw_md (verbatim table markdown); llmdesc (Qwen3.7-Max German table description)")
    row("retrieval", "query_variants", "enriched (retrieval_text); zeroshot; oneshot (LOO); twoshot (seed 42)")
    row("retrieval", "selection_metric", "Recall@5 (operating_k aligns with verification k=5)")
    row("retrieval", "winner", "gemini / baseSeg / llmdesc / enriched @ k=5; collection google001_baseSeg_llmdesc")
    row("retrieval", "winner_recall_at5", f"{n['win_recall']:.4f}")
    row("retrieval", "winner_hit_at5", f"{n['win_hit']:.4f}")
    row("retrieval", "winner_mrr_at5", f"{n['win_mrr']:.4f}")

    # ---- Stage 1 relevance ----
    row("stage1_relevance", "task", "is_applicable -> relevant/not_relevant/unclear; one call per company, JSON")
    row("stage1_relevance", "winner", f"{n['rel_model']} (accuracy {n['rel_acc']:.4f})")
    row("stage1_relevance", "finding", "errors one-directional (over-predict relevant); relevant-recall >= 0.985; H3 unclear-avoidance near-total")

    # ---- Stage 3 fulfillment (model selection, pre-relabel) ----
    row("stage3_fulfillment", "task", "is_fulfilled; verifier judges from retrieved passages")
    row("stage3_fulfillment", "design", "4 LLMs x {predicted@5, oracle} x {statute_only, web_enriched}; 3-class GT (pre-relabel)")
    row("stage3_fulfillment", "best_ternary_predicted_statute", f"{n['ful_model']} (accuracy {n['ful_acc']:.4f})")
    row("stage3_fulfillment", "H2_context", "web_enriched does NOT help; significantly hurts gemini")
    row("stage3_fulfillment", "predicted_vs_oracle", "predicted >= oracle (sig only opus/statute) -> retrieval is not the Stage-3 bottleneck; the verdict is")

    # ---- final fulfillment pipeline (binary) ----
    row("final_pipeline", "decision", "P1 = 2-option binary prompt (fulfilled/not_fulfilled); user choice 2026-06-30")
    row("final_pipeline", "model", "qwen_3_7_max / predicted@5 (rank order) / statute_only")
    row("final_pipeline", "accuracy_binary", f"{n['p1_acc']:.4f} (majority 0.871)")
    row("final_pipeline", "f2_needs_review", f"{n['p1_f2']:.4f}")
    row("final_pipeline", "binary_vs_ternary", "2 options does NOT beat 3-class collapse or the 0.871 baseline; F2 study in results/F2_pipeline_comparison.md")

    # ---- RQ5 ----
    row("rq5_passage_position", "arms", "top-5 rank / top-1 / top-5 doc-order / top-5 relevance-last (binary GT)")
    row("rq5_passage_position", "finding", "order is noise (no U-shape); top-1 << top-5 (delta -0.157, sig)")

    # ---- e2e (Phase 6) ----
    row("e2e", "pipeline", "best-of-breed: gemini S1 + retrieval winner + qwen S3 (binary); 140 pairs")
    row("e2e", "metric", "cumulative correctness (all required stages right; correct verdict on wrong span = error)")
    row("e2e", "full_accuracy", f"{n['e2e_full']:.4f}")
    row("e2e", "oracle_ceiling_rel_retr", f"{n['e2e_ceiling']:.4f} (Stage-3 caps the pipeline)")
    row("e2e", "bottleneck", f"{n['bottleneck']} (delta {n['bottleneck_delta']:+.4f}, significant={n['bottleneck_sig']})")

    # ---- verification settings ----
    row("verification", "k", VERIFICATION_K)
    row("verification", "context_variants", "statute_only (legal_basis + verification_criterion); web_enriched")

    # ---- generation models ----
    row("gen_models", "claude_opus_4_8", "anthropic/claude-opus-4-8")
    row("gen_models", "gemini_3_1_pro", "google/gemini-3.1-pro-preview")
    row("gen_models", "qwen_3_7_max", "qwen/qwen3.7-max")
    row("gen_models", "mimo_v2_5_pro", "xiaomi/mimo-v2.5-pro")
    row("gen_models", "bert_nli", "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7 (baseline, not run to completion)")
    return R


INDEX_SECTIONS = [
    ("Dataset & ground truth", [
        ("CSV", "gt_label_distribution_relevance.csv, gt_label_distribution_fulfillment.csv, gt_span_stats.csv, gt_sanity_report.csv"),
        ("Tables", "tab_gt_dist_relevance, tab_gt_dist_fulfillment, tab_gt_span_stats, tab_gt_sanity"),
        ("Takeaway", "182-item grid; binary fulfillment GT 122/18 (majority 0.871); GT evidence 97.1% located."),
    ]),
    ("Stage 2 — Retrieval", [
        ("CSV", "retrieval_metrics.csv, recall_at_k_curve.csv, retrieval_main_effects.csv, retrieval_per_requirement.csv, retrieval_winner.csv"),
        ("Tables", "tab_retrieval_winner, tab_retrieval_topk, tab_retrieval_main_effects, tab_retrieval_per_requirement"),
        ("Figures", "fig_recall_at_k.pdf, fig_retrieval_per_requirement.pdf"),
        ("Takeaway", "Winner gemini/baseSeg/llmdesc/enriched @k=5 (Recall@5 0.689). Embedding is the dominant factor; R12 is the hardest obligation."),
    ]),
    ("Stage 1 — Relevance classification", [
        ("CSV", "relevance_metrics_per_model.csv, relevance_confusion.csv, relevance_per_requirement.csv, relevance_h3_unclear_avoidance.csv"),
        ("Tables", "tab_relevance_models, tab_relevance_h3, tab_relevance_per_requirement"),
        ("Figures", "fig_relevance_per_requirement.pdf, fig_relevance_confusion.pdf"),
        ("Takeaway", "Gemini 3.1 Pro best (0.918). Errors one-directional (over-predict relevant) = safe for a completeness check; unclear class near-unrecoverable (H3)."),
    ]),
    ("Stage 3 — Fulfillment (model selection, 3-class, pre-relabel)", [
        ("CSV", "fulfillment_metrics_per_model.csv, fulfillment_context_variants.csv, fulfillment_retrieval_conditions.csv, fulfillment_confusion.csv"),
        ("Tables", "tab_fulfillment_models_ternary, tab_fulfillment_context_h2, tab_fulfillment_retrieval_conditions"),
        ("Figures", "fig_fulfillment_confusion.pdf"),
        ("Takeaway", "On the 3-class GT all models sit below the 0.738 majority (auditor-conservative). H2 web-enriched hurts; predicted>=oracle => the verdict, not retrieval, is the bottleneck."),
    ]),
    ("Output-scheme study & final pipeline (binary GT)", [
        ("CSV", "fulfillment_binary_vs_ternary.csv, fulfillment_binary_vs_ternary_delta.csv, fulfillment_f2_comparison.csv"),
        ("Tables", "tab_binary_vs_ternary, tab_binary_vs_ternary_delta, tab_f2_pipeline"),
        ("Figures", "fig_f2_pipeline.pdf"),
        ("Doc", "results/F2_pipeline_comparison.md"),
        ("Takeaway", "Final system = P1 2-option binary prompt. 2 options does not beat 3-class collapse or the 0.871 baseline; F2 favours the recall-oriented P3 but P1 was chosen for simplicity."),
    ]),
    ("RQ5 — Evidence passage position", [
        ("CSV", "rq5_passage_ordering.csv, rq5_ordering_deltas.csv"),
        ("Tables", "tab_rq5_ordering, tab_rq5_deltas"),
        ("Figures", "fig_rq5_ordering.pdf"),
        ("Takeaway", "Passage order is noise (no U-shaped-attention effect); passage count matters — top-1 is 15.7 pts worse than top-5."),
    ]),
    ("End-to-end & oracle ablation (Phase 6)", [
        ("CSV", "e2e_cumulative.csv, ablation_configs.csv, ablation_deltas_bootstrap.csv"),
        ("Tables", "tab_e2e_ablation, tab_e2e_deltas"),
        ("Figures", "fig_e2e_cumulative.pdf, fig_e2e_ablation_deltas.pdf"),
        ("Takeaway", "Full pipeline 0.729; perfect upstream still caps at 0.750 => Stage-3 fulfillment is the ceiling. Ablation deltas all non-significant."),
    ]),
    ("Reproducibility", [
        ("CSV", "run_manifest.csv"),
        ("Tables", "tab_run_manifest"),
        ("Takeaway", "Seeds, model slugs, factorial design, winners and git commit. Regenerate tables/figures: python -m scripts.eval.phase7_tables ; phase7_figures."),
    ]),
]


def build_index() -> str:
    n = _live_numbers()
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    out = [f"# Results Index\n",
           f"_Generated {now} (Phase 8). Maps thesis sections to their source CSVs, "
           f"LaTeX tables (`results/latex/`) and figures (`results/figures/`)._\n",
           "## Headline numbers\n",
           f"- **Retrieval** winner Recall@5 = {n['win_recall']:.3f} (gemini/baseSeg/llmdesc/enriched)",
           f"- **Stage 1** best = {n['rel_model']} at {n['rel_acc']:.3f}",
           f"- **Stage 3** final pipeline (P1, binary) = {n['p1_acc']:.3f}; F2(needs-review) = {n['p1_f2']:.3f}; majority 0.871",
           f"- **End-to-end** full = {n['e2e_full']:.3f}; oracle ceiling = {n['e2e_ceiling']:.3f} (Stage-3 caps the pipeline)\n"]
    for title, items in INDEX_SECTIONS:
        out.append(f"## {title}\n")
        for label, val in items:
            out.append(f"- **{label}:** {val}")
        out.append("")
    return "\n".join(out)


def main() -> None:
    rows = build_manifest()
    write_csv(RESULTS / "run_manifest.csv", rows, ["section", "key", "value"])
    (RESULTS / "INDEX.md").write_text(build_index(), encoding="utf-8")
    print(f"wrote results/run_manifest.csv ({len(rows)} rows)")
    print(f"wrote results/INDEX.md ({len(INDEX_SECTIONS)} sections)")


if __name__ == "__main__":
    main()
