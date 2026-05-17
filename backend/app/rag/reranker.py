"""
Cross-encoder re-ranker using ms-marco-MiniLM-L-6-v2.
Re-scores query–chunk pairs for precise relevance ranking.
Adds ~200–400ms latency; query caching offsets this for repeated queries.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_reranker = None
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def warm_up_reranker() -> None:
    """Load the reranker model at startup to avoid cold-start latency."""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        logger.info("Loading reranker model: %s", RERANKER_MODEL)
        _reranker = CrossEncoder(RERANKER_MODEL, max_length=512)
        logger.info("Reranker model loaded")


def get_reranker():
    global _reranker
    if _reranker is None:
        warm_up_reranker()
    return _reranker


def rerank_chunks(
    query: str,
    chunks: List[Dict],
    top_k: int | None = None,
) -> List[Dict]:
    """
    Re-rank retrieved chunks using a cross-encoder relevance model.

    Args:
        query:  The user's original (or rewritten) query.
        chunks: List of retrieved chunk dicts (must have 'text' key).
        top_k:  Return only the top_k highest-scored chunks.

    Returns:
        Chunks sorted by rerank_score descending, limited to top_k.
    """
    if not chunks:
        return []

    try:
        reranker = get_reranker()
        pairs = [(query, chunk.get("text", "")[:512]) for chunk in chunks]
        scores = reranker.predict(pairs)

        for chunk, score in zip(chunks, scores):
            chunk["rerank_score"] = float(score)

        ranked = sorted(chunks, key=lambda x: x.get("rerank_score", 0.0), reverse=True)

        if top_k:
            ranked = ranked[:top_k]

        logger.debug(
            "Reranked %d chunks → top %d | best score: %.3f",
            len(chunks),
            len(ranked),
            ranked[0]["rerank_score"] if ranked else 0.0,
        )
        return ranked

    except Exception as exc:
        logger.warning("Reranker failed, returning original order: %s", exc)
        # Graceful fallback: use similarity score
        fallback = sorted(
            chunks, key=lambda x: x.get("similarity_score", 0.0), reverse=True
        )
        return fallback[:top_k] if top_k else fallback
