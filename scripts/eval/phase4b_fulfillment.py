"""Phase 4b — Stage-3 fulfillment verification (RQ3 / H2).

For each fulfillment-scored pair (is_fulfilled set → 141 pairs) a verifier judges
whether the obligation is fulfilled given evidence passages:
    fulfilled / partially / not_fulfilled.

Factorial per model:  retrieval condition {predicted@k, oracle} × verification
context {statute_only, web_enriched}.  One LLM call per pair.

Outputs per (model, condition, variant) in results/preds/:
    fulfillment_<model>_<cond>_<variant>.csv   (company_id, obligation_id, pred_label,
                                                 gt_label, correct, reason)
    fulfillment_<model>_<cond>_<variant>.md    (run log: n, parse fails, accuracy)
    fulfillment_<model>_<cond>_<variant>_raw.jsonl
Cache: results/_qcache/fulfillment_<model>.jsonl (hash-separated across combos).

Run (build/estimate only, NO paid calls):
    python -m scripts.eval.phase4b_fulfillment --dry-run
Run for real (one or more models):
    python -m scripts.eval.phase4b_fulfillment --models claude_opus_4_8
"""
from __future__ import annotations

import argparse
import threading
from concurrent.futures import ThreadPoolExecutor

from scripts.eval._common import GEN_MODELS, RESULTS
from scripts.eval._load_gt import gt_master
from scripts.eval.lib.answer_parse import parse_label
from scripts.eval.lib.cost_estimate import estimate
from scripts.eval.lib.evidence import DEFAULT_K, evidence
from scripts.eval.lib.llm import ChatClient
from scripts.eval.lib.pred_output import write_predictions
from scripts.eval.lib.verif_context import CONTEXT_VARIANTS, context

LABELS = {"fulfilled", "partially", "not_fulfilled"}
RETRIEVAL_CONDS = ["predicted", "oracle"]
MAX_TOKENS = {"gemini_3_1_pro": 8000, "mimo_v2_5_pro": 8000}
DEFAULT_MAX_TOKENS = 1500
JSON_MODE = {"mimo_v2_5_pro": {"type": "json_object"}}
# OpenRouter prices ($/MTok in, out); None = not pinned (token counts still reported).
PRICES = {"claude_opus_4_8": (5.0, 25.0)}

SYSTEM = (
    "Du bist ein erfahrener Wirtschaftsprüfer. Beurteile ausschließlich anhand der "
    "bereitgestellten Textstellen aus einem HGB-Jahresabschluss/Lagebericht, ob eine "
    "gesetzliche Offenlegungspflicht erfüllt ist."
)
USER_TMPL = """Offenlegungspflicht: [{oid}] {title}
{ctx}

Nachfolgend Textstellen aus dem Abschluss dieses Unternehmens, die für die Pflicht relevant sein könnten:
{passages}

Beurteile, ob die Pflichtangabe durch diese Textstellen erfüllt ist:
- "fulfilled": vollständig vorhanden.
- "partially": nur teilweise / unvollständig vorhanden.
- "not_fulfilled": fehlt.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{"label": "fulfilled|partially|not_fulfilled", "reason": "<kurze Begründung>"}}
"""


def scored_pairs() -> tuple[list[tuple[str, str]], dict]:
    m = gt_master()
    s = m[m["fulfillment"] != ""]
    gt = {(r.company_id, r.obligation_id): r.fulfillment for r in s.itertuples(index=False)}
    return sorted(gt), gt


def _format_passages(passages: list[tuple[int, int, str]]) -> str:
    if not passages:
        return "(keine Textstellen gefunden)"
    return "\n\n".join(f"[{i}] {t.strip()}" for i, (_, _, t) in enumerate(passages, 1))


def build_prompt(company: str, obl: str, cond: str, variant: str, k: int) -> tuple[str, str, int]:
    title, ctx = context(obl, variant)
    passages = evidence(company, obl, cond, k)
    user = USER_TMPL.format(oid=obl, title=title, ctx=ctx, passages=_format_passages(passages))
    return SYSTEM, user, len(passages)


def _build_tasks(models, conds, variants, pairs, k):
    """Flatten the model × cond × variant × pair grid into independent call tasks."""
    tasks = []
    for mk in models:
        for cond in conds:
            for variant in variants:
                for (c, o) in pairs:
                    sysm, user, _ = build_prompt(c, o, cond, variant, k)
                    tasks.append((mk, cond, variant, c, o, sysm, user))
    return tasks


