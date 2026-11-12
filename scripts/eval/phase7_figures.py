"""Phase 7 — PDF figures from the canonical result CSVs.

Reads ONLY from results/*.csv and writes vector PDFs into results/figures/.
Matplotlib (Agg), no seaborn. Point decimals, English labels. Figures that draw
on the pre-relabel 3-class GT (fulfillment confusion) are titled as such.

Run:  python -m scripts.eval.phase7_figures
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from scripts.eval._common import RESULTS

FIG = RESULTS / "figures"

plt.rcParams.update({
    "figure.dpi": 150, "savefig.bbox": "tight", "font.size": 10,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
    "grid.alpha": 0.3, "grid.linewidth": 0.5,
})

MODEL_PRETTY = {
    "claude_opus_4_8": "Claude\nOpus 4.8", "gemini_3_1_pro": "Gemini\n3.1 Pro",
    "qwen_3_7_max": "Qwen\n3.7 Max", "mimo_v2_5_pro": "MiMo\nv2.5 Pro",
}
ARM_PRETTY = {
    "k5_rank": "top-5\nrank", "k1_rank": "top-1", "k5_doc": "top-5\ndoc",
    "k5_relevancelast": "top-5\nrel-last",
}
CONFIG_PRETTY = {
    "full": "Full", "oracle_rel": "Oracle\nrel.", "oracle_retr": "Oracle\nretr.",
    "oracle_rel_retr": "Oracle\nrel.+retr.", "full_oracle": "Full\noracle",
}
PIPE_PRETTY = {
    "P1_2option_binary": "P1\n2-option", "P2_3option_optimistic": "P2\n3-opt. optim.",
    "P3_3option_fine_review": "P3\nfine/review",
}


def csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RESULTS / name)


def save(fig, name: str) -> str:
    fig.savefig(FIG / name)
    plt.close(fig)
    return name


def _yerr(point, lo, hi):
    point, lo, hi = np.asarray(point), np.asarray(lo), np.asarray(hi)
    return np.vstack([np.clip(point - lo, 0, None), np.clip(hi - point, 0, None)])


# ----------------------------------------------------------------- figures ----
def fig_recall_at_k() -> str:
    d = csv("recall_at_k_curve.csv")
    w = d[(d.embedding == "gemini") & (d.segmentation == "baseSeg") &
          (d.table_rep == "llmdesc") & (d.query_variant == "enriched")].sort_values("k")
    fig, ax = plt.subplots(figsize=(5, 3.4))
    ax.plot(w.k, w.recall_mean, "o-", label="Recall@k")
    ax.plot(w.k, w.hit_mean, "s--", label="Hit@k")
    ax.set_xlabel("k"); ax.set_ylabel("score"); ax.set_xticks(w.k)
    ax.set_ylim(0, 1); ax.legend(frameon=False)
    ax.set_title("Retrieval quality of the winning configuration")
    return save(fig, "fig_recall_at_k.pdf")


def fig_retrieval_per_req() -> str:
    d = csv("retrieval_per_requirement.csv").sort_values("recall_mean")
    fig, ax = plt.subplots(figsize=(5, 4))
    ax.barh(d.obligation, d.recall_mean, color="#4C72B0")
    ax.set_xlabel("Mean Recall@5"); ax.set_xlim(0, 1)
    ax.grid(axis="y", visible=False)
    ax.set_title("Retrieval Recall@5 per obligation")
    return save(fig, "fig_retrieval_per_requirement.pdf")


def fig_relevance_per_req() -> str:
    d = csv("relevance_per_requirement.csv")
    piv = d.pivot(index="obligation_id", columns="model", values="accuracy")
    models = [m for m in MODEL_PRETTY if m in piv.columns]
    piv = piv[models]
    fig, ax = plt.subplots(figsize=(5.5, 5))
    im = ax.imshow(piv.values, cmap="RdYlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(models)),
                  [MODEL_PRETTY[m].replace("\n", " ") for m in models], rotation=30, ha="right")
    ax.set_yticks(range(len(piv.index)), piv.index)
    ax.grid(False)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                    color="black" if 0.25 < v < 0.85 else "white")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="accuracy")
    ax.set_title("Stage-1 relevance accuracy per obligation")
    return save(fig, "fig_relevance_per_requirement.pdf")


def fig_relevance_gt_share() -> str:
    """(a) GT relevance composition per obligation, (b) accuracy against it.

    Panel (b) draws the identity line, which is the accuracy an "always relevant"
    classifier reaches on an obligation whose GT relevant share is x, and the
    pooled OLS fit taken from relevance_gtshare_regression.csv.
    """
    gt = csv("relevance_gt_per_requirement.csv").sort_values(
        "share_relevant", kind="stable")  # stable: ties keep the obligation-id order
    per = csv("relevance_per_requirement.csv").merge(
        gt[["obligation_id", "share_relevant"]], on="obligation_id")
    dist = csv("gt_label_distribution_relevance.csv").set_index("class")["share"]
    fit = csv("relevance_gtshare_regression.csv")
    fit = fit[(fit.model == "POOLED") & (fit.target == "accuracy")].iloc[0]
    overall = float(dist.get("relevant", float("nan")))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    ax = axes[0]
    x = np.arange(len(gt))
    bottom = np.zeros(len(gt))
    for col, lab, colour in [("share_relevant", "relevant", "#3b6ea5"),
                             ("share_not_relevant", "not relevant", "#c0504d"),
                             ("share_unclear", "unclear", "#bfbfbf")]:
        ax.bar(x, gt[col], bottom=bottom, label=lab, color=colour)
        bottom = bottom + gt[col].to_numpy()
    ax.axhline(overall, color="black", lw=1.1, ls=":",
               label=f"overall relevant share ({overall:.3f})")
    ax.set_xticks(x, gt.obligation_id, rotation=90, fontsize=8)
    ax.set_ylabel("share of the 14 entities")
    ax.set_ylim(0, 1.3); ax.set_yticks(np.arange(0, 1.01, 0.2))  # headroom for the legend
    ax.grid(axis="x", visible=False)
    ax.set_title("(a) Ground-truth relevance per obligation", fontsize=10)
    ax.legend(fontsize=7.5, loc="upper center", ncol=2, framealpha=0.9)

    ax = axes[1]
    markers = {"claude_opus_4_8": "o", "gemini_3_1_pro": "s",
               "qwen_3_7_max": "^", "mimo_v2_5_pro": "D"}
    colours = {"claude_opus_4_8": "#3b6ea5", "gemini_3_1_pro": "#c0504d",
               "qwen_3_7_max": "#4f8a4f", "mimo_v2_5_pro": "#8064a2"}
    for m in [m for m in MODEL_PRETTY if m in set(per.model)]:
        s = per[per.model == m]
        # open markers: models agree on most obligations, so points coincide
        ax.scatter(s.share_relevant, s.accuracy, marker=markers[m], s=46,
                   facecolors="none", edgecolors=colours[m], linewidths=1.3,
                   label=MODEL_PRETTY[m].replace("\n", " "))
    xx = np.linspace(0.2, 1.0, 50)
    ax.plot(xx, xx, ls="--", lw=1.1, color="#666666", label="always-relevant baseline")
    ax.plot(xx, fit.intercept + fit.slope * xx, lw=1.6, color="black",
            label=f"OLS fit ($r$ = {fit.pearson_r:.2f}, $R^2$ = {fit.r_squared:.2f})")
    ax.set_xlabel("GT share of entities for which the obligation is relevant")
    ax.set_ylabel("per-obligation accuracy")
    ax.set_xlim(0.15, 1.05); ax.set_ylim(0.2, 1.05)
    ax.set_title("(b) Accuracy against the ground-truth relevant share", fontsize=10)
    ax.legend(fontsize=7.5, loc="lower right", framealpha=0.9)
    fig.tight_layout()
    return save(fig, "fig_relevance_gt_share.pdf")


def _confusion_grid(d: pd.DataFrame, classes: list, short: list, title: str, fname: str) -> str:
    models = [m for m in MODEL_PRETTY if m in d.model.unique()]
    fig, axes = plt.subplots(2, 2, figsize=(7, 6.6))
    for ax, model in zip(axes.ravel(), models):
        md = d[d.model == model]
        mat = np.zeros((len(classes), len(classes)))
        for r in md.itertuples():
            if r.gt in classes and r.pred in classes:
                mat[classes.index(r.gt), classes.index(r.pred)] = r.n
        im = ax.imshow(mat, cmap="Blues", aspect="auto")
        ax.set_xticks(range(len(classes)), short, fontsize=8)
        ax.set_yticks(range(len(classes)), short, fontsize=8)
        ax.set_xlabel("predicted", fontsize=8); ax.set_ylabel("ground truth", fontsize=8)
        ax.set_title(MODEL_PRETTY[model].replace("\n", " "), fontsize=9)
        ax.grid(False)
        thr = mat.max() * 0.6 if mat.max() else 1
        for i in range(len(classes)):
            for j in range(len(classes)):
                ax.text(j, i, int(mat[i, j]), ha="center", va="center", fontsize=8,
                        color="white" if mat[i, j] > thr else "black")
    for ax in axes.ravel()[len(models):]:
        ax.axis("off")
    fig.suptitle(title, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    return save(fig, fname)


def fig_relevance_confusion() -> str:
    d = csv("relevance_confusion.csv")
    return _confusion_grid(d, ["relevant", "not_relevant", "unclear"],
                           ["rel", "not", "unc"],
                           "Stage-1 relevance confusion matrices", "fig_relevance_confusion.pdf")


def fig_fulfillment_confusion() -> str:
    d = csv("fulfillment_confusion.csv")
    d = d[(d.retrieval == "predicted") & (d.context == "statute_only")]
    return _confusion_grid(d, ["fulfilled", "partially", "not_fulfilled"],
                           ["ful", "part", "not"],
                           "Stage-3 fulfillment confusion (3-class GT, pre-relabel)",
                           "fig_fulfillment_confusion.pdf")


def fig_e2e_cumulative() -> str:
    d = csv("ablation_configs.csv")
    labels = [CONFIG_PRETTY.get(c, c) for c in d.config]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = np.arange(len(d))
    ax.bar(x, d.cumulative_acc, yerr=_yerr(d.cumulative_acc, d.acc_ci_lo, d.acc_ci_hi),
           capsize=4, color="#55A868")
    ax.set_xticks(x, labels, fontsize=9)
    ax.set_ylabel("cumulative accuracy"); ax.set_ylim(0, 1.05)
    ax.grid(axis="x", visible=False)
    for xi, v in zip(x, d.cumulative_acc):
        ax.text(xi, v + 0.02, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_title("End-to-end cumulative correctness (best-of-breed, n=140)")
    return save(fig, "fig_e2e_cumulative.pdf")


def fig_e2e_ablation_deltas() -> str:
    d = csv("ablation_deltas_bootstrap.csv")
    fig, ax = plt.subplots(figsize=(5.5, 3))
    y = np.arange(len(d))
    ax.errorbar(d.delta, y, xerr=_yerr(d.delta, d.ci_lo, d.ci_hi), fmt="o",
                color="#C44E52", capsize=4)
    ax.axvline(0, color="grey", lw=0.8, ls="--")
    ax.set_yticks(y, d.isolates); ax.set_xlabel(r"$\Delta$ cumulative acc. vs. full")
    ax.grid(axis="y", visible=False)
    ax.set_title("Oracle-ablation deltas (95% bootstrap CI)")
    return save(fig, "fig_e2e_ablation_deltas.pdf")


def fig_rq5_ordering() -> str:
    d = csv("rq5_passage_ordering.csv")
    order = ["k1_rank", "k5_rank", "k5_doc", "k5_relevancelast"]
    d = d.set_index("arm").loc[[a for a in order if a in d.arm.values]].reset_index()
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    x = np.arange(len(d))
    ax.bar(x, d.accuracy, yerr=_yerr(d.accuracy, d.acc_ci_lo, d.acc_ci_hi),
           capsize=4, color="#4C72B0")
    ax.set_xticks(x, [ARM_PRETTY.get(a, a) for a in d.arm], fontsize=9)
    ax.set_ylabel("accuracy"); ax.set_ylim(0, 1)
    ax.grid(axis="x", visible=False)
    for xi, v in zip(x, d.accuracy):
        ax.text(xi, v + 0.02, f"{v:.3f}", ha="center", fontsize=8)
    ax.set_title("RQ5: evidence count and position (binary GT)")
    return save(fig, "fig_rq5_ordering.pdf")


def fig_f2_pipeline() -> str:
    d = csv("fulfillment_f2_comparison_md.csv")
    order = ["P1_2option_binary", "P2_3option_optimistic", "P3_3option_fine_review"]
    d = d.set_index("pipeline").loc[[p for p in order if p in d.pipeline.values]].reset_index()
    metrics = [("recall_needs_review", "Recall"), ("f1_needs_review", "F1"),
               ("f2_needs_review", "F2")]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = np.arange(len(d)); width = 0.25
    colors = ["#8172B3", "#4C72B0", "#C44E52"]
    for i, (col, lab) in enumerate(metrics):
        ax.bar(x + (i - 1) * width, d[col], width, label=lab, color=colors[i])
    ax.set_xticks(x, [PIPE_PRETTY.get(p, p) for p in d.pipeline], fontsize=9)
    ax.set_ylabel("score (needs-review class)"); ax.set_ylim(0, 1)
    ax.legend(frameon=False, ncol=3); ax.grid(axis="x", visible=False)
    ax.set_title("Output-scheme comparison on the needs-review class")
    return save(fig, "fig_f2_pipeline.pdf")


FIGURES = [
    fig_recall_at_k, fig_retrieval_per_req, fig_relevance_per_req,
    fig_relevance_gt_share, fig_relevance_confusion, fig_fulfillment_confusion,
    fig_e2e_cumulative, fig_e2e_ablation_deltas, fig_rq5_ordering, fig_f2_pipeline,
]


def main() -> None:
    FIG.mkdir(parents=True, exist_ok=True)
    written = []
    for fn in FIGURES:
        try:
            written.append(fn())
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED {fn.__name__}: {exc}")
    print(f"wrote {len(written)} figures to {FIG}:")
    for n in written:
        print(f"  {n}")


if __name__ == "__main__":
    main()
