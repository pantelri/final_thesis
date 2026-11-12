"""Parse a single-label JSON answer ({"label", "reason"}) from an LLM response.

Strict full-object json.loads first; on failure (e.g. a reasoning model truncated
the object) fall back to a per-field regex salvage. Generic over the allowed label
set so any stage can reuse it. Returns ("", "") when no valid label is recoverable.
"""
from __future__ import annotations

import json
import re
from collections.abc import Iterable


def _salvage(text: str, labels: Iterable[str]) -> tuple[str, str]:
    alt = "|".join(re.escape(x) for x in labels)
    m = re.search(r'"label"\s*:\s*"(' + alt + r')"'
                  r'(?:[^{}]*?"reason"\s*:\s*"((?:[^"\\]|\\.)*)")?',
                  text, re.DOTALL | re.IGNORECASE)
    if not m:
        return "", ""
    return m.group(1).lower(), (m.group(2) or "").strip()


def parse_label(text: str, labels: Iterable[str]) -> tuple[str, str]:
    labels = set(labels)
    s = re.sub(r"```(?:json)?", "", text).strip() if "```" in text else text.strip()
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            lab = str(obj.get("label", "")).strip().lower()
            if lab in labels:
                return lab, str(obj.get("reason", "")).strip()
        except json.JSONDecodeError:
            pass
    return _salvage(s, labels)
