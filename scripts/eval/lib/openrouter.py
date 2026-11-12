"""OpenRouter client factory — single place that constructs the OpenAI-compatible
client used for both embeddings and chat completions across all phases."""
from __future__ import annotations

from scripts.eval._common import load_openrouter_key

BASE_URL = "https://openrouter.ai/api/v1"


def make_client(api_key: str | None = None):
    """Return an OpenAI client pointed at OpenRouter. Reads the key from
    annotation_app/.env (via _common) when not passed explicitly."""
    from openai import OpenAI
    return OpenAI(api_key=api_key or load_openrouter_key(), base_url=BASE_URL)
