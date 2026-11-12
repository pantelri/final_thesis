"""Reusable building blocks for the evaluation harness.

Phase scripts (scripts/eval/phaseN_*.py) stay thin orchestration; the reusable
units live here so later phases import the piece they need:

  openrouter : OpenRouter client factory (embeddings + chat).
  embedder   : QueryEmbedder — cached, truncation-safe query embedding.
  llm        : ChatClient — cached, retrying chat-completions (summaries, Phase 4).
  chroma     : open_collection / retrieve — ChromaDB top-k by company.
  metrics    : span-overlap retrieval metrics (recall/hit/precision/MRR).
  gt         : load the frozen retrieval GT snapshot into eval structures.
  queries    : build retrieval query strings from the enriched obligations.
"""
