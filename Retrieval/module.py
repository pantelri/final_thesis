from __future__ import annotations

import logging
from typing import Callable

import chromadb

from .actions import apply_trim, apply_remove_sentence, fetch_neighbor
from .helpers import _chroma_row_to_chunk, _merge_metadata
from .llm_client import ReviewLLMError, build_review_prompt, call_review_llm, get_llm_config
from .models import ChunkResult, ReviewResult
from .sentence_splitter import SentenceSplitter

logger = logging.getLogger(__name__)


class RetrievalReviewModule:
    """Retrieve relevant chunks and iteratively refine them via an LLM review loop."""

    def __init__(
        self,
        collection: chromadb.Collection,
        embed_fn:   Callable[[str], list[float]],
    ) -> None:
        self._col        = collection
        self._embed_fn   = embed_fn
        self._splitter   = SentenceSplitter()
        self._model, self._base_url, self._api_key, self._max_rounds = get_llm_config()

    def retrieve(self, query: str, filters: dict, top_n: int = 5) -> list[ChunkResult]:
        """Query ChromaDB and return the top-N chunks sorted by relevance."""
        q_vec  = self._embed_fn(query)
        kwargs: dict = dict(
            query_embeddings=[q_vec],
            n_results=min(top_n, self._col.count()),
            include=["documents", "metadatas", "distances"],
        )
        if filters:
            kwargs["where"] = filters

        res = self._col.query(**kwargs)

        results: list[ChunkResult] = []
        for chroma_id, doc, meta, dist in zip(
            res["ids"][0],
            res["documents"][0],
            res["metadatas"][0],
            res["distances"][0],
        ):
            score = max(0.0, 1.0 - dist)
            results.append(_chroma_row_to_chunk(chroma_id, doc, meta, score))

        results.sort(key=lambda c: c.score, reverse=True)
        logger.debug("Retrieval: %d Ergebnisse für Query '%s'", len(results), query[:60])
        return results

    def retrieve_raw(self, query: str, filters: dict, top_n: int = 5) -> list[dict]:
        """Wie retrieve(), aber gibt rohe Dicts zurück — vor dem Review-Loop.

        Jedes Dict enthält: chunk_id, rank, score, char_start, char_end,
        heading_path, text (vollständig).
        Gedacht für Chunk-Level Hit@k-Auswertung.
        """
        chunks = self.retrieve(query, filters, top_n=top_n)
        return [
            {
                "rank":         i + 1,
                "chunk_id":     c.metadata.get("_chunk_id", ""),
                "score":        round(c.score, 5),
                "char_start":   c.start_char,
                "char_end":     c.end_char,
                "heading_path": c.metadata.get("heading_path", ""),
                "text":         c.text,
            }
            for i, c in enumerate(chunks)
        ]

    def get_all_chunks_for_company(self, company: str) -> list[dict]:
        """Alle Chunks einer Firma aus ChromaDB — für Offset-Spot-Check."""
        res = self._col.get(
            where={"company": {"$eq": company}},
            include=["documents", "metadatas"],
        )
        return [
            {
                "chunk_id":   res["ids"][i],
                "char_start": res["metadatas"][i].get("char_start", 0),
                "char_end":   res["metadatas"][i].get("char_end", 0),
                "text":       res["documents"][i],
            }
            for i in range(len(res["ids"]))
        ]

    def run(self, query: str, filters: dict, top_n: int = 5) -> ReviewResult:
        """Run the full retrieve-and-review pipeline."""
        retrieval_results = self.retrieve(query, filters, top_n=top_n)
        if not retrieval_results:
            logger.warning("Keine Ergebnisse für Query '%s'.", query)
            return ReviewResult(
                final_text="", document_id="", source_chunk_indices=[],
                final_start_char=0, final_end_char=0, review_rounds=0,
                actions_taken=[], retrieval_scores=[], metadata={},
            )

        included: list[ChunkResult] = [retrieval_results[0]]
        span_text  = retrieval_results[0].text
        queue      = retrieval_results[1:]
        history:   list[str] = []
        actions_taken: list[str] = []
        round_num  = 0

        for round_num in range(1, self._max_rounds + 1):
            logger.info("Runde %d/%d | Span: %d Zeichen | Queue: %d",
                        round_num, self._max_rounds, len(span_text), len(queue))

            prompt = build_review_prompt(query, round_num, history, span_text, len(queue))
            try:
                decision = call_review_llm(self._model, self._base_url, self._api_key, prompt)
            except ReviewLLMError as exc:
                logger.error("LLM-Fehler in Runde %d: %s – Abbruch.", round_num, exc)
                break

            action    = decision.get("action", "")
            reasoning = decision.get("reasoning", "")
            logger.info("Aktion: %s | Begründung: %s", action, reasoning)
            history.append(f"Runde {round_num}: {action} – {reasoning}")

            if action == "finalize":
                actions_taken.append("finalize")
                break
            elif action == "add_next_result":
                if not queue:
                    history[-1] += " (Queue leer, übersprungen)"
                    continue
                nxt = queue.pop(0)
                included.append(nxt)
                span_text = span_text + "\n\n" + nxt.text
                actions_taken.append("add_next_result")
            elif action == "trim_incomplete_sentence":
                pos = decision.get("trim_position", "end")
                span_text, trimmed = apply_trim(span_text, pos, self._splitter)
                if trimmed:
                    actions_taken.append(f"trim_incomplete_sentence:{pos}")
                else:
                    history[-1] += " (kein Fragment, übersprungen)"
            elif action == "remove_sentence":
                sentence = decision.get("sentence_to_remove", "")
                new_text = apply_remove_sentence(span_text, sentence)
                if new_text is not None:
                    span_text = new_text
                    actions_taken.append("remove_sentence")
                else:
                    history[-1] += " (Satz nicht gefunden, übersprungen)"
            elif action == "expand_neighbor":
                direction = decision.get("direction", "next")
                neighbor  = fetch_neighbor(included, direction, self._col)
                if neighbor is not None:
                    included.append(neighbor)
                    if direction == "previous":
                        span_text = neighbor.text + "\n\n" + span_text
                    else:
                        span_text = span_text + "\n\n" + neighbor.text
                    actions_taken.append(f"expand_neighbor:{direction}")
                else:
                    history[-1] += " (Nachbar nicht vorhanden, übersprungen)"
            else:
                logger.warning("Unbekannte Aktion '%s' – übersprungen.", action)
                history[-1] += f" (unbekannte Aktion '{action}', übersprungen)"
        else:
            logger.warning("REVIEW_MAX_ROUNDS (%d) erreicht – Finalisierung erzwungen.", self._max_rounds)
            actions_taken.append("max_rounds_reached")

        final_start = min(c.start_char for c in included)
        final_end   = max(c.end_char   for c in included)
        logger.info("Fertig nach %d Runde(n) | Aktionen: %s | Span: %d Zeichen",
                    round_num, actions_taken, len(span_text))

        return ReviewResult(
            final_text           = span_text,
            document_id          = included[0].document_id,
            source_chunk_indices = [c.chunk_index for c in included],
            final_start_char     = final_start,
            final_end_char       = final_end,
            review_rounds        = round_num,
            actions_taken        = actions_taken,
            retrieval_scores     = [c.score for c in included if c.score > 0.0],
            metadata             = _merge_metadata(included),
        )
