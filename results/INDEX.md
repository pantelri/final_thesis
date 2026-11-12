# Results Index

_Generated 2026-06-30 (Phase 8). Maps thesis sections to their source CSVs, LaTeX tables (`results/latex/`) and figures (`results/figures/`)._

## Headline numbers

- **Retrieval** winner Recall@5 = 0.689 (gemini/baseSeg/llmdesc/enriched)
- **Stage 1** best = gemini_3_1_pro at 0.918
- **Stage 3** final pipeline (P1, binary) = 0.757; F2(needs-review) = 0.463; majority 0.871
- **End-to-end** full = 0.729; oracle ceiling = 0.750 (Stage-3 caps the pipeline)

## Dataset & ground truth

- **CSV:** gt_label_distribution_relevance.csv, gt_label_distribution_fulfillment.csv, gt_span_stats.csv, gt_sanity_report.csv
- **Tables:** tab_gt_dist_relevance, tab_gt_dist_fulfillment, tab_gt_span_stats, tab_gt_sanity
- **Takeaway:** 182-item grid; binary fulfillment GT 122/18 (majority 0.871); GT evidence 97.1% located.

## Stage 2 — Retrieval

- **CSV:** retrieval_metrics.csv, recall_at_k_curve.csv, retrieval_main_effects.csv, retrieval_per_requirement.csv, retrieval_winner.csv
- **Tables:** tab_retrieval_winner, tab_retrieval_topk, tab_retrieval_main_effects, tab_retrieval_per_requirement
- **Figures:** fig_recall_at_k.pdf, fig_retrieval_per_requirement.pdf
- **Takeaway:** Winner gemini/baseSeg/llmdesc/enriched @k=5 (Recall@5 0.689). Embedding is the dominant factor; R12 is the hardest obligation.

## Stage 1 — Relevance classification

- **CSV:** relevance_metrics_per_model.csv, relevance_confusion.csv, relevance_per_requirement.csv, relevance_h3_unclear_avoidance.csv
- **Tables:** tab_relevance_models, tab_relevance_h3, tab_relevance_per_requirement
- **Figures:** fig_relevance_per_requirement.pdf, fig_relevance_confusion.pdf
- **Takeaway:** Gemini 3.1 Pro best (0.918). Errors one-directional (over-predict relevant) = safe for a completeness check; unclear class near-unrecoverable (H3).

## Stage 3 — Fulfillment (model selection, 3-class, pre-relabel)

- **CSV:** fulfillment_metrics_per_model.csv, fulfillment_context_variants.csv, fulfillment_retrieval_conditions.csv, fulfillment_confusion.csv
- **Tables:** tab_fulfillment_models_ternary, tab_fulfillment_context_h2, tab_fulfillment_retrieval_conditions
- **Figures:** fig_fulfillment_confusion.pdf
- **Takeaway:** On the 3-class GT all models sit below the 0.738 majority (auditor-conservative). H2 web-enriched hurts; predicted>=oracle => the verdict, not retrieval, is the bottleneck.

## Output-scheme study & final pipeline (binary GT)

- **CSV:** fulfillment_binary_vs_ternary.csv, fulfillment_binary_vs_ternary_delta.csv, fulfillment_f2_comparison.csv
- **Tables:** tab_binary_vs_ternary, tab_binary_vs_ternary_delta, tab_f2_pipeline
- **Figures:** fig_f2_pipeline.pdf
- **Doc:** results/F2_pipeline_comparison.md
- **Takeaway:** Final system = P1 2-option binary prompt. 2 options does not beat 3-class collapse or the 0.871 baseline; F2 favours the recall-oriented P3 but P1 was chosen for simplicity.

## RQ5 — Evidence passage position

- **CSV:** rq5_passage_ordering.csv, rq5_ordering_deltas.csv
- **Tables:** tab_rq5_ordering, tab_rq5_deltas
- **Figures:** fig_rq5_ordering.pdf
- **Takeaway:** Passage order is noise (no U-shaped-attention effect); passage count matters — top-1 is 15.7 pts worse than top-5.

## End-to-end & oracle ablation (Phase 6)

- **CSV:** e2e_cumulative.csv, ablation_configs.csv, ablation_deltas_bootstrap.csv
- **Tables:** tab_e2e_ablation, tab_e2e_deltas
- **Figures:** fig_e2e_cumulative.pdf, fig_e2e_ablation_deltas.pdf
- **Takeaway:** Full pipeline 0.729; perfect upstream still caps at 0.750 => Stage-3 fulfillment is the ceiling. Ablation deltas all non-significant.

## Reproducibility

- **CSV:** run_manifest.csv
- **Tables:** tab_run_manifest
- **Takeaway:** Seeds, model slugs, factorial design, winners and git commit. Regenerate tables/figures: python -m scripts.eval.phase7_tables ; phase7_figures.
