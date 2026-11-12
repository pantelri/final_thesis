"""Shared config, paths, constants, and helpers for the evaluation harness.

Run everything with the `thesis2` conda interpreter:
    python -m scripts.eval.<module>
from the repo root (source_code/).

Determinism: GLOBAL_SEED is fixed; the Efron bootstrap uses exactly N_BOOTSTRAP resamples.
"""
from __future__ import annotations

import os
import random
import subprocess
from pathlib import Path
from typing import NamedTuple

import numpy as np

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[2]          # .../source_code

# Root .env (see README "Environment Setup"); already-set variables take precedence.
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass
RESULTS = ROOT / "results"
PREDS = RESULTS / "preds"
LATEX = RESULTS / "latex"
FIGURES = RESULTS / "figures"
for _d in (RESULTS, PREDS, LATEX, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)

MD_DIR = ROOT / "Output" / "md_files"
CHUNKS_JSONL = ROOT / "Output" / "chunks" / "chunks.jsonl"
CHROMA_BASE = ROOT / "Output" / "chromadb"
ENRICHED_JSON = ROOT / "Requirements" / "offenlegungspflichten_enriched.json"
STALE_SPANS_CSV = ROOT / "gt_output" / "df1_spans.csv"
STALE_PFLICHTEN_CSV = ROOT / "gt_output" / "df2_pflichten.csv"
CLASSIFICATION_GT_DIR = ROOT / "Output" / "Classification_GTs"

# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #
GLOBAL_SEED = 42
N_BOOTSTRAP = 1000


def set_seeds(seed: int = GLOBAL_SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)


# --------------------------------------------------------------------------- #
# Database (canonical retrieval GT) — Postgres in container, port-mapped to host
# --------------------------------------------------------------------------- #
PG_HOST = os.environ.get("PGHOST", "127.0.0.1")
PG_PORT = os.environ.get("PGPORT", "5432")
PG_DB = os.environ.get("POSTGRES_DB", "annotation")
PG_USER = os.environ.get("POSTGRES_USER", "annotation")
PG_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
DB_URL = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}"


def get_engine():
    from sqlalchemy import create_engine
    return create_engine(DB_URL, future=True)


# --------------------------------------------------------------------------- #
# Canonical entities
# --------------------------------------------------------------------------- #
N_OBLIGATIONS = 13
N_COMPANIES = 14
N_ITEMS = N_OBLIGATIONS * N_COMPANIES  # 182

# --------------------------------------------------------------------------- #
# Label vocabularies & thesis mappings (see DISCOVERY_REPORT §2.3, §6b)
# --------------------------------------------------------------------------- #
# Stage-1 relevance = is_applicable
RELEVANCE_MAP = {"yes": "relevant", "no": "not_relevant", "unsure": "unclear"}
RELEVANCE_CLASSES = ["relevant", "not_relevant", "unclear"]

# Stage-3 fulfillment = is_fulfilled (unclear class dropped per author)
FULFILLMENT_MAP = {"yes": "fulfilled", "no": "not_fulfilled", "partially": "partially"}
FULFILLMENT_CLASSES = ["fulfilled", "not_fulfilled", "partially"]

# BERT-NLI entailment -> fulfillment mapping
NLI_TO_FULFILLMENT = {
    "entailment": "fulfilled",
    "contradiction": "not_fulfilled",
    "neutral": "partially",
}

# Generative LLMs (OpenRouter slugs, author-confirmed 2026-06-23)
GEN_MODELS = {
    "claude_opus_4_8": "anthropic/claude-opus-4-8",      # live-verified 2026-06-26
    "gemini_3_1_pro": "google/gemini-3.1-pro-preview",   # live-verified 2026-06-26 (slug needs -preview suffix)
    "qwen_3_7_max": "qwen/qwen3.7-max",                  # live-verified 2026-06-25
    "mimo_v2_5_pro": "xiaomi/mimo-v2.5-pro",             # live-verified 2026-06-26 (-> 'Hello!')
    # 2026-11 refresh: newer models (slugs verified on OpenRouter /models 2026-11-11)
    "claude_sonnet_5_5": "anthropic/claude-sonnet-5.5",
    "gemini_4_argon": "google/gemini-4-argon",
    "kimi_k3": "moonshotai/kimi-k3",
}
# Models of the 2026-11 refresh run (all reasoning models -> generous max_tokens).
REFRESH_MODELS = ["claude_sonnet_5_5", "gemini_4_argon", "kimi_k3"]
# BERT-NLI verification baseline (German/multilingual NLI). Concrete checkpoint
# pinned in Phase 4b; mapping in NLI_TO_FULFILLMENT.
BERT_NLI_MODEL = "MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7"

