"""Phase 4b-2 — BINARY fulfillment verification (winning config) + RQ5 ordering.

After the 2026-06-30 GT relabeling, fulfillment is 2-class (fulfilled / not_fulfilled;
the 27 former 'partially' were re-decided). This script re-generates predictions for
the *winning* fulfillment configuration only — qwen_3_7_max / statute_only — under a
strict 2-option prompt, and serves two studies at once:

  * Binary vs ternary: the predicted/k5/rank arm is the like-for-like binary
    counterpart of the on-disk 3-class run (compared in phase5_fulfillment_binary).
  * RQ5 passage position: predicted/k5 in three orderings (rank / doc / relevance_last)
    plus single-passage top-1 (k=1). Isolates ranked-list-vs-single and U-shape effects.

The oracle arm feeds the Phase-6 ablation (qwen on GT evidence, binary).

Scored against gt_master(binary=True) → 140 pairs (122 fulfilled / 18 not_fulfilled;
majority baseline 0.871). One LLM call per (arm × pair); cache is prompt-hashed so
re-scoring is free and distinct orderings get distinct keys.

Run:
    python -m scripts.eval.phase4b2_fulfillment_binary --dry-run
    python -m scripts.eval.phase4b2_fulfillment_binary --arms all
"""
from __future__ import annotations

import argparse
import threading
from concurrent.futures import ThreadPoolExecutor

from scripts.eval._common import GEN_MODELS, RESULTS
from scripts.eval._load_gt import gt_master
from scripts.eval.lib.answer_parse import parse_label
from scripts.eval.lib.evidence import evidence
from scripts.eval.lib.llm import ChatClient
from scripts.eval.lib.pred_output import write_predictions
from scripts.eval.lib.verif_context import context

MODEL = "qwen_3_7_max"
VARIANT = "statute_only"
LABELS = {"fulfilled", "not_fulfilled"}

# arm name -> (retrieval condition, k, passage order)
ARMS = {
    "predicted_k5_rank":          ("predicted", 5, "rank"),
    "predicted_k1_rank":          ("predicted", 1, "rank"),
    "predicted_k5_doc":           ("predicted", 5, "doc"),
    "predicted_k5_relevancelast": ("predicted", 5, "relevance_last"),
    "oracle":                     ("oracle",    5, "rank"),
}

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
- "fulfilled": die geforderte Angabe ist vorhanden.
- "not_fulfilled": die geforderte Angabe fehlt.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt:
{{"label": "fulfilled|not_fulfilled", "reason": "<kurze Begründung>"}}
"""


def scored_pairs() -> tuple[list[tuple[str, str]], dict]:
    m = gt_master(binary=True)
    s = m[m["fulfillment"] != ""]
    gt = {(r.company_id, r.obligation_id): r.fulfillment for r in s.itertuples(index=False)}
    return sorted(gt), gt


def _format_passages(passages) -> str:
    if not passages:
        return "(keine Textstellen gefunden)"
    return "\n\n".join(f"[{i}] {t.strip()}" for i, (_, _, t) in enumerate(passages, 1))


def build_prompt(company: str, obl: str, arm: str) -> tuple[str, str]:
    cond, k, order = ARMS[arm]
    title, ctx = context(obl, VARIANT)
    passages = evidence(company, obl, cond, k, order)
    user = USER_TMPL.format(oid=obl, title=title, ctx=ctx, passages=_format_passages(passages))
    return SYSTEM, user


def run(arms: list[str], limit: int, workers: int, model: str = MODEL) -> None:
    pairs, gt = scored_pairs()
    if limit:
        pairs = pairs[:limit]
    print(f"binary fulfillment: {len(pairs)} pairs  model={model}  arms={arms}")

    # Reasoning models spend hidden tokens against max_tokens -> larger budget.
    mt = 1500 if model == MODEL else 12000
    client = ChatClient(GEN_MODELS[model], RESULTS / "_qcache" / f"fulfillment_{model}.jsonl",
                        temperature=0.0, max_tokens=mt)
    # Build every prompt up front in the main thread: ChromaDB's PersistentClient is
    # not safe to initialise concurrently, so all retrieval happens single-threaded here.
    print("building prompts (retrieval, single-threaded)…")
    tasks = [(arm, c, o, *build_prompt(c, o, arm)) for arm in arms for (c, o) in pairs]
    texts: dict = {}
    cnt, lock = {"n": 0}, threading.Lock()
    abort = threading.Event()

    def work(t):
        if abort.is_set():
            return
        arm, c, o, sysm, user = t
        try:
            texts[(arm, c, o)] = client.complete(sysm, user)
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {arm} {c} {o}: {type(exc).__name__}: {str(exc)[:160]}")
            if getattr(exc, "status_code", None) in (401, 403) or "Key limit" in str(exc):
                abort.set()
            return
        with lock:
            cnt["n"] += 1
            if cnt["n"] % 50 == 0 or cnt["n"] == len(tasks):
                print(f"  [{cnt['n']}/{len(tasks)}] done")

    print(f"running {len(tasks)} calls, {workers} workers")
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(work, tasks))
    if abort.is_set():
        raise SystemExit("ABORTED on 401/403 (expired key or key limit) — fix the key and re-run (cache resumes free).")

    for arm in arms:
        rows = []
        for (c, o) in pairs:
            text = texts.get((arm, c, o), "")
            lab, reason = parse_label(text, LABELS)
            rows.append({"company_id": c, "obligation_id": o, "pred_label": lab,
                         "gt_label": gt[(c, o)], "correct": int(bool(lab) and lab == gt[(c, o)]),
                         "reason": reason, "raw": text})
        write_predictions(f"fulfillmentbin_{model}_{arm}", GEN_MODELS[model], rows)
        acc = sum(r["correct"] for r in rows) / len(rows)
        nfail = sum(1 for r in rows if not r["pred_label"])
        print(f"  {arm}: acc={acc:.4f}  parse_fail={nfail}")


def dry_run(arms: list[str]) -> None:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    pairs, _ = scored_pairs()
    total = 0
    for arm in arms:
        toks = sum(len(enc.encode(build_prompt(c, o, arm)[1])) for (c, o) in pairs)
        total += toks
        print(f"  {arm}: {len(pairs)} calls, ~{toks:,} input tokens")
    print(f"TOTAL: {len(arms) * len(pairs)} calls, ~{total:,} input tokens (output small, temp=0)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default="all", help="comma list of arm names, or 'all'")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-workers", type=int, default=16)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--model", default=MODEL, help=f"GEN_MODELS key (default {MODEL})")
    args = ap.parse_args()
    arms = list(ARMS) if args.arms == "all" else [a.strip() for a in args.arms.split(",")]
    for a in arms:
        if a not in ARMS:
            raise SystemExit(f"unknown arm {a!r}; valid: {list(ARMS)}")
    if args.dry_run:
        dry_run(arms)
    else:
        if args.model not in GEN_MODELS:
            raise SystemExit(f"unknown model {args.model!r}; valid: {list(GEN_MODELS)}")
        run(arms, args.limit, args.max_workers, args.model)


if __name__ == "__main__":
    main()
