"""QueryEmbedder — embed plain query strings for one embedding model, with an
on-disk cache (keyed by input hash) and model-aware truncation.

Why truncation: gemini-embedding-001 has a 2048-token input limit. Dense tabular
GT evidence (the one/two-shot query variants) is ~2 chars/token, so a char-only
cap is NOT safe — it can still exceed 2048 tokens, OpenRouter then returns an
empty payload. We truncate by both a char budget and a tiktoken token budget, and
keep an adaptive shrink-on-empty-payload backstop so no single query can crash a
run. All truncations are logged for reproducibility.
"""
from __future__ import annotations

import hashlib
import json
import time
from functools import lru_cache

from scripts.eval._common import EMBED_MODELS, RESULTS
from scripts.eval.lib.openrouter import make_client

CACHE_DIR = RESULTS / "_qcache"
CACHE_DIR.mkdir(exist_ok=True)
_TRUNC_LOG = CACHE_DIR / "truncations.log"

# Conservative char budgets (gemini-embedding-001 ~2048 tokens; qwen3-embedding-8b
# far larger). Token budget applies the hard model limit with headroom for the
# gemini/cl100k tokenizer mismatch.
MAX_QUERY_CHARS = {"gemini": 6000, "qwen3": 16000}
MAX_QUERY_TOKENS = {"gemini": 1800}


@lru_cache(maxsize=1)
def _tok_enc():
    import tiktoken
    return tiktoken.get_encoding("cl100k_base")


def truncate_tokens(text: str, max_tokens: int) -> str:
    enc = _tok_enc()
    ids = enc.encode(text)
    if len(ids) <= max_tokens:
        return text
    return enc.decode(ids[:max_tokens])


def _sha1(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


class QueryEmbedder:
    """Embeds plain queries for one embedding model, cached by (truncated) text
    hash. Truncates inputs above the model's char/token budget (logged)."""

    def __init__(self, embed_key: str):
        self.embed_key = embed_key
        self.model_id = EMBED_MODELS[embed_key]
        self.max_chars = MAX_QUERY_CHARS.get(embed_key, 6000)
        self.max_tokens = MAX_QUERY_TOKENS.get(embed_key)
        self.cache_path = CACHE_DIR / f"qemb_{embed_key}.jsonl"
        self._cache: dict[str, list[float]] = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._cache[rec["h"]] = rec["v"]
        self._client = None

    def _log(self, kind: str, msg: str, text: str) -> None:
        with open(_TRUNC_LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{self.embed_key}\t{kind}\t{msg}\t{text[:50]!r}\n")

    def embed(self, text: str) -> list[float]:
        if len(text) > self.max_chars:
            self._log("chars", f"{len(text)}->{self.max_chars}", text)
            text = text[: self.max_chars]
        if self.max_tokens is not None:
            shrunk = truncate_tokens(text, self.max_tokens)
            if shrunk != text:
                self._log("tokens", f"->{self.max_tokens}tok", text)
                text = shrunk
        h = _sha1(text)
        if h in self._cache:
            return self._cache[h]
        if self._client is None:
            self._client = make_client()
        # Adaptive backstop: if OpenRouter persistently returns an empty payload
        # (some dense inputs still trip the model even under the token cap), halve
        # the input and retry down to a floor so no single query crashes the run.
        cur = text
        floor_chars = 200
        while True:
            try:
                vec = self._embed_once(cur)
                break
            except Exception:
                if len(cur) <= floor_chars:
                    raise
                new_len = max(floor_chars, len(cur) // 2)
                self._log("shrink", f"{len(cur)}->{new_len}", cur)
                cur = cur[:new_len]
        self._cache[h] = vec
        with open(self.cache_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"h": h, "v": vec}) + "\n")
        return vec

    def _embed_once(self, text: str) -> list[float]:
        """One embedding call with retry+backoff on transient empty payloads.
        Raises after 6 attempts so the adaptive backstop in embed() can shrink."""
        for attempt in range(1, 7):
            try:
                resp = self._client.embeddings.create(model=self.model_id, input=[text])
                if not resp.data:
                    raise ValueError("empty payload")
                return resp.data[0].embedding
            except Exception:
                if attempt == 6:
                    raise
                time.sleep(min(2 ** attempt, 30))
