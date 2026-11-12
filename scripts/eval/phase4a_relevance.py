"""Phase 4a — Stage-1 relevance classification (RQ1).

Each of the 4 generative LLMs decides, for every (company x obligation) pair,
whether the disclosure obligation is RELEVANT (applicable / triggered) for that
company's annual financial statement. This mirrors the human `is_applicable`
label (yes->relevant, no->not_relevant, unsure->unclear) — it is about
APPLICABILITY, not whether the disclosure is actually present.

Design (stage-isolated): one call per company. The model receives the FULL
company report (md) plus all 13 obligation descriptions and classifies each in a
single JSON object (the reports fit comfortably — max ~140k chars ~= 40k tokens).
No retrieval is involved at stage 1.

Per model outputs (results/preds/):
  relevance_<model>_raw.jsonl  : one row per company (prompt-free: model, raw text, parsed)
  relevance_<model>.csv        : company_id, obligation_id, pred_label, gt_label, correct, reason
  relevance_<model>.md         : run log (n, parse failures, accuracy, confusion)
Cache: results/_qcache/relevance_<model>.jsonl (via ChatClient request hash).

Run: python -m scripts.eval.phase4a_relevance [--models qwen_3_7_max,claude_opus_4_8 ...]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter

from scripts.eval._common import ENRICHED_JSON, GEN_MODELS, PREDS, RESULTS, ROOT
from scripts.eval._load_gt import gt_master
from scripts.eval.lib.llm import ChatClient

MD_DIR = ROOT / "Output" / "md_files"
LABELS = {"relevant", "not_relevant", "unclear"}
# Reasoning models (gemini-3.1-pro-preview, mimo-v2.5-pro) spend a large, variable
# share of max_tokens on hidden reasoning; too small a budget truncates the JSON
# answer mid-object (finish_reason='length'). Give them ample headroom.
MAX_TOKENS = {"gemini_3_1_pro": 8000, "mimo_v2_5_pro": 8000,
              "claude_sonnet_5_5": 16000, "gemini_4_argon": 16000, "kimi_k3": 16000}
DEFAULT_MAX_TOKENS = 4000
# mimo-v2.5-pro is a heavy reasoning model that otherwise emits non-deterministic /
# truncated JSON; response_format=json_object forces a complete, parseable object.
JSON_MODE = {"mimo_v2_5_pro": {"type": "json_object"}}

SYSTEM = (
    "Du bist ein erfahrener Wirtschaftsprüfer. Deine Aufgabe ist zu beurteilen, welche "
    "gesetzlichen Pflichtangaben (HGB/DRS/IFRS) für einen konkreten Jahresabschluss "
    "RELEVANT, also einschlägig bzw. anwendbar, sind. Es geht um die ANWENDBARKEIT der "
    "Pflicht für dieses Unternehmen, NICHT darum, ob die Angabe tatsächlich gemacht wurde."
)

USER_TMPL = """Nachfolgend der vollständige Jahresabschluss/Lagebericht eines Unternehmens, danach eine \
Liste von {n} Offenlegungspflichten.

Beurteile für JEDE Pflicht, ob sie für diesen Abschluss relevant (anwendbar) ist:
- "relevant": Die Pflichtangabe ist für dieses Unternehmen einschlägig/anwendbar.
- "not_relevant": Die Pflichtangabe ist für dieses Unternehmen nicht einschlägig.
- "unclear": Die Anwendbarkeit lässt sich nicht eindeutig bestimmen.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt, das für jede Pflicht-ID einen Eintrag enthält:
{{"R02": {{"label": "relevant|not_relevant|unclear", "reason": "<kurze Begründung>"}}, ...}}

=== JAHRESABSCHLUSS ===
{report}

