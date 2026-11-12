"""Phase 7 — booktabs LaTeX tables from the canonical result CSVs.

Reads ONLY from results/*.csv (no recomputation) and writes one .tex file per
table into results/latex/. Point decimals, English captions/headers. Tables that
draw on the pre-relabel 3-class GT (the 4-model H1/H2 fulfillment comparison) are
captioned as such; the final-system tables use the binary GT and the 2-option
(P1) pipeline.

Run:  python -m scripts.eval.phase7_tables
"""
from __future__ import annotations

import pandas as pd

from scripts.eval._common import RESULTS

LATEX = RESULTS / "latex"

MODEL_PRETTY = {
    "claude_opus_4_8": "Claude Opus 4.8",
    "gemini_3_1_pro": "Gemini 3.1 Pro",
    "qwen_3_7_max": "Qwen 3.7 Max",
    "mimo_v2_5_pro": "MiMo v2.5 Pro",
}
ARM_PRETTY = {
    "binary": "2-option (binary prompt)",
    "ternary_A_partially_to_not_fulfilled": "3-option, partially$\\to$not\\_fulfilled",
    "ternary_B_partially_to_fulfilled": "3-option, partially$\\to$fulfilled",
    "majority_baseline": "Majority baseline",
    "k5_rank": "top-5, rank order",
    "k1_rank": "top-1",
    "k5_doc": "top-5, document order",
    "k5_relevancelast": "top-5, relevance-last",
    "P1_2option_binary": "P1: 2-option (binary)",
    "P2_3option_optimistic": "P2: 3-option, optimistic",
    "P3_3option_fine_review": "P3: 3-option, fine/needs-review",
}
CONFIG_PRETTY = {
    "full": "Full pipeline",
    "oracle_rel": "Oracle relevance",
    "oracle_retr": "Oracle retrieval",
    "oracle_rel_retr": "Oracle rel.\\,+\\,retr.",
    "full_oracle": "Full oracle (ceiling)",
}


def esc(s) -> str:
    s = str(s)
    for a, b in [("\\", r"\textbackslash{}"), ("_", r"\_"), ("%", r"\%"),
                 ("&", r"\&"), ("#", r"\#")]:
        if a == "\\" and ("$" in s or "\\to" in s or "\\," in s or "\\_" in s):
            continue  # already-LaTeX strings from the PRETTY maps pass through
        s = s.replace(a, b)
    return s


def f3(x, nd: int = 3) -> str:
    if pd.isna(x):
        return "--"
    try:
        v = float(x)
    except (TypeError, ValueError):
        return esc(x)
    if v.is_integer():
        return str(int(v))
    return f"{v:.{nd}f}"


def ci(lo, hi) -> str:
    if pd.isna(lo) or pd.isna(hi):
        return "--"
    return f"[{float(lo):.3f}, {float(hi):.3f}]"


def pretty(val, mapping: dict) -> str:
    return mapping.get(str(val), esc(val))


def table(rows, header, caption, label, colspec=None, note=None) -> str:
    ncol = len(header)
    colspec = colspec or ("l" + "r" * (ncol - 1))
    out = [r"\begin{table}[htbp]", r"  \centering",
           f"  \\caption{{{caption}}}", f"  \\label{{{label}}}",
           f"  \\begin{{tabular}}{{{colspec}}}", r"    \toprule",
           "    " + " & ".join(header) + r" \\", r"    \midrule"]
    out += ["    " + " & ".join(r) + r" \\" for r in rows]
    out += [r"    \bottomrule", r"  \end{tabular}"]
    if note:
        out.append(f"  \\par\\smallskip\\footnotesize {note}")
    out += [r"\end{table}", ""]
    return "\n".join(out)


def write(name: str, content: str) -> str:
    p = LATEX / name
    p.write_text(content, encoding="utf-8")
    return name


def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


