# How to re-run the experiments (after the GT changes)

When new annotators finish and the **consensus GT** changes, re-running the LLM
experiments is **free and fast** — the model predictions are cached and do *not*
depend on the GT, so only the `correct` column + metrics are recomputed. You only
pay the API again if you change models, prompts, evidence (k / retrieval winner),
or the obligation/report text.

## 0. Environment (every command)

```bash
# from repo root: C:\Users\Sellit\Documents\Masterarbeit\source_code
export PYTHONPATH="$PWD"
PY="C:/Users/Sellit/anaconda3/envs/thesis2/python.exe"
# All runs: pipe through this to mute gRPC noise
#   ... 2>&1 | grep -v -E "absl::InitializeLog|instrument.cc|grpc.resource_quota"
```

## 1. Refresh the frozen DB export  (only if annotations changed)

The experiments read the frozen CSVs in `results/_db_export/` (host psycopg2
segfaults under this Anaconda build, so the GT is exported from the container).
Re-export `annotations.csv`, `annotation_items.csv`, `passage_sentences.csv`,
`irrelevant_elements.csv`, `suggested_passages.csv`, `obligations.csv`,
`companies.csv` via `docker exec <pg> psql \copy ...` (same way the current export
was produced). Schema/columns: `annotation_app/app/export.py`.

## 2. Switch the GT source to consensus  (one-time integration)

The consensus (majority-vote) GT is `scripts/eval/_consensus_gt.consensus_gt()`. It
is **parity-proven** against `gt_master()` on single-annotator data. With multiple
annotators, `gt_master()`'s one-to-one merge breaks, so point the loaders at the
consensus GT:

- Quickest: make `_load_gt.gt_master()` delegate to `_consensus_gt.consensus_gt()`
  (same output columns: company_id, obligation_id, is_applicable, is_fulfilled,
  relevance, fulfillment) — then every phase below works unchanged.

Sanity-check first: `$PY -m scripts.eval._consensus_gt` prints the parity check,
how many items still need votes, and how many have unresolved questions. Do not
finalize the GT while `needs_more`/`unresolved` items remain.

## 3. Re-score the predictions  (FREE — reads model caches)

```bash
$PY -m scripts.eval.phase4a_relevance        # Stage-1, re-scores from results/_qcache/relevance_*
$PY -m scripts.eval.phase4b_fulfillment      # Stage-3, re-scores from results/_qcache/fulfillment_*
```
Both reuse cached model outputs; with an unchanged model set they make **0 API
calls**. (Confirm with `--dry-run` on phase4b, or watch that `_qcache/*` line counts
don't grow.)

## 4. Recompute the metric CSVs  (FREE — pure analysis)

```bash
$PY -m scripts.eval.phase5_relevance_metrics    # Stage-1: per-model, per-obligation,
                                                # clusters, GT-share regression,
                                                # excl-unclear, reference baselines
$PY -m scripts.eval.phase5_fulfillment_metrics
$PY -m scripts.eval.phase5_error_cases          # error_cases + error_taxonomy_seed
```
`phase5_relevance_metrics` aborts if the frozen `gt_label` column in
`results/preds/relevance_*.csv` disagrees with the GT loader — run step 3 first.

Then rebuild the derived artefacts:
```bash
$PY -m scripts.eval.phase7_tables
$PY -m scripts.eval.phase7_figures
```

All bootstrap intervals come from `scripts/eval/lib/bootstrap.py`
(`numpy.random.default_rng(42)`, 1000 replicates, 2.5/97.5 percentiles). Do not
re-seed locally in a phase — call the helper, otherwise the same quantity gets
different bounds in different tables.

## 5. Retrieval (Phase 3) — only if evidence spans changed

Retrieval GT depends on the curated spans. If `passage_sentences` / `is_relevant`
changed, rebuild the snapshot then re-run retrieval (this DOES use embeddings, but
they're cached per query):
```bash
$PY -m scripts.eval.phase1b_retrieval_gt
$PY -m scripts.eval.phase3_retrieval
```
Note the open question: the Stage-2 retrieval population currently uses
`is_relevant=t` (170 pairs); revisit vs the applicable population (141) when the GT
is final (see `results/stage_population.md`).

## When you DO pay API again
- New/changed model → delete/ignore that model's `results/_qcache/fulfillment_<model>.jsonl`
  and re-run (use `phase4b_fulfillment --dry-run` first for the cost estimate).
- Changed prompt, context variant text, or retrieval k/winner → cache keys change,
  so those calls re-run. Everything else stays cached.
