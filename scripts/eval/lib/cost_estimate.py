"""Estimate prompt-token volume and cost for a generation grid — NO API calls.

Generic over the phase: pass a build_prompt(company, obl, cond, variant, k) ->
(system, user, n_passages) callable and the constant system string. Prices map
model_key -> ($/MTok in, $/MTok out); models without a pinned price report raw
token counts only.
"""
from __future__ import annotations


def estimate(build_prompt, system, pairs, conds, variants, k, models, prices,
             out_tok_per_answer: int = 120) -> None:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    sys_tok = len(enc.encode(system))
    n_calls = len(pairs) * len(conds) * len(variants)
    print(f"DRY RUN -- {len(pairs)} pairs x {len(conds)} cond x {len(variants)} ctx "
          f"= {n_calls} calls/model\n")
    grid_in = 0
    for cond in conds:
        for variant in variants:
            tin = nempty = 0
            for (c, o) in pairs:
                _, user, npas = build_prompt(c, o, cond, variant, k)
                tin += sys_tok + len(enc.encode(user))
                nempty += int(npas == 0)
            grid_in += tin
            print(f"  {cond:9} | {variant:12}  in~{tin:>8} tok  empty-evidence pairs: {nempty}")
    est_out = n_calls * out_tok_per_answer
    print(f"\n  per-model input ~ {grid_in} tok   est. output ~ {est_out} tok")
    for mk in models:
        price = prices.get(mk)
        if price:
            cost = grid_in / 1e6 * price[0] + est_out / 1e6 * price[1]
            print(f"  {mk:16} est. cost ~ ${cost:.2f}  (in ${price[0]}/out ${price[1]} per MTok)")
        else:
            print(f"  {mk:16} price not pinned -- in {grid_in} / out {est_out} tok")
