from __future__ import annotations

from .models import ChunkResult


def _parse_chunk_id(chunk_id: str) -> tuple[str, int]:
    """Parse ``'Amazon_2024_0042'`` → ``('Amazon_2024', 42)``."""
    pos     = chunk_id.rfind("_")
    company = chunk_id[:pos]
    index   = int(chunk_id[pos + 1:])
    return company, index


def _build_chunk_id(company: str, index: int) -> str:
    return f"{company}_{index:04d}"


def _chroma_row_to_chunk(
    chroma_id: str,
    document:  str,
    metadata:  dict,
    score:     float = 0.0,
) -> ChunkResult:
    company, idx = _parse_chunk_id(chroma_id)
    return ChunkResult(
        text        = document,
        chunk_index = idx,
        start_char  = metadata.get("char_start", 0),
        end_char    = metadata.get("char_end", 0),
        document_id = metadata.get("company", company),
        score       = score,
        metadata    = {**metadata, "_chunk_id": chroma_id},
    )


def _merge_metadata(chunks: list[ChunkResult]) -> dict:
    companies = sorted({c.document_id for c in chunks})
    headings  = sorted({
        c.metadata.get("heading_path", "")
        for c in chunks
        if c.metadata.get("heading_path")
    })
    chunk_ids = [c.metadata.get("_chunk_id", "") for c in chunks]
    return {
        "companies":     companies,
        "heading_paths": headings,
        "chunk_ids":     chunk_ids,
    }