def run_all(clients, models, conds, variants, pairs, gt, k, workers):
    """Run the whole grid in ONE global thread pool (parallel across models+combos).

    Resilient to a mid-run API failure (e.g. the OpenRouter 403 weekly key limit):
    on 403 it sets an abort flag so queued tasks short-circuit instead of retry-
    storming. Each COMBO's outputs are written to disk the moment its last pair
    completes, so partial progress survives even a hard kill."""
    tasks = _build_tasks(models, conds, variants, pairs, k)
    texts, total = {}, len(tasks)
    cnt, combo_n, lock = {"n": 0}, {}, threading.Lock()
    abort = threading.Event()
    npairs = len(pairs)

    def work(t):
        if abort.is_set():
            return
        mk, cond, variant, c, o, sysm, user = t
        try:
            out = clients[mk].complete(sysm, user)
        except Exception as exc:  # noqa: BLE001 — keep the pool alive; record + maybe abort
            if getattr(exc, "status_code", None) == 403 or "Key limit" in str(exc):
                abort.set()
            return
        texts[(mk, cond, variant, c, o)] = out
        with lock:
            cnt["n"] += 1
            combo_n[(mk, cond, variant)] = combo_n.get((mk, cond, variant), 0) + 1
            combo_done = combo_n[(mk, cond, variant)] == npairs
            if cnt["n"] % 50 == 0 or cnt["n"] == total:
                print(f"  [{cnt['n']}/{total}] done")
        if combo_done:                     # incremental save: this combo is complete
            _write_combo(clients[mk].model_id, mk, cond, variant, pairs, gt, texts)

    print(f"\nrunning {total} calls across {len(models)} model(s), {workers} workers")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, tasks))

    blocked = [f"{mk}/{cond}/{variant}" for mk in models for cond in conds for variant in variants
               if combo_n.get((mk, cond, variant), 0) != npairs]
    print(f"\ncombos written: {len(models)*len(conds)*len(variants) - len(blocked)}  "
          f"blocked (incomplete): {len(blocked)}")
    if blocked:
        print("  blocked:", ", ".join(blocked))
    if abort.is_set():
        print("ABORTED on 403 weekly key limit — raise the limit, then re-run; cache resumes free.")


def _write_combo(model_id, model_key, cond, variant, pairs, gt, texts):
    rows = []
    for (c, o) in pairs:
        text = texts[(model_key, cond, variant, c, o)]
        lab, reason = parse_label(text, LABELS)
        rows.append({"company_id": c, "obligation_id": o, "pred_label": lab,
                     "gt_label": gt[(c, o)], "correct": int(bool(lab) and lab == gt[(c, o)]),
                     "reason": reason, "raw": text})
    write_predictions(f"fulfillment_{model_key}_{cond}_{variant}", model_id, rows)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(GEN_MODELS))
    ap.add_argument("--conditions", default=",".join(RETRIEVAL_CONDS))
    ap.add_argument("--variants", default=",".join(CONTEXT_VARIANTS))
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    ap.add_argument("--max-workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=0, help="cap to first N pairs (smoke test); 0 = all")
    ap.add_argument("--dry-run", action="store_true", help="build prompts + estimate cost, no API calls")
    args = ap.parse_args()

    models = [x.strip() for x in args.models.split(",") if x.strip()]
    conds = [x.strip() for x in args.conditions.split(",") if x.strip()]
    variants = [x.strip() for x in args.variants.split(",") if x.strip()]
    for mk in models:
        if mk not in GEN_MODELS:
            raise SystemExit(f"unknown model key {mk!r}; valid: {list(GEN_MODELS)}")
    pairs, gt = scored_pairs()
    if args.limit:
        pairs = pairs[: args.limit]
    print(f"fulfillment-scored pairs: {len(pairs)}  models={models}  conds={conds}  variants={variants}")

    if args.dry_run:
        estimate(build_prompt, SYSTEM, pairs, conds, variants, args.k, models, PRICES)
        return

    clients = {
        mk: ChatClient(GEN_MODELS[mk], RESULTS / "_qcache" / f"fulfillment_{mk}.jsonl",
                       temperature=0.0, max_tokens=MAX_TOKENS.get(mk, DEFAULT_MAX_TOKENS),
                       response_format=JSON_MODE.get(mk))
        for mk in models
    }
    run_all(clients, models, conds, variants, pairs, gt, args.k, args.max_workers)


if __name__ == "__main__":
    main()
