"""
Hybrid Retriever — combines dense (Qdrant semantic) and sparse (PostgreSQL BM25/FTS)
retrieval, merging results using Reciprocal Rank Fusion (RRF).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Set

from app.config import settings
from app.db.postgres import pg_fulltext_search
from app.db.vector_store import semantic_search
from app.ingestion.embedder import embed_single

logger = logging.getLogger(__name__)

RRF_K = 60  # RRF constant — higher = smoother fusion


async def hybrid_retrieve(
    queries: List[str],
    top_k: int | None = None,
    score_threshold: float | None = None,
) -> List[Dict]:
    """
    Hybrid retrieval across multiple expanded queries.

    For each query:
      1. Dense search in Qdrant (cosine similarity of embeddings).
      2. Sparse search in PostgreSQL (BM25-like full-text ranking).
    Merge all results per query via RRF, then deduplicate across queries.

    Returns top_k unique chunks sorted by fused RRF score.
    """
    top_k = top_k or settings.max_retrieved_chunks
    score_threshold = score_threshold or settings.similarity_threshold

    all_dense_lists: List[List[Dict]] = []
    all_sparse_lists: List[List[Dict]] = []

    for query in queries:
        # Dense retrieval
        try:
            embedding = await embed_single(query)
            dense_hits = await semantic_search(
                query_vector=embedding,
                top_k=top_k,
                score_threshold=score_threshold,
            )
            all_dense_lists.append(dense_hits)
        except Exception as exc:
            logger.warning("Dense retrieval failed for query '%s': %s", query[:50], exc)
            all_dense_lists.append([])

        # Sparse retrieval
        try:
            sparse_hits = await pg_fulltext_search(query, top_k=top_k)
            # Normalize sparse hits to same format as dense hits
            normalized_sparse = [_normalize_pg_row(row) for row in sparse_hits]
            all_sparse_lists.append(normalized_sparse)
        except Exception as exc:
            logger.warning("Sparse retrieval failed for query '%s': %s", query[:50], exc)
            all_sparse_lists.append([])

    # Merge dense + sparse per query, then merge across queries
    per_query_merged: List[List[Dict]] = []
    for dense_list, sparse_list in zip(all_dense_lists, all_sparse_lists):
        merged = _reciprocal_rank_fusion([dense_list, sparse_list])
        per_query_merged.append(merged)

    # Final merge across all queries
    if per_query_merged:
        final_merged = _reciprocal_rank_fusion(per_query_merged)
    else:
        final_merged = []

    # Deduplicate by chunk_id, keep highest-scored
    final_unique = _deduplicate(final_merged)

    logger.info(
        "Hybrid retrieval: %d queries → %d unique chunks",
        len(queries),
        len(final_unique),
    )
    return final_unique[:top_k]


def _reciprocal_rank_fusion(ranked_lists: List[List[Dict]]) -> List[Dict]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.
    Score(d) = Σ 1 / (k + rank(d)) across all lists.
    """
    scores: Dict[str, Dict] = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list):
            chunk_id = item.get("chunk_id", "")
            if not chunk_id:
                continue
            if chunk_id not in scores:
                scores[chunk_id] = {"rrf_score": 0.0, "item": item}
            scores[chunk_id]["rrf_score"] += 1.0 / (RRF_K + rank + 1)

    sorted_items = sorted(
        scores.values(), key=lambda x: x["rrf_score"], reverse=True
    )
    result = []
    for entry in sorted_items:
        item = dict(entry["item"])
        item["rrf_score"] = entry["rrf_score"]
        result.append(item)
    return result


def _deduplicate(chunks: List[Dict]) -> List[Dict]:
    """Remove duplicate chunks, keeping the first (highest-scored) occurrence."""
    seen: Set[str] = set()
    unique = []
    for chunk in chunks:
        cid = chunk.get("chunk_id", "")
        if cid and cid not in seen:
            seen.add(cid)
            unique.append(chunk)
    return unique


def _normalize_pg_row(row: Dict) -> Dict:
    """Convert PostgreSQL FTS row to standard chunk dict format."""
    return {
        "chunk_id": row.get("chunk_id", ""),
        "text": row.get("chunk_text", ""),
        "similarity_score": float(row.get("rank", 0.0)),
        "metadata": {
            "chunk_id":    row.get("chunk_id", ""),
            "pmid":        row.get("pmid"),
            "pmc_id":      row.get("pmc_id"),
            "doi":         row.get("doi"),
            "title":       row.get("title", "Untitled"),
            "authors":     row.get("authors", []),
            "journal":     row.get("journal", ""),
            "pub_date":    row.get("pub_date", ""),
            "abstract":    row.get("abstract", ""),
            "source_type": row.get("source_type", "pubmed"),
            "url":         row.get("url"),
        },
    }
