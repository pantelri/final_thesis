"""Extract markdown table blocks from a section, preserving absolute char offsets.

A table block is a run of consecutive lines whose stripped form starts with '|'.
Tables are never split — each block becomes one atomic chunk (is_table=True).
Non-table content between or around tables becomes gap dicts (is_table=False).
"""
from __future__ import annotations


def _is_table_line(line: str) -> bool:
    return line.lstrip().startswith('|')


def _line_spans(text: str, abs_start: int) -> list[tuple[int, int]]:
    """Return (abs_start, abs_end) for every line including its newline character."""
    spans: list[tuple[int, int]] = []
    pos = 0
    while pos < len(text):
        nl  = text.find('\n', pos)
        end = nl + 1 if nl != -1 else len(text)
        spans.append((abs_start + pos, abs_start + end))
        pos = end
    return spans


def extract_tables_and_gaps(section: dict) -> tuple[list[dict], list[dict]]:
    """
    Partition a section into table chunks and text-gap dicts.

    Each item in the returned lists has:
        heading_path, char_start, char_end, text, is_table
    where text == original_md[char_start:char_end].
    """
    text      = section['text']
    abs_start = section['char_start']
    spans     = _line_spans(text, abs_start)

    tables: list[dict] = []
    gaps:   list[dict] = []

    i = 0
    while i < len(spans):
        ls, le   = spans[i]
        line_txt = text[ls - abs_start : le - abs_start]
        is_tbl   = _is_table_line(line_txt)

        block_start = ls
        block_end   = le
        i += 1

        # Extend block while lines have the same type
        while i < len(spans):
            ls2, le2 = spans[i]
            lt2      = text[ls2 - abs_start : le2 - abs_start]
            if _is_table_line(lt2) == is_tbl:
                block_end = le2
                i += 1
            else:
                break

        piece = _make_piece(section, block_start, block_end, is_table=is_tbl)
        if piece['text'].strip():          # skip whitespace-only gaps
            (tables if is_tbl else gaps).append(piece)

    return tables, gaps


def _make_piece(section: dict, cs: int, ce: int, *, is_table: bool) -> dict:
    offset = section['char_start']
    return {
        'heading_path': section['heading_path'],
        'char_start':   cs,
        'char_end':     ce,
        'text':         section['text'][cs - offset : ce - offset],
        'is_table':     is_table,
    }
