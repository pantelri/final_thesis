"""Load Offenlegungspflichten metadata from the Requirements JSON file."""
from __future__ import annotations
import json
from pathlib import Path


def load_requirements(path: str | Path) -> dict[str, dict]:
    """Return mapping R-code (e.g. 'R04') -> metadata dict."""
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    req_map: dict[str, dict] = {}
    for item in raw["requirements"]:
        code: str = item["id"]
        req_map[code] = {
            "category": item["category"],
            "title_de": item["title_de"],
            "title_en": item.get("title_en", ""),
            "legal_basis": item.get("legal_basis", ""),
            "applicability_type": item.get("applicability", {}).get("type", ""),
        }
    return req_map
