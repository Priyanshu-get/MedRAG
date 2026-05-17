"""
Celery tasks for asynchronous and scheduled document ingestion.
Run worker: celery -A app.ingestion.tasks worker --loglevel=info
Run scheduler: celery -A app.ingestion.tasks beat --loglevel=info
"""
from __future__ import annotations

import asyncio
import logging
from typing import List

from celery import Celery
from celery.schedules import crontab

from app.config import settings

logger = logging.getLogger(__name__)

# ── Celery app ────────────────────────────────────────────────────────────────
celery_app = Celery(
    "medrag",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    timezone="UTC",
    enable_utc=True,
)

# ── Scheduled tasks ───────────────────────────────────────────────────────────
celery_app.conf.beat_schedule = {
    "weekly-pubmed-update": {
        "task": "app.ingestion.tasks.weekly_pubmed_update",
        "schedule": crontab(hour=2, minute=0, day_of_week="sunday"),
    },
}

# Medical topics for weekly updates
WEEKLY_TOPICS: List[str] = [
    "myocardial infarction treatment",
    "hypertension management guidelines",
    "type 2 diabetes mellitus",
    "oncology immunotherapy",
    "stroke thrombolysis",
    "antibiotic resistance",
    "COVID-19 long term effects",
    "Alzheimer disease treatment",
    "heart failure management",
    "sepsis treatment protocol",
    "chronic kidney disease progression",
    "atrial fibrillation ablation",
    "breast cancer clinical trial",
    "lung cancer immunotherapy",
    "depression SSRi treatment",
    "rheumatoid arthritis biologics",
]


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def weekly_pubmed_update(self):
    """
    Weekly Celery task: ingest latest PubMed articles for key medical topics.
    Runs Sunday at 02:00 UTC.
    """
    logger.info("🔄 Starting weekly PubMed update for %d topics", len(WEEKLY_TOPICS))

    total_chunks = 0
    for topic in WEEKLY_TOPICS:
        try:
            chunks = asyncio.run(_ingest_topic_pubmed(topic, max_results=100))
            total_chunks += chunks
            logger.info("Ingested %d chunks for topic: %s", chunks, topic)
        except Exception as exc:
            logger.error("Failed to ingest topic '%s': %s", topic, exc)

    logger.info("✅ Weekly update complete: %d total chunks indexed", total_chunks)
    return {"chunks_indexed": total_chunks}


@celery_app.task
def ingest_topic_async(topic: str, max_results: int = 50, sources: List[str] = None):
    """
    On-demand Celery task: ingest a specific topic.
    Triggered by POST /api/v1/ingest.
    """
    if sources is None:
        sources = ["pubmed"]

    logger.info("📥 Async ingestion: topic='%s', sources=%s", topic, sources)
    chunks = asyncio.run(_ingest_topic_all_sources(topic, max_results, sources))
    return {"topic": topic, "chunks_indexed": chunks}


# ── Async helpers ─────────────────────────────────────────────────────────────

async def _ingest_topic_pubmed(topic: str, max_results: int = 50) -> int:
    from app.ingestion.sources.pubmed import search_pubmed, fetch_pubmed_abstracts
    from app.ingestion.chunker import chunk_document
    from app.ingestion.indexer import index_chunks

    pmids = await search_pubmed(topic, max_results)
    if not pmids:
        return 0

    abstracts = await fetch_pubmed_abstracts(pmids)
    all_chunks = []
    for doc in abstracts:
        text = doc.get("abstract", "")
        if text:
            chunks = chunk_document(text, doc)
            all_chunks.extend(chunks)

    return await index_chunks(all_chunks)


async def _ingest_topic_all_sources(
    topic: str,
    max_results: int,
    sources: List[str],
) -> int:
    from app.ingestion.chunker import chunk_document
    from app.ingestion.indexer import index_chunks

    all_docs = []

    if "pubmed" in sources:
        from app.ingestion.sources.pubmed import search_pubmed, fetch_pubmed_abstracts
        pmids = await search_pubmed(topic, max_results)
        all_docs.extend(await fetch_pubmed_abstracts(pmids))

    if "pmc" in sources:
        from app.ingestion.sources.pmc import search_pmc, fetch_pmc_fulltext
        pmc_ids = await search_pmc(topic, min(max_results, 20))
        for pmc_id in pmc_ids[:10]:  # Full-text is expensive; limit
            doc = await fetch_pmc_fulltext(pmc_id)
            if doc:
                all_docs.append(doc)

    if "semantic_scholar" in sources:
        from app.ingestion.sources.semantic_scholar import search_semantic_scholar
        all_docs.extend(await search_semantic_scholar(topic, max_results))

    if "clinical_trials" in sources:
        from app.ingestion.sources.clinical_trials import search_clinical_trials
        all_docs.extend(await search_clinical_trials(topic, max_results))

    all_chunks = []
    for doc in all_docs:
        text = doc.get("full_text") or doc.get("abstract", "")
        if text:
            chunks = chunk_document(text, doc)
            all_chunks.extend(chunks)

    return await index_chunks(all_chunks)