# ---------------------------------------------------------------- retrieval ----
def t_retrieval_winner() -> str:
    d = csv("retrieval_winner.csv").iloc[0]
    rows = [[esc(d.embedding), esc(d.segmentation), esc(d.table_rep),
             esc(d.query_variant), str(int(d.k)),
             f3(d.recall), f3(d.hit), f3(d.mrr)]]
    return write("tab_retrieval_winner.tex", table(
        rows, ["Embedding", "Segmentation", "Table rep.", "Query", "$k$",
               "Recall", "Hit", "MRR"],
        "Best retrieval configuration (selected by Recall@5).",
        "tab:retrieval-winner"))


def t_retrieval_topk() -> str:
    d = csv("retrieval_metrics.csv")
    w = d[(d.embedding == "gemini") & (d.segmentation == "baseSeg") &
          (d.table_rep == "llmdesc") & (d.query_variant == "enriched")].sort_values("k")
    rows = [[str(int(r.k)), f3(r.recall_mean), f3(r.hit_mean),
             f3(r.precision_mean), f3(r.mrr_mean)] for r in w.itertuples()]
    return write("tab_retrieval_topk.tex", table(
        rows, ["$k$", "Recall", "Hit", "Precision", "MRR"],
        "Retrieval metrics of the winning configuration across $k$.",
        "tab:retrieval-topk"))


def t_retrieval_main_effects() -> str:
    d = csv("retrieval_main_effects.csv")
    rows = [[esc(r.factor), esc(r.level), f3(r.recall_mean)] for r in d.itertuples()]
    return write("tab_retrieval_main_effects.tex", table(
        rows, ["Factor", "Level", "Mean Recall@5"],
        "Main effects of the retrieval design factors on mean Recall@5.",
        "tab:retrieval-main-effects", colspec="llr"))


def t_retrieval_per_req() -> str:
    d = csv("retrieval_per_requirement.csv").sort_values("recall_mean")
    rows = [[esc(r.obligation), str(int(r.n_pairs)), f3(r.recall_mean),
             f3(r.hit_mean), f3(r.mrr_mean)] for r in d.itertuples()]
    return write("tab_retrieval_per_requirement.tex", table(
        rows, ["Obligation", "$n$", "Recall@5", "Hit@5", "MRR"],
        "Retrieval performance per obligation (winning configuration), sorted by Recall@5.",
        "tab:retrieval-per-req"))


# ------------------------------------------------------------------ stage-1 ----
def t_relevance_models() -> str:
    d = csv("relevance_metrics_per_model.csv").sort_values("accuracy", ascending=False)
    rows = [[pretty(r.model, MODEL_PRETTY), str(int(r.n_scored)),
             f3(r.accuracy), ci(r.acc_ci_lo, r.acc_ci_hi), f3(r.macro_f1),
             f3(r.recall_relevant), f3(r.recall_not_relevant)] for r in d.itertuples()]
    return write("tab_relevance_models.tex", table(
        rows, ["Model", "$n$", "Acc.", "95\\% CI", "Macro-F1",
               "Rec. rel.", "Rec. not\\_rel."],
        "Stage-1 relevance classification per model ($n=182$).",
        "tab:relevance-models",
        note="Recall on the \\emph{unclear} class is omitted (support $=4$; see Tab.~\\ref{tab:relevance-h3})."))


def t_relevance_h3() -> str:
    d = csv("relevance_h3_unclear_avoidance.csv")
    rows = [[pretty(r.model, MODEL_PRETTY), str(int(r.n_pred_unclear)),
             f3(r.pred_unclear_rate), str(int(r.n_gt_unclear)),
             f3(r.gt_unclear_recall), f3(r.unclear_avoidance_rate)] for r in d.itertuples()]
    return write("tab_relevance_h3.tex", table(
        rows, ["Model", "\\#pred unclear", "Rate", "\\#GT unclear",
               "GT-unclear recall", "Avoidance"],
        "H3: model handling of \\emph{unclear} relevance judgments.",
        "tab:relevance-h3"))


