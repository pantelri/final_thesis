"""Generiert angereicherte Pflichtentexte (retrieval_text) via Claude.

Jede Offenlegungspflicht erhält einen semantisch passenden Beispieltext,
der dem Sprachstil eines HGB-Jahresabschlusses entspricht. Dieser Text
dient als Embedding-Query und ist semantisch näher am tatsächlichen
Berichtstext als das abstrakte verification_criterion.

Ausgabe:
  Requirements/offenlegungspflichten_enriched.json   — Angereicherte Pflichten
  Requirements/api_costs_enrichment.json             — API-Kosten (Tokens + Schätzpreis)

Nutzung:
  python generate_enriched_requirements.py            # einmalige Generierung
  python generate_enriched_requirements.py --force    # Neuerstellen erzwingen
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import time
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

_ROOT    = Path(__file__).parent
REQ_IN   = _ROOT / "Requirements" / "offenlegungspflichten_gefiltert.json"
REQ_OUT  = _ROOT / "Requirements" / "offenlegungspflichten_enriched.json"
COST_OUT = _ROOT / "Requirements" / "api_costs_enrichment.json"

MODEL = "anthropic/claude-opus-4.8"

# OpenRouter-Preise für claude-opus-4.8 (USD pro 1M Tokens)
PRICE_INPUT_PER_MTOK  = 5.0
PRICE_OUTPUT_PER_MTOK = 25.0

_SYSTEM = (
    "Du bist ein Experte für HGB-Jahresabschlüsse und Lageberichte. "
    "Formuliere einen typischen, authentisch klingenden deutschen Textabschnitt, "
    "der in einem HGB-Lagebericht oder Anhang stehen würde und die angegebene "
    "Offenlegungspflicht inhaltlich erfüllt. "
    "Schreibe ausschließlich den Berichtstext (50–120 Wörter), "
    "ohne Überschriften, Einleitung oder Meta-Kommentare."
)


def _make_client():
    from openai import OpenAI
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY nicht gesetzt.")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)


def _generate_retrieval_text(client, req: dict) -> tuple[str, dict]:
    """Ruft Claude auf und gibt (retrieval_text, usage_dict) zurück."""
    user = (
        f"Pflicht-ID: {req['id']}\n"
        f"Titel: {req['title_de']}\n"
        f"Rechtsgrundlage: {req['legal_basis']}\n"
        f"Kategorie: {req['category']}\n"
        f"Prüfungskriterium: {req['verification_criterion']}\n\n"
        "Schreibe einen typischen HGB-Berichtstext (50–120 Wörter), "
        "der diese Offenlegungspflicht erfüllt:"
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": user},
        ],
        max_tokens=350,
        temperature=0.2,
    )
    text  = response.choices[0].message.content.strip()
    usage = {
        "prompt_tokens":     response.usage.prompt_tokens,
        "completion_tokens": response.usage.completion_tokens,
        "total_tokens":      response.usage.total_tokens,
    }
    return text, usage


def main(force: bool = False) -> None:
    if REQ_OUT.exists() and not force:
        logger.info("Angereichertes JSON bereits vorhanden: %s", REQ_OUT)
        logger.info("Verwende --force zum Neuerstellen.")
        return

    data = json.loads(REQ_IN.read_text(encoding="utf-8"))
    reqs: list[dict] = data.get("requirements", data) if isinstance(data, dict) else data

    client = _make_client()
    cost_records: list[dict] = []
    total_in = total_out = 0

    for req in reqs:
        rid = req["id"]
        logger.info("Generiere retrieval_text für %s …", rid)
        try:
            text, usage = _generate_retrieval_text(client, req)
            req["retrieval_text"] = text
            cost_records.append({"req_id": rid, **usage})
            total_in  += usage["prompt_tokens"]
            total_out += usage["completion_tokens"]
            logger.info(
                "  %s: %d+%d Tokens | Text: %s…",
                rid, usage["prompt_tokens"], usage["completion_tokens"], text[:60],
            )
            time.sleep(0.5)
        except Exception as exc:
            logger.error("Fehler bei %s: %s — Fallback auf verification_criterion.", rid, exc)
            req["retrieval_text"] = req.get("verification_criterion", "")

    REQ_OUT.write_text(
        json.dumps({"requirements": reqs}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Angereichertes JSON: %s", REQ_OUT)

    est_cost = (
        total_in  / 1_000_000 * PRICE_INPUT_PER_MTOK +
        total_out / 1_000_000 * PRICE_OUTPUT_PER_MTOK
    )
    cost_summary = {
        "model":                  MODEL,
        "n_requirements":         len(reqs),
        "total_input_tokens":     total_in,
        "total_output_tokens":    total_out,
        "total_tokens":           total_in + total_out,
        "estimated_cost_usd":     round(est_cost, 5),
        "price_input_per_mtok":   PRICE_INPUT_PER_MTOK,
        "price_output_per_mtok":  PRICE_OUTPUT_PER_MTOK,
        "per_requirement":        cost_records,
    }
    COST_OUT.write_text(
        json.dumps(cost_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "API-Kosten gespeichert: %s  (geschätzt %.5f USD | %d Eingabe + %d Ausgabe Tokens)",
        COST_OUT, est_cost, total_in, total_out,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Anreicherung der Pflichten via Claude")
    parser.add_argument("--force", action="store_true", help="Vorhandene Datei überschreiben")
    args = parser.parse_args()
    main(force=args.force)
