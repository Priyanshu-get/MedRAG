"""
PostgreSQL async engine using SQLAlchemy.
Provides session factory and raw async connection for full-text search.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator, List, Dict, Any, Optional

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import text

from app.config import settings

logger = logging.getLogger(__name__)

# ── Engine singleton ──────────────────────────────────────────────────────────
_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker] = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.app_env == "development",
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Full-text search ──────────────────────────────────────────────────────────

async def pg_fulltext_search(
    query: str,
    top_k: int = 20,
) -> List[Dict[str, Any]]:
    """
    BM25-like full-text search using PostgreSQL tsvector.
    Returns chunks ranked by ts_rank_cd.
    """
    async with get_session_factory()() as session:
        sql = text(
            """
            SELECT
                chunk_id,
                title,
                authors,
                journal,
                pub_date,
                doi,
                pmid,
                pmc_id,
                url,
                abstract,
                chunk_text,
                source_type,
                ts_rank_cd(search_vector, query) AS rank
            FROM documents, plainto_tsquery('english', :query) query
            WHERE search_vector @@ query
            ORDER BY rank DESC
            LIMIT :top_k
            """
        )
        result = await session.execute(sql, {"query": query, "top_k": top_k})
        rows = result.mappings().all()
        return [dict(row) for row in rows]


async def upsert_document_metadata(doc: Dict[str, Any]) -> None:
    """Insert or update document metadata in PostgreSQL."""
    async with get_session_factory()() as session:
        sql = text(
            """
            INSERT INTO documents (
                chunk_id, pmid, pmc_id, doi, title, authors,
                journal, pub_date, abstract, chunk_text, source_type, url
            ) VALUES (
                :chunk_id, :pmid, :pmc_id, :doi, :title, :authors,
                :journal, :pub_date, :abstract, :chunk_text, :source_type, :url
            )
            ON CONFLICT (chunk_id) DO UPDATE SET
                title       = EXCLUDED.title,
                chunk_text  = EXCLUDED.chunk_text,
                abstract    = EXCLUDED.abstract,
                indexed_at  = NOW()
            """
        )
        await session.execute(sql, doc)
        await session.commit()


async def count_indexed_documents() -> int:
    """Return total number of indexed document chunks."""
    async with get_session_factory()() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM documents"))
        return result.scalar() or 0


async def check_postgres_health() -> bool:
    """Return True if PostgreSQL is reachable."""
    try:
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("PostgreSQL health check failed: %s", exc)
        return False
