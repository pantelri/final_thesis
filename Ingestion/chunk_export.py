"""Export finalised chunks to JSONL and CSV.

Each output record has exactly the fields specified in the metadata schema:
    chunk_id, company, heading_path, char_start, char_end,
    is_table, n_tokens, text
n_tokens is approximated as len(text) // 4 (rough German-text token estimate).
"""
from __future__ import annotations
import csv
import json
from pathlib import Path

_FIELDS = ['chunk_id', 'company', 'heading_path',
           'char_start', 'char_end', 'is_table', 'n_tokens', 'text']


def _to_records(chunks: list[dict], company: str) -> list[dict]:
    records = []
    for i, c in enumerate(chunks, start=1):
        records.append({
            'chunk_id':     f"{company}_{i:04d}",
            'company':      company,
            'heading_path': c.get('heading_path', ''),
            'char_start':   c['char_start'],
            'char_end':     c['char_end'],
            'is_table':     bool(c.get('is_table', False)),
            'n_tokens':     len(c['text']) // 4,
            'text':         c['text'],
        })
    return records


def export_jsonl(chunks: list[dict], company: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for rec in _to_records(chunks, company):
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def export_csv(chunks: list[dict], company: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _to_records(chunks, company)
    if not records:
        return
    with open(path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        writer.writeheader()
        writer.writerows(records)


def append_jsonl(chunks: list[dict], company: str, path: Path) -> None:
    """Append records to an existing JSONL (used for combined multi-company output)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'a', encoding='utf-8') as f:
        for rec in _to_records(chunks, company):
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def append_csv(chunks: list[dict], company: str, path: Path,
               write_header: bool = False) -> None:
    """Append records to a combined CSV (write_header=True for the first company)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _to_records(chunks, company)
    if not records:
        return
    mode = 'w' if write_header else 'a'
    with open(path, mode, newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDS)
        if write_header:
            writer.writeheader()
        writer.writerows(records)