def t_relevance_per_req() -> str:
    d = csv("relevance_per_requirement.csv")
    piv = d.pivot(index="obligation_id", columns="model", values="accuracy")
    models = [m for m in MODEL_PRETTY if m in piv.columns]
    piv = piv[models]
    rows = [[esc(ob)] + [f3(piv.loc[ob, m]) for m in models] for ob in piv.index]
    header = ["Obligation"] + [pretty(m, MODEL_PRETTY) for m in models]
    return write("tab_relevance_per_requirement.tex", table(
        rows, header,
        "Stage-1 relevance accuracy per obligation and model.",
        "tab:relevance-per-req"))


# ------------------------------------------------------------------ stage-3 ----
def t_fulfillment_models_ternary() -> str:
    d = csv("fulfillment_metrics_per_model.csv")
    w = d[(d.retrieval == "predicted") & (d.context == "statute_only")].sort_values(
        "accuracy", ascending=False)
    rows = [[pretty(r.model, MODEL_PRETTY), f3(r.accuracy), ci(r.acc_ci_lo, r.acc_ci_hi),
             f3(r.macro_f1), f3(r.f1_fulfilled), f3(r.f1_partially), f3(r.f1_not_fulfilled)]
            for r in w.itertuples()]
    return write("tab_fulfillment_models_ternary.tex", table(
        rows, ["Model", "Acc.", "95\\% CI", "Macro-F1", "F1 ful.", "F1 part.", "F1 not\\_ful."],
        "Stage-3 fulfillment per model on the \\textbf{3-class GT (pre-relabel)}, "
        "predicted@5 / statute-only. Majority baseline $=0.738$.",
        "tab:fulfillment-models-ternary"))


def t_fulfillment_context_h2() -> str:
    d = csv("fulfillment_context_variants.csv")
    rows = [[pretty(r.model, MODEL_PRETTY), esc(r.retrieval), f3(r.acc_web_enriched),
             f3(r.acc_statute_only), f3(r.delta_web_minus_statute),
             ci(r.ci_lo, r.ci_hi), esc(r.significant)] for r in d.itertuples()]
    return write("tab_fulfillment_context_h2.tex", table(
        rows, ["Model", "Retrieval", "Acc. web", "Acc. statute",
               "$\\Delta$ web$-$statute", "95\\% CI", "Sig."],
        "H2: web-enriched vs.\\ statute-only verification context "
        "(3-class GT, pre-relabel).",
        "tab:fulfillment-h2", colspec="llrrrrc"))


def t_fulfillment_retrieval_conditions() -> str:
    d = csv("fulfillment_retrieval_conditions.csv")
    rows = [[pretty(r.model, MODEL_PRETTY), esc(r.context), f3(r.acc_predicted),
             f3(r.acc_oracle), f3(r.delta_predicted_minus_oracle),
             ci(r.ci_lo, r.ci_hi), esc(r.significant)] for r in d.itertuples()]
    return write("tab_fulfillment_retrieval_conditions.tex", table(
        rows, ["Model", "Context", "Acc. pred.", "Acc. oracle",
               "$\\Delta$ pred$-$oracle", "95\\% CI", "Sig."],
        "Predicted@5 vs.\\ oracle evidence for Stage-3 (3-class GT, pre-relabel).",
        "tab:fulfillment-retrieval", colspec="llrrrrc"))


def t_gt_span_stats() -> str:
    d = csv("gt_span_stats.csv")
    rows = [[esc(r.scope), str(int(r.n_pairs)), str(int(r.n_span_elements)),
             f3(r.spans_per_pair_mean, 2), f3(r.chars_per_span_median, 0),
             f3(r.pct_table, 1), f3(r.pct_located, 1)] for r in d.itertuples()]
    return write("tab_gt_span_stats.tex", table(
        rows, ["Scope", "$n$ pairs", "\\#spans", "Spans/pair",
               "Chars/span (med.)", "\\% table", "\\% located"],
        "Ground-truth evidence-span statistics, overall and per obligation.",
        "tab:gt-span-stats"))


