# Embedding models — decision & provenance

Both embedding models are served via **OpenRouter** (`https://openrouter.ai/api/v1`,
`OPENROUTER_API_KEY`), the same route used to build the existing sliding-window
collections (`Ingestion/embed_pipeline.py`).

| Brief name | OpenRouter slug | Dim | Status |
|---|---|---|---|
| qwen3 | `qwen/qwen3-embedding-8b` | 4096 | OK |
| google-embedding-001 | `google/gemini-embedding-001` | 3072 | **USED** |
| (candidate) | `google/gemini-embedding-2` | — | **NOT available on OpenRouter** (returns "No embedding data received") |

## Decision
We use **`google/gemini-embedding-001`** for the Google side (not `-2`).

- The author noted `google/gemini-embedding-001` is slated for deprecation and that
  `google/gemini-embedding-2` could be used instead. As of 2026-06-23, OpenRouter does
  **not** yet serve `gemini-embedding-2` (empty payload), so it cannot be used.
- Staying on `gemini-embedding-001` also keeps the new **sentSeg** collection on the
  **same model** as the existing **baseSeg** collection, so the 2×2 factorial isolates
  the segmentation effect (embedding model held constant). Switching one cell to a
  different embedding model would confound the comparison.

**If/when `gemini-embedding-2` becomes available** and a switch is desired, change
`EMBED_MODELS["gemini"]` in `scripts/eval/_common.py` AND re-embed **both** Google
collections (base + sent) so they remain on the same model, then update this file.

## Reliability note
OpenRouter's embedding endpoint intermittently returns an empty payload
("No embedding data received"). `scripts/eval/phase2_embed.py` wraps each batch in a
retry/backoff loop (up to 6 attempts, then batch-splitting) so a transient empty
response does not abort a full embedding run.

## Asymmetric setup (unchanged from embed_pipeline.py)
Documents are embedded as `"{heading_path}\n\n{text}"` (heading enrichment); queries
are embedded plain (no heading prefix). Cosine space. Query-time embedding must use the
same slug as the collection.