=== OFFENLEGUNGSPFLICHTEN ===
{obligations}
"""


def obligation_block() -> tuple[str, list[str]]:
    obls = json.loads(ENRICHED_JSON.read_text(encoding="utf-8"))["requirements"]
    lines = []
    for o in obls:
        app = o.get("applicability", {}) or {}
        app_s = f"{app.get('type', '')} ({app.get('trigger', '')})".strip()
        lines.append(
            f"[{o['id']}] {o.get('title_de', '')}\n"
            f"  Rechtsgrundlage: {o.get('legal_basis', '')}\n"
            f"  Anwendbarkeit: {app_s}\n"
            f"  Prüfkriterium: {o.get('verification_criterion', '')}"
        )
    return "\n\n".join(lines), [o["id"] for o in obls]


def _salvage_entry(s: str, oid: str) -> tuple[str, str]:
    """Recover one obligation's label/reason from possibly-truncated JSON text.

    Reasoning models occasionally truncate the answer mid-object so the whole
    blob won't json.loads. Each entry is flat ({"label":..,"reason":..}), so we
    grab the per-id label (and optional reason) directly; entries that were never
    emitted stay empty.
    """
    pat = re.compile(
        r'"' + re.escape(oid) + r'"\s*:\s*\{[^{}]*?'
        r'"label"\s*:\s*"(relevant|not_relevant|unclear)"'
        r'(?:[^{}]*?"reason"\s*:\s*"((?:[^"\\]|\\.)*)")?',
        re.DOTALL | re.IGNORECASE)
    m = pat.search(s)
    if not m:
        return "", ""
    lab = m.group(1).strip().lower()
    reason = (m.group(2) or "").strip()
    return (lab if lab in LABELS else ""), reason


def parse_labels(text: str, obl_ids: list[str]) -> dict[str, dict]:
    """Extract the JSON object and normalise to {id: {label, reason}}; '' label if missing.

    First tries a strict full-object parse; for any id still missing (e.g. the
    object was truncated mid-way), falls back to per-entry regex salvage.
    """
    s = text.strip()
    if "```" in s:
        s = re.sub(r"```(?:json)?", "", s).strip()
    m = re.search(r"\{.*\}", s, re.DOTALL)
    raw = {}
    if m:
        try:
            raw = json.loads(m.group(0))
        except json.JSONDecodeError:
            raw = {}
    out = {}
    for oid in obl_ids:
        entry = raw.get(oid) if isinstance(raw, dict) else None
        if isinstance(entry, dict):
            lab = str(entry.get("label", "")).strip().lower()
            reason = str(entry.get("reason", "")).strip()
        elif isinstance(entry, str):
            lab, reason = entry.strip().lower(), ""
        else:
            lab, reason = "", ""
        lab = lab if lab in LABELS else ""
        if not lab:                       # salvage from raw text (truncated JSON)
            lab, reason = _salvage_entry(s, oid)
        out[oid] = {"label": lab, "reason": reason}
    return out


def run_model(model_key: str, companies: list[str], gt: dict, obl_text: str,
              obl_ids: list[str]) -> None:
    model_id = GEN_MODELS[model_key]
    cache = RESULTS / "_qcache" / f"relevance_{model_key}.jsonl"
    mt = MAX_TOKENS.get(model_key, DEFAULT_MAX_TOKENS)
    rf = JSON_MODE.get(model_key)
    client = ChatClient(model_id, cache, temperature=0.0, max_tokens=mt, response_format=rf)
    print(f"\n=== {model_key} ({model_id})  max_tokens={mt}"
          + (f"  json_mode" if rf else "") + " ===")

    raw_path = PREDS / f"relevance_{model_key}_raw.jsonl"
    rows, raw_lines = [], []
    n_parse_fail = 0
    for ci, company in enumerate(companies, 1):
        report = (MD_DIR / f"{company}.md").read_text(encoding="utf-8")
        user = USER_TMPL.format(n=len(obl_ids), report=report, obligations=obl_text)
        text = client.complete(SYSTEM, user)
        parsed = parse_labels(text, obl_ids)
        missing = [o for o in obl_ids if not parsed[o]["label"]]
        n_parse_fail += len(missing)
        print(f"  [{ci}/{len(companies)}] {company:16} parsed {len(obl_ids)-len(missing)}/{len(obl_ids)}"
              + (f"  MISSING {missing}" if missing else ""))
        raw_lines.append(json.dumps(
            {"company_id": company, "model": model_id, "raw": text, "parsed": parsed},
            ensure_ascii=False))
        for oid in obl_ids:
            gl = gt.get((company, oid), "")
            pl = parsed[oid]["label"]
            rows.append({"company_id": company, "obligation_id": oid, "pred_label": pl,
                         "gt_label": gl, "correct": int(bool(pl) and pl == gl),
                         "reason": parsed[oid]["reason"]})
    raw_path.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    _write_csv(PREDS / f"relevance_{model_key}.csv", rows)
    _write_md(PREDS / f"relevance_{model_key}.md", model_key, model_id, rows, n_parse_fail)


def _write_csv(path, rows):
    import csv
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["company_id", "obligation_id", "pred_label",
                                           "gt_label", "correct", "reason"])
        w.writeheader()
        w.writerows(rows)


def _write_md(path, model_key, model_id, rows, n_parse_fail):
    scored = [r for r in rows if r["gt_label"] and r["pred_label"]]
    acc = sum(r["correct"] for r in scored) / len(scored) if scored else float("nan")
    conf = Counter((r["gt_label"], r["pred_label"]) for r in scored)
    lines = [f"# Phase 4a relevance — {model_key}", "",
             f"- model: `{model_id}`", f"- pairs: {len(rows)}  scored: {len(scored)}",
             f"- parse failures (empty label): {n_parse_fail}",
             f"- **accuracy: {acc:.4f}**", "",
             "## confusion (gt -> pred)", "", "| gt | pred | n |", "|----|------|---|"]
    for (g, p), n in sorted(conf.items(), key=lambda x: -x[1]):
        lines.append(f"| {g} | {p} | {n} |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"  -> accuracy {acc:.4f}  (parse failures {n_parse_fail})  {path.name}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(GEN_MODELS),
                    help="comma-separated GEN_MODELS keys")
    args = ap.parse_args()

    obl_text, obl_ids = obligation_block()
    m = gt_master()
    gt = {(r.company_id, r.obligation_id): r.relevance for r in m.itertuples(index=False)}
    companies = sorted(m["company_id"].unique())
    missing_md = [c for c in companies if not (MD_DIR / f"{c}.md").exists()]
    if missing_md:
        raise SystemExit(f"missing md reports for: {missing_md}")
    print(f"companies={len(companies)} obligations={len(obl_ids)} pairs={len(m)}")

    for mk in [x.strip() for x in args.models.split(",") if x.strip()]:
        if mk not in GEN_MODELS:
            raise SystemExit(f"unknown model key {mk!r}; valid: {list(GEN_MODELS)}")
        run_model(mk, companies, gt, obl_text, obl_ids)


if __name__ == "__main__":
    main()
