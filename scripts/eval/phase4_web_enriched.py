"""Phase 4 prep — build the `web_enriched` verification-context variant.

For the fulfillment stage (Phase 4b, hypothesis H2) the verifier judges each
retrieved-evidence passage against a *reference description* of the obligation.
Two context variants are compared:

  statute_only : legal_basis + verification_criterion (verbatim, no generation;
                 assembled at verification time — nothing to precompute here).
  web_enriched : an LLM-expanded German reference description that draws on the
                 model's knowledge of the underlying standard (HGB/DRS/IFRS) to
                 spell out WHAT must be disclosed and HOW to recognise fulfilment.

This script generates only the `web_enriched` text (13 obligations, one-time).
It is NOT an example compliant passage (that is `retrieval_text`, used for
RETRIEVAL queries) — using a fabricated answer as the judging criterion would
bias the verifier toward "fulfilled". This is a description of the *requirement*.

Generator model: claude-opus-4-8 (strongest; accuracy of the standard-knowledge
matters). NOTE: this model is also a Phase-4b verifier, so document the shared
context when reporting H2. The same text is given to all verifiers, so it is a
fair common input.

Run: python -m scripts.eval.phase4_web_enriched
Output: Requirements/offenlegungspflichten_web_enriched.json  (keyed by obligation id)
"""
from __future__ import annotations

import json

from scripts.eval._common import ENRICHED_JSON, GEN_MODELS, RESULTS, ROOT
from scripts.eval.lib.llm import ChatClient

OUT_JSON = ROOT / "Requirements" / "offenlegungspflichten_web_enriched.json"
CACHE = RESULTS / "_qcache" / "web_enriched_claude.jsonl"
MODEL = GEN_MODELS["claude_opus_4_8"]

SYSTEM = (
    "Du bist ein erfahrener Wirtschaftsprüfer und Experte für handelsrechtliche "
    "Rechnungslegung (HGB), die Deutschen Rechnungslegungs Standards (DRS) und IFRS. "
    "Du formulierst präzise, fachlich korrekte Referenzbeschreibungen von Pflichtangaben "
    "im Anhang und Lagebericht deutscher Jahresabschlüsse."
)

USER_TMPL = """Erstelle eine angereicherte deutsche Referenzbeschreibung (Kontext) für die folgende \
Offenlegungspflicht. Diese Beschreibung dient einem Prüfer als Maßstab, um zu beurteilen, ob ein \
Jahresabschluss die Pflichtangabe erfüllt.

Pflichtangabe-ID: {id}
Titel: {title_de}
Rechtsgrundlage: {legal_basis}
Kategorie: {category}
Prüfkriterium: {verification_criterion}

Nutze dein Wissen über den zugrunde liegenden Standard und erläutere:
- WAS konkret angegeben werden muss (erforderliche Inhalte, typische Bestandteile),
- WORAN man die Erfüllung erkennt (welche Formulierungen/Angaben ausreichen),
- typische Grenz- oder Teilerfüllungsfälle, falls relevant.

Vorgaben:
- Erfinde KEINE konkreten Unternehmenszahlen oder -namen.
- Beschreibe die Anforderung allgemein, nicht ein Beispieldokument.
- Schreibe sachlichen deutschen Fließtext, ca. 150–250 Wörter, keine Aufzählungszeichen.
Gib NUR die Referenzbeschreibung aus, ohne Vorrede."""


def obligations() -> list[dict]:
    return json.loads(ENRICHED_JSON.read_text(encoding="utf-8"))["requirements"]


def main() -> None:
    obls = obligations()
    client = ChatClient(MODEL, CACHE, temperature=0.0, max_tokens=900)
    items = [
        (
            o["id"],
            SYSTEM,
            USER_TMPL.format(
                id=o["id"],
                title_de=o.get("title_de", ""),
                legal_basis=o.get("legal_basis", ""),
                category=o.get("category", ""),
                verification_criterion=o.get("verification_criterion", ""),
            ),
        )
        for o in obls
    ]
    print(f"generating web_enriched context for {len(items)} obligations via {MODEL}")
    texts = client.complete_many(
        items, max_workers=6,
        on_done=lambda key, n, total: print(f"  [{n}/{total}] {key} done"),
    )

    out = {}
    for o in obls:
        oid = o["id"]
        out[oid] = {
            "id": oid,
            "title_de": o.get("title_de", ""),
            "legal_basis": o.get("legal_basis", ""),
            "verification_criterion": o.get("verification_criterion", ""),
            "web_enriched_text": texts[oid],
        }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    lens = [len(v["web_enriched_text"]) for v in out.values()]
    print(f"\nwrote {OUT_JSON}")
    print(f"  obligations={len(out)}  char-len min/median/max="
          f"{min(lens)}/{sorted(lens)[len(lens)//2]}/{max(lens)}")


if __name__ == "__main__":
    main()