# --------------------------------------------- output-scheme / RQ5 / e2e ----
def t_binary_vs_ternary() -> str:
    d = csv("fulfillment_binary_vs_ternary.csv")
    rows = [[pretty(r.arm, ARM_PRETTY), f3(r.accuracy), ci(r.acc_ci_lo, r.acc_ci_hi),
             f3(r.macro_f1), f3(r.f1_fulfilled), f3(r.f1_not_fulfilled),
             f3(r.recall_not_fulfilled)] for r in d.itertuples()]
    return write("tab_binary_vs_ternary.tex", table(
        rows, ["Scheme", "Acc.", "95\\% CI", "Macro-F1", "F1 ful.",
               "F1 not\\_ful.", "Rec. not\\_ful."],
        "2-option prompt vs.\\ collapsed 3-class predictions on the binary GT "
        "(Qwen winner, predicted@5). Majority baseline $=0.871$.",
        "tab:binary-vs-ternary"))


def t_binary_vs_ternary_delta() -> str:
    d = csv("fulfillment_binary_vs_ternary_delta.csv")
    label = {"binary_minus_ternary_A_partially_to_not_fulfilled":
             "binary $-$ ternary (partially$\\to$not\\_ful.)",
             "binary_minus_ternary_B_partially_to_fulfilled":
             "binary $-$ ternary (partially$\\to$ful.)"}
    rows = [[label.get(r.comparison, esc(r.comparison)), f3(r.delta),
             ci(r.ci_lo, r.ci_hi), esc(r.significant)] for r in d.itertuples()]
    return write("tab_binary_vs_ternary_delta.tex", table(
        rows, ["Comparison", "$\\Delta$ acc.", "95\\% CI", "Sig."],
        "Paired bootstrap deltas: binary prompt vs.\\ each 3-class collapse.",
        "tab:binary-vs-ternary-delta", colspec="lrrc"))


def t_f2_pipeline() -> str:
    d = csv("fulfillment_f2_comparison_md.csv")
    rows = [[pretty(r.pipeline, ARM_PRETTY), f3(r.accuracy), f3(r.macro_f1), f3(r.macro_f2),
             f3(r.recall_needs_review), f3(r.f1_needs_review), f3(r.f2_needs_review),
             ci(r.f2_needs_review_ci_lo, r.f2_needs_review_ci_hi)] for r in d.itertuples()]
    return write("tab_f2_pipeline.tex", table(
        rows, ["Pipeline", "Acc.", "Macro-F1", "Macro-F2", "Rec. (review)",
               "F1 (review)", "F2 (review)", "F2 95\\% CI"],
        "Output-scheme comparison on the binary GT: F1/F2 on the "
        "\\emph{needs-review} class (Qwen winner). Support (review) $=18$.",
        "tab:f2-pipeline"))


def t_rq5_ordering() -> str:
    d = csv("rq5_passage_ordering.csv")
    rows = [[pretty(r.arm, ARM_PRETTY), f3(r.accuracy), ci(r.acc_ci_lo, r.acc_ci_hi),
             f3(r.macro_f1), f3(r.recall_fulfilled), f3(r.recall_not_fulfilled)]
            for r in d.itertuples()]
    return write("tab_rq5_ordering.tex", table(
        rows, ["Evidence arm", "Acc.", "95\\% CI", "Macro-F1",
               "Rec. ful.", "Rec. not\\_ful."],
        "RQ5: effect of evidence-passage count and position on Stage-3 "
        "fulfillment (binary GT, Qwen winner).",
        "tab:rq5-ordering"))


def t_rq5_deltas() -> str:
    d = csv("rq5_ordering_deltas.csv")
    rows = [[pretty(r.arm, ARM_PRETTY), f3(r.delta), ci(r.ci_lo, r.ci_hi), esc(r.significant)]
            for r in d.itertuples()]
    return write("tab_rq5_deltas.tex", table(
        rows, ["Arm", "$\\Delta$ vs.\\ top-5 rank", "95\\% CI", "Sig."],
        "RQ5 paired bootstrap deltas vs.\\ the top-5 rank-order baseline.",
        "tab:rq5-deltas", colspec="lrrc"))


