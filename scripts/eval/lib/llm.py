"""ChatClient — cached, retrying chat-completions over OpenRouter.

Used by the Phase-2 table-summary arm and (later) the Phase-4 generation steps.
Responses are cached on disk (JSONL, keyed by a hash of model + system + user +
sampling params) so re-runs are free and deterministic. Default temperature 0.0
for reproducibility.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from scripts.eval.lib.openrouter import make_client


def _req_hash(model: str, system: str, user: str, temperature: float, max_tokens: int,
              response_format=None) -> str:
    parts = [model, system, user, temperature, max_tokens]
    # Append only when set so existing caches (response_format=None) keep their hash.
    if response_format is not None:
        parts.append(response_format)
    blob = json.dumps(parts, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


class ChatClient:
    """One chat model, cached by request hash. Call complete(system, user)."""

    def __init__(self, model_id: str, cache_path: Path, *, temperature: float = 0.0,
                 max_tokens: int = 1024, max_retries: int = 6, response_format=None):
        self.model_id = model_id
        self.cache_path = Path(cache_path)
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.max_retries = max_retries
        self.response_format = response_format   # e.g. {"type": "json_object"}; None = unset
        self._cache: dict[str, str] = {}
        if self.cache_path.exists():
            for line in self.cache_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    rec = json.loads(line)
                    self._cache[rec["h"]] = rec["text"]
        self._client = None
        self._lock = threading.Lock()        # guards _cache + cache-file appends

    def complete(self, system: str, user: str, *, temperature: float | None = None,
                 max_tokens: int | None = None, response_format=None) -> str:
        temp = self.temperature if temperature is None else temperature
        mt = self.max_tokens if max_tokens is None else max_tokens
        rf = self.response_format if response_format is None else response_format
        h = _req_hash(self.model_id, system, user, temp, mt, rf)
        with self._lock:
            if h in self._cache:
                return self._cache[h]
            if self._client is None:
                self._client = make_client()
        # API call OUTSIDE the lock so parallel requests overlap
        text = self._complete_once(system, user, temp, mt, rf)
        with self._lock:
            self._cache[h] = text
            with open(self.cache_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"h": h, "model": self.model_id, "text": text},
                                    ensure_ascii=False) + "\n")
        return text

    def complete_many(self, items: list[tuple], *, max_workers: int = 8,
                      on_done=None) -> dict:
        """Run many (key, system, user) requests concurrently; return {key: text}.

        Cached items resolve instantly (no API call). max_workers bounds in-flight
        requests. on_done(key, idx, total) is invoked after each completion for
        progress reporting. Reusable for any batch chat workload (e.g. Phase-4 gen).
        """
        results: dict = {}
        total = len(items)
        counter = {"n": 0}
        cnt_lock = threading.Lock()

        def _work(item):
            key, system, user = item
            text = self.complete(system, user)
            results[key] = text
            if on_done is not None:
                with cnt_lock:
                    counter["n"] += 1
                    on_done(key, counter["n"], total)
            return key

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            list(ex.map(_work, items))
        return results

    def _complete_once(self, system: str, user: str, temperature: float, max_tokens: int,
                       response_format=None) -> str:
        kwargs = {}
        if response_format is not None:
            kwargs["response_format"] = response_format
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model_id,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs,
                )
                if not resp.choices:
                    raise ValueError("empty choices")
                content = resp.choices[0].message.content
                if not content or not content.strip():
                    raise ValueError("empty content")
                return content.strip()
            except Exception as exc:
                # 401 = invalid/expired key, 403 = key/credit limit: retrying cannot help, fail fast.
                if getattr(exc, "status_code", None) in (401, 403):
                    raise
                if attempt == self.max_retries:
                    raise
                time.sleep(min(2 ** attempt, 30))
