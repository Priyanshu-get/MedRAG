"""
Qdrant vector store client.
Handles collection initialization and semantic search.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    ScoredPoint,
    Filter,
)

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[AsyncQdrantClient] = None


def get_qdrant_client() -> AsyncQdrantClient:
    global _client
    if _client is None:
        _client = AsyncQdrantClient(url=settings.qdrant_url, timeout=30)
    return _client


async def init_qdrant_collection() -> None:
    """Create the Qdrant collection if it doesn't exist."""
    client = get_qdrant_client()
    collections = await client.get_collections()
    existing = [c.name for c in collections.collections]

    if settings.qdrant_collection not in existing:
        await client.create_collection(
            collection_name=settings.qdrant_collection,
            vectors_config=VectorParams(
                size=settings.qdrant_vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info(
            "Created Qdrant collection '%s' with %d-dim vectors",
            settings.qdrant_collection,
            settings.qdrant_vector_size,
        )
    else:
        logger.info("Qdrant collection '%s' already exists", settings.qdrant_collection)


async def semantic_search(
    query_vector: List[float],
    top_k: int = 20,
    score_threshold: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Dense semantic search in Qdrant.
    Returns list of dicts with chunk_id, text, metadata, and similarity score.
    """
    client = get_qdrant_client()
    results: List[ScoredPoint] = await client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
        with_payload=True,
    )

    hits = []
    for point in results:
        payload = point.payload or {}
        hits.append(
            {
                "chunk_id": payload.get("chunk_id", str(point.id)),
                "text": payload.get("chunk_text", payload.get("text", "")),
                "metadata": {
                    "chunk_id":    payload.get("chunk_id", str(point.id)),
                    "pmid":        payload.get("pmid"),
                    "pmc_id":      payload.get("pmc_id"),
                    "doi":         payload.get("doi"),
                    "title":       payload.get("title", "Untitled"),
                    "authors":     payload.get("authors", []),
                    "journal":     payload.get("journal", ""),
                    "pub_date":    payload.get("pub_date", ""),
                    "abstract":    payload.get("abstract", ""),
                    "source_type": payload.get("source_type", "pubmed"),
                    "url":         payload.get("url"),
                },
                "similarity_score": point.score,
            }
        )
    return hits


async def upsert_vectors(points: List[Dict[str, Any]]) -> int:
    """
    Upsert a batch of embedded chunks into Qdrant.
    Each point: {chunk_id, embedding, text, metadata dict}
    Returns number of points upserted.
    """
    client = get_qdrant_client()

    qdrant_points = []
    for p in points:
        # Use a deterministic integer ID derived from chunk_id hash
        point_id = abs(hash(p["chunk_id"])) % (2**63)
        payload = {
            "chunk_id":    p["chunk_id"],
            "chunk_text":  p["text"],
            **p.get("metadata", {}),
        }
        qdrant_points.append(
            PointStruct(id=point_id, vector=p["embedding"], payload=payload)
        )

    if qdrant_points:
        await client.upsert(
            collection_name=settings.qdrant_collection,
            points=qdrant_points,
        )

    return len(qdrant_points)


async def count_vectors() -> int:
    """Return total number of vectors in the collection."""
    try:
        client = get_qdrant_client()
        info = await client.get_collection(settings.qdrant_collection)
        return info.points_count or 0
    except Exception:
        return 0


async def check_qdrant_health() -> bool:
    """Return True if Qdrant is reachable."""
    try:
        client = get_qdrant_client()
        await client.get_collections()
        return True
    except Exception as exc:
        logger.error("Qdrant health check failed: %s", exc)
        return False