# Verification settings (author-confirmed)
VERIFICATION_K = 5
VERIFICATION_CONTEXT_VARIANTS = ["statute_only", "web_enriched"]

# Embedding models (OpenRouter slugs, from Ingestion/embed_pipeline.py)
EMBED_MODELS = {
    "qwen3": "qwen/qwen3-embedding-8b",
    "gemini": "google/gemini-embedding-001",  # "google-embedding-001" in the brief
}
# Existing (sliding-window/baseSeg) collections live at CHROMA_BASE/{gemini,qwen3}, name "hgb_chunks".
EXISTING_COLLECTION_NAME = "hgb_chunks"


class CollSpec(NamedTuple):
    """One corpus collection in the retrieval factorial.

    Factors: embed (embedding model) x seg (segmentation) x table_rep (how table
    chunks are turned into embedding input). table_rep:
      raw_md  : embed the verbatim markdown table (existing behaviour).
      llmdesc : embed a Qwen3.7-Max plain-text description of the table; the
                verbatim md is still kept as the chunk text/offsets for GT overlap
                and verification. text (non-table) chunks are identical to raw_md.
    """
    chroma_dir: Path
    name: str
    embed: str        # embedding-model key: "gemini" | "qwen3"
    seg: str          # "baseSeg" | "sentSeg"
    table_rep: str    # "raw_md" | "llmdesc"


# Corpus collections of the retrieval factorial: embedding x segmentation x
# table_rep. raw_md baseSeg = existing sliding-window (DO NOT rebuild); raw_md
# sentSeg = Phase-2 sentence-aware build; llmdesc = Phase-2 table-description arm.
COLLECTIONS = {
    # ---- raw_md (verbatim table markdown) ----
    "google001_baseSeg": CollSpec(CHROMA_BASE / "gemini", "hgb_chunks", "gemini", "baseSeg", "raw_md"),
    "qwen3_baseSeg": CollSpec(CHROMA_BASE / "qwen3", "hgb_chunks", "qwen3", "baseSeg", "raw_md"),
    "google001_sentSeg": CollSpec(CHROMA_BASE / "gemini_sentseg", "hgb_chunks", "gemini", "sentSeg", "raw_md"),
    "qwen3_sentSeg": CollSpec(CHROMA_BASE / "qwen3_sentseg", "hgb_chunks", "qwen3", "sentSeg", "raw_md"),
    # ---- llmdesc (Qwen3.7-Max table descriptions) ----
    "google001_baseSeg_llmdesc": CollSpec(CHROMA_BASE / "gemini_llmdesc_baseseg", "hgb_chunks", "gemini", "baseSeg", "llmdesc"),
    "qwen3_baseSeg_llmdesc": CollSpec(CHROMA_BASE / "qwen3_llmdesc_baseseg", "hgb_chunks", "qwen3", "baseSeg", "llmdesc"),
    "google001_sentSeg_llmdesc": CollSpec(CHROMA_BASE / "gemini_llmdesc_sentseg", "hgb_chunks", "gemini", "sentSeg", "llmdesc"),
    "qwen3_sentSeg_llmdesc": CollSpec(CHROMA_BASE / "qwen3_llmdesc_sentseg", "hgb_chunks", "qwen3", "sentSeg", "llmdesc"),
}

# Chunk corpora per segmentation (raw_md and llmdesc share the same chunk set;
# only the table chunks' embedding INPUT differs).
SENTSEG_JSONL = ROOT / "Output" / "chunks" / "chunks_sentseg.jsonl"
CHUNKS_BY_SEG = {"baseSeg": CHUNKS_JSONL, "sentSeg": SENTSEG_JSONL}
# Qwen3.7-Max table descriptions (Phase-2 llmdesc arm), keyed by table text-hash.
TABLE_SUMMARIES_JSONL = ROOT / "Output" / "chunks" / "table_summaries.jsonl"
TABLE_SUMMARY_MODEL = GEN_MODELS["qwen_3_7_max"]


def load_openrouter_key() -> str:
    """Read OPENROUTER_API_KEY from env, else from annotation_app/.env."""
    key = os.environ.get("OPENROUTER_API_KEY", "")
    if key:
        return key
    env_path = ROOT / "annotation_app" / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENROUTER_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def write_csv(path: Path, rows: list[dict], fieldnames: list[str] | None = None) -> None:
    """Deterministic CSV writer (utf-8, LF, stable column order)."""
    import csv
    if not rows and fieldnames is None:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = fieldnames or list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
