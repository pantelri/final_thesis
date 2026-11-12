"""Interaktiver Test für die Retrieval/Review-Pipeline.

Ablauf:
    1. Pflicht aus Requirements/ auswählen (CSV oder JSON)
    2. Firma aus import.json auswählen
    3. Review-Pipeline ausführen und Ergebnis anzeigen

Erforderlich:
    OPENROUTER_API_KEY Umgebungsvariable
"""
from __future__ import annotations

import csv
import json
import logging
import os
from functools import partial
from pathlib import Path

_ROOT = Path(__file__).parent

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

REQUIREMENTS_CSV  = _ROOT / "Requirements" / "offenlegungspflichten_gefiltert.csv"
REQUIREMENTS_JSON = _ROOT / "Requirements" / "offenlegungspflichten_gefiltert.json"
IMPORT_JSON       = _ROOT / "import.json"


# ── Laden der Pflichten ───────────────────────────────────────────────────────

def _load_requirements_csv() -> list[dict]:
    with REQUIREMENTS_CSV.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _load_requirements_json() -> list[dict]:
    data = json.loads(REQUIREMENTS_JSON.read_text(encoding="utf-8"))
    return data.get("requirements", data) if isinstance(data, dict) else data


def choose_requirement() -> dict:
    print("\nQuelle für Pflichten:")
    print("  1) CSV")
    print("  2) JSON")
    choice = input("Auswahl [1/2, Standard: 1]: ").strip() or "1"
    reqs = _load_requirements_csv() if choice != "2" else _load_requirements_json()

    print(f"\n{len(reqs)} Pflichten verfügbar:\n")
    for i, r in enumerate(reqs, 1):
        rid   = r.get("id", "?")
        title = r.get("title_de", r.get("title_en", ""))
        print(f"  {i:>3}. [{rid}] {title}")

    while True:
        raw = input(f"\nPflicht auswählen [1–{len(reqs)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(reqs):
            return reqs[int(raw) - 1]
        print("Ungültige Eingabe.")


# ── Laden der Firmen ──────────────────────────────────────────────────────────

def _load_companies() -> list[str]:
    tasks = json.loads(IMPORT_JSON.read_text(encoding="utf-8"))
    seen: set[str] = set()
    companies: list[str] = []
    for task in tasks:
        company = task.get("data", {}).get("company", "")
        if company and company not in seen:
            seen.add(company)
            companies.append(company)
    return sorted(companies)


def choose_company() -> str:
    companies = _load_companies()
    print(f"\n{len(companies)} Firmen verfügbar:\n")
    for i, c in enumerate(companies, 1):
        print(f"  {i:>3}. {c}")

    while True:
        raw = input(f"\nFirma auswählen [1–{len(companies)}]: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(companies):
            return companies[int(raw) - 1]
        print("Ungültige Eingabe.")


# ── Hilfsfunktionen ───────────────────────────────────────────────────────────

def _build_query(req: dict) -> str:
    return req.get("verification_criterion", req.get("title_de", ""))


def _print_result(result) -> None:
    sep = "═" * 70
    print(f"\n{sep}")
    print("  REVIEW RESULT")
    print(sep)
    print(f"  document_id          : {result.document_id}")
    print(f"  source_chunk_indices : {result.source_chunk_indices}")
    print(f"  final_start_char     : {result.final_start_char}")
    print(f"  final_end_char       : {result.final_end_char}")
    print(f"  review_rounds        : {result.review_rounds}")
    print(f"  actions_taken        : {result.actions_taken}")
    print(f"  retrieval_scores     : {[round(s, 4) for s in result.retrieval_scores]}")
    print(f"\n  metadata:")
    for k, v in result.metadata.items():
        print(f"    {k}: {v}")
    print(f"\n  final_text ({len(result.final_text)} chars):")
    print("  " + "-" * 66)
    for line in result.final_text.splitlines():
        print(f"  {line}")
    print(sep)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY nicht gesetzt.")

    from Ingestion.embed_pipeline import (
        COLLECTION_NAME,
        MODELS,
        _make_client,
        embed_query,
        open_collection,
    )
    from Retrieval import RetrievalReviewModule

    requirement = choose_requirement()
    company     = choose_company()

    query = _build_query(requirement)
    logger.info("Query:  %s", query)
    logger.info("Firma:  %s", company)
    logger.info("Pflicht: [%s] %s", requirement.get("id"), requirement.get("title_de"))

    for model_key in ("qwen3", "gemini"):
        try:
            collection = open_collection(model_key, COLLECTION_NAME)
            logger.info("Collection '%s' geladen (%d Chunks).", model_key, collection.count())
            break
        except Exception:
            logger.warning("Collection '%s' nicht gefunden – versuche nächstes.", model_key)
    else:
        raise SystemExit(
            "Keine ChromaDB-Collection gefunden. "
            "Bitte zuerst: python -m Ingestion.embed_pipeline"
        )

    or_client = _make_client(api_key)
    embed_fn  = partial(embed_query, model_id=MODELS[model_key], client=or_client)

    module = RetrievalReviewModule(collection=collection, embed_fn=embed_fn)
    result = module.run(query=query, filters={"company": company}, top_n=5)

    _print_result(result)


if __name__ == "__main__":
    main()
