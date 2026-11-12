"""Reusable utilities for locating text spans within Markdown (.md) documents.

Use this wherever a (tokenized, drifted, or LLM-reworded) string must be mapped
back to its verbatim position in an original .md file — e.g. "find the place in
the .md where this passage came from".
"""
from .document import MdDocument
from .normalize import expand_span, find_all, norm_map

__all__ = ["MdDocument", "norm_map", "find_all", "expand_span"]
