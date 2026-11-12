"""Phase 1a — Classification GT sanity check.

Validates the canonical classification GT (DB export): the 13x14 grid, label
vocabularies, relevance<->fulfillment consistency, and per-axis counts.

Output: results/gt_sanity_report.csv  + console PASS/FAIL summary.
Run: python -m scripts.eval.phase1a_gt_sanity
"""
from __future__ import annotations

from scripts.eval._common import (
    N_COMPANIES, N_ITEMS, N_OBLIGATIONS, RESULTS, write_csv,
)
from scripts.eval._load_gt import gt_master, load_companies, load_obligations

REL_VOCAB = {"yes", "no", "unsure"}            # is_applicable
FUL_VOCAB = {"yes", "partially", "no", ""}     # is_fulfilled (empty allowed)


def main() -> None:
    m = gt_master()
    obls = sorted(load_obligations()["id"])
    comps = sorted(load_companies()["id"])
    checks: list[dict] = []

    def chk(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # --- total ---
    total_ok = len(m) == N_ITEMS
    chk("total_items_eq_182", total_ok, f"found {len(m)} (expected {N_ITEMS})")

    # --- grid completeness / duplicates ---
    pairs = m.groupby(["obligation_id", "company_id"]).size()
    dupes = pairs[pairs > 1]
    present = set(zip(m["obligation_id"], m["company_id"]))
    expected = {(o, c) for o in obls for c in comps}
    missing = sorted(expected - present)
    chk("grid_no_duplicates", dupes.empty, "" if dupes.empty else f"{len(dupes)} dup pairs")
    chk("grid_no_missing_pairs", not missing, "" if not missing else f"{len(missing)} missing: {missing[:10]}")
    chk("obligation_count_eq_13", len(set(m["obligation_id"])) == N_OBLIGATIONS,
        f"{len(set(m['obligation_id']))} distinct obligations")
    chk("company_count_eq_14", len(set(m["company_id"])) == N_COMPANIES,
        f"{len(set(m['company_id']))} distinct companies")

    # --- vocab ---
    rel_oov = sorted(set(m["is_applicable"]) - REL_VOCAB)
    ful_oov = sorted(set(m["is_fulfilled"]) - FUL_VOCAB)
    chk("relevance_vocab_ok", not rel_oov, "" if not rel_oov else f"OOV: {rel_oov}")
    chk("fulfillment_vocab_ok", not ful_oov, "" if not ful_oov else f"OOV: {ful_oov}")

    # --- consistency: applicable=yes <=> has fulfillment ---
    applicable = m["is_applicable"] == "yes"
    has_ful = m["is_fulfilled"] != ""
    rel_no_ful = m[applicable & ~has_ful]
    notrel_ful = m[~applicable & has_ful]
    chk("applicable_yes_has_fulfillment", len(rel_no_ful) == 0,
        f"{len(rel_no_ful)} applicable-yes rows without fulfillment")
    chk("not_applicable_no_fulfillment", len(notrel_ful) == 0,
        f"{len(notrel_ful)} non-applicable rows with fulfillment")

    # --- per-axis counts (each obligation should appear for 14 companies; each company 13) ---
    per_obl = m.groupby("obligation_id").size()
    per_comp = m.groupby("company_id").size()
    chk("per_obligation_eq_14", (per_obl == N_COMPANIES).all(),
        "" if (per_obl == N_COMPANIES).all() else per_obl[per_obl != N_COMPANIES].to_dict().__str__())
    chk("per_company_eq_13", (per_comp == N_OBLIGATIONS).all(),
        "" if (per_comp == N_OBLIGATIONS).all() else per_comp[per_comp != N_OBLIGATIONS].to_dict().__str__())

    write_csv(RESULTS / "gt_sanity_report.csv", checks, ["check", "status", "detail"])

    # --- console summary ---
    n_fail = sum(c["status"] == "FAIL" for c in checks)
    print("=" * 70)
    print("Phase 1a — Classification GT sanity")
    print("=" * 70)
    for c in checks:
        flag = "OK " if c["status"] == "PASS" else "XX "
        print(f"  [{flag}] {c['check']:34} {c['detail']}")
    print("-" * 70)
    print(f"  relevance dist  : {m['relevance'].value_counts().to_dict()}")
    print(f"  fulfillment dist: {m[m['fulfillment']!=''] ['fulfillment'].value_counts().to_dict()}")
    print("-" * 70)
    print(f"  {'ALL CHECKS PASSED' if n_fail == 0 else f'{n_fail} CHECK(S) FAILED'}")
    print(f"  report -> {(RESULTS / 'gt_sanity_report.csv')}")
    if n_fail:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
