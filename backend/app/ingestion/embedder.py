"""
Embedding generation — supports OpenAI and local BAAI/bge models.
Automatically selects provider based on EMBEDDING_PROVIDER config.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ── Provider selection ────────────────────────────────────────────────────────

_openai_client = None
_local_model = None


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        from openai import AsyncOpenAI
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_local_model():
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading local embedding model: %s", settings.local_embedding_model)
        _local_model = SentenceTransformer(
            settings.local_embedding_model,
            device="cpu",
        )
        logger.info("Local embedding model loaded")
    return _local_model


# ── Public API ────────────────────────────────────────────────────────────────

async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.
    Dispatches to OpenAI or local BAAI/bge based on EMBEDDING_PROVIDER setting.
    """
    if not texts:
        return []

    if settings.embedding_provider == "openai":
        return await _embed_openai(texts)
    else:
        return _embed_local(texts)


async def embed_single(text: str) -> List[float]:
    """Convenience wrapper to embed a single text."""
    results = await embed_texts([text])
    return results[0] if results else []


async def _embed_openai(texts: List[str]) -> List[List[float]]:
    """OpenAI text-embedding-3-large embeddings (3072 dims)."""
    client = _get_openai_client()

    # OpenAI accepts up to 2048 texts per call; batch if needed
    BATCH_SIZE = 100
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        # Truncate very long texts to avoid token limit errors
        batch = [t[:8000] for t in batch]
        try:
            response = await client.embeddings.create(
                model=settings.openai_embedding_model,
                input=batch,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)
        except Exception as exc:
            logger.error("OpenAI embedding failed for batch %d: %s", i, exc)
            # Return zero vectors on failure to avoid pipeline crash
            all_embeddings.extend([[0.0] * 3072] * len(batch))

    return all_embeddings


def _embed_local(texts: List[str]) -> List[List[float]]:
    """BAAI/bge-large-en-v1.5 embeddings (1024 dims) — runs locally."""
    model = _get_local_model()
    try:
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return embeddings.tolist()
    except Exception as exc:
        logger.error("Local embedding failed: %s", exc)
        dim = 1024
        return [[0.0] * dim] * len(texts)