def t_e2e_ablation() -> str:
    d = csv("ablation_configs.csv")
    rows = [[pretty(r.config, CONFIG_PRETTY), str(int(r.n)), f3(r.cumulative_acc),
             ci(r.acc_ci_lo, r.acc_ci_hi), str(int(r.n_correct))] for r in d.itertuples()]
    return write("tab_e2e_ablation.tex", table(
        rows, ["Configuration", "$n$", "Cumulative acc.", "95\\% CI", "\\#correct"],
        "End-to-end cumulative correctness under oracle ablations "
        "(best-of-breed: Gemini S1 + Qwen S3, $n=140$).",
        "tab:e2e-ablation"))


def t_e2e_deltas() -> str:
    d = csv("ablation_deltas_bootstrap.csv")
    rows = [[esc(r.isolates), f3(r.delta), ci(r.ci_lo, r.ci_hi), esc(r.significant)]
            for r in d.itertuples()]
    return write("tab_e2e_deltas.tex", table(
        rows, ["Oracle stage isolated", "$\\Delta$ vs.\\ full", "95\\% CI", "Sig."],
        "Oracle-ablation deltas vs.\\ the full pipeline (Efron bootstrap, "
        "$N=1000$, seed 42). Largest positive $\\Delta$ = bottleneck.",
        "tab:e2e-deltas", colspec="lrrc"))


# ----------------------------------------------------------- gt / appendix ----
def t_gt_dist_relevance() -> str:
    d = csv("gt_label_distribution_relevance.csv")
    rows = [[esc(r._1), str(int(r.n)), f3(r.share)] for r in d.itertuples()]
    return write("tab_gt_dist_relevance.tex", table(
        rows, ["Relevance class", "$n$", "Share"],
        "Stage-1 ground-truth label distribution ($n=182$).",
        "tab:gt-dist-relevance", colspec="lrr"))


def t_gt_dist_fulfillment() -> str:
    d = csv("gt_label_distribution_fulfillment.csv")
    rows = [[esc(r._1), str(int(r.n)), f3(r.share)] for r in d.itertuples()]
    return write("tab_gt_dist_fulfillment.tex", table(
        rows, ["Fulfillment class", "$n$", "Share"],
        "Stage-3 ground-truth label distribution on the 3-class GT (pre-relabel). "
        "After the binary relabel: fulfilled $122$ / not\\_fulfilled $18$.",
        "tab:gt-dist-fulfillment", colspec="lrr"))


def t_gt_sanity() -> str:
    d = csv("gt_sanity_report.csv")
    rows = [[esc(r.check), esc(r.status), esc(r.detail) if not pd.isna(r.detail) else ""]
            for r in d.itertuples()]
    return write("tab_gt_sanity.tex", table(
        rows, ["Check", "Status", "Detail"],
        "Ground-truth integrity checks.", "tab:gt-sanity", colspec="lll"))


def t_run_manifest() -> str:
    d = csv("run_manifest.csv")
    rows = [[esc(r.section), esc(r.key), esc(r.value)] for r in d.itertuples()]
    return write("tab_run_manifest.tex", table(
        rows, ["Section", "Key", "Value"],
        "Run manifest: configurations, seeds, and provenance.",
        "tab:run-manifest", colspec="lll"))


TABLES = [
    t_retrieval_winner, t_retrieval_topk, t_retrieval_main_effects, t_retrieval_per_req,
    t_relevance_models, t_relevance_h3, t_relevance_per_req,
    t_fulfillment_models_ternary, t_fulfillment_context_h2,
    t_fulfillment_retrieval_conditions, t_gt_span_stats,
    t_binary_vs_ternary, t_binary_vs_ternary_delta, t_f2_pipeline,
    t_rq5_ordering, t_rq5_deltas, t_e2e_ablation, t_e2e_deltas,
    t_gt_dist_relevance, t_gt_dist_fulfillment, t_gt_sanity, t_run_manifest,
]


def main() -> None:
    LATEX.mkdir(parents=True, exist_ok=True)
    written = []
    for fn in TABLES:
        try:
            written.append(fn())
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED {fn.__name__}: {exc}")
    print(f"wrote {len(written)} LaTeX tables to {LATEX}:")
    for n in written:
        print(f"  {n}")


if __name__ == "__main__":
    main()
