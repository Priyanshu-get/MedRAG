"""
Indexer: embeds chunks and stores them in Qdrant + PostgreSQL.
"""
from __future__ import annotations

import logging
from typing import Dict, List

from app.db.postgres import upsert_document_metadata
from app.db.vector_store import upsert_vectors
from app.ingestion.embedder import embed_texts

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 50  # embed N chunks at a time


async def index_chunks(chunks: List[Dict]) -> int:
    """
    Pipeline: chunks → embed → upsert to Qdrant + PostgreSQL.
    Returns number of chunks successfully indexed.
    """
    if not chunks:
        return 0

    total_indexed = 0

    # Process in batches to avoid memory issues
    for batch_start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[batch_start : batch_start + EMBED_BATCH_SIZE]
        texts = [c["text"] for c in batch]

        # 1. Generate embeddings
        try:
            embeddings = await embed_texts(texts)
        except Exception as exc:
            logger.error("Embedding failed for batch at %d: %s", batch_start, exc)
            continue

        # 2. Prepare Qdrant points
        qdrant_points = []
        for chunk, embedding in zip(batch, embeddings):
            meta = chunk["metadata"]
            qdrant_points.append(
                {
                    "chunk_id": meta["chunk_id"],
                    "embedding": embedding,
                    "text": chunk["text"],
                    "metadata": meta,
                }
            )

        # 3. Upsert to Qdrant (vector search)
        try:
            upserted = await upsert_vectors(qdrant_points)
            logger.debug("Upserted %d vectors to Qdrant", upserted)
        except Exception as exc:
            logger.error("Qdrant upsert failed: %s", exc)

        # 4. Upsert to PostgreSQL (metadata + full-text search)
        for chunk in batch:
            meta = chunk["metadata"]
            pg_doc = {
                "chunk_id":    meta["chunk_id"],
                "pmid":        meta.get("pmid"),
                "pmc_id":      meta.get("pmc_id"),
                "doi":         meta.get("doi"),
                "title":       meta.get("title", ""),
                "authors":     meta.get("authors", []),
                "journal":     meta.get("journal", ""),
                "pub_date":    meta.get("pub_date", ""),
                "abstract":    meta.get("abstract", ""),
                "chunk_text":  chunk["text"],
                "source_type": meta.get("source_type", "pubmed"),
                "url":         meta.get("url"),
            }
            try:
                await upsert_document_metadata(pg_doc)
            except Exception as exc:
                logger.warning("PostgreSQL upsert failed for %s: %s", meta["chunk_id"], exc)

        total_indexed += len(batch)

    logger.info("Indexing complete: %d/%d chunks indexed", total_indexed, len(chunks))
    return total_indexed
