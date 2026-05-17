"""
/api/v1/ingest — On-demand document ingestion endpoint.
Triggers ingestion of medical literature for a given topic.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.query import IngestRequest
from app.models.response import IngestResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Trigger document ingestion for a medical topic",
    description=(
        "Fetches articles from configured sources (PubMed, PMC, Semantic Scholar, "
        "ClinicalTrials.gov), chunks them, generates embeddings, and indexes them "
        "in Qdrant + PostgreSQL.\n\n"
        "This endpoint runs synchronously for small max_results (≤50) and "
        "as a background task for larger batches."
    ),
)
async def ingest(
    request: IngestRequest,
    background_tasks: BackgroundTasks,
) -> IngestResponse:
    """Ingest medical literature for a topic into the vector store."""
    logger.info(
        "Ingest request: topic='%s', max=%d, sources=%s",
        request.topic[:80], request.max_results, request.sources,
    )

    # Validate sources
    valid_sources = {"pubmed", "pmc", "semantic_scholar", "clinical_trials"}
    invalid = set(request.sources) - valid_sources
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sources: {invalid}. Valid options: {valid_sources}",
        )

    try:
        if request.max_results <= 50:
            # Run synchronously for small batches (fast feedback)
            chunks_indexed = await _run_ingestion(
                request.topic, request.max_results, request.sources
            )
            return IngestResponse(
                topic=request.topic,
                chunks_indexed=chunks_indexed,
                status="completed",
                message=f"Successfully indexed {chunks_indexed} chunks from {request.sources}.",
            )
        else:
            # Dispatch to background for large batches
            background_tasks.add_task(
                _run_ingestion_bg, request.topic, request.max_results, request.sources
            )
            return IngestResponse(
                topic=request.topic,
                status="processing",
                message=(
                    f"Large ingestion job started in background for {request.max_results} articles. "
                    "Check /api/v1/health for indexed document count."
                ),
            )

    except Exception as exc:
        logger.error("Ingestion failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(exc)}")


async def _run_ingestion(topic: str, max_results: int, sources: list) -> int:
    """Run ingestion pipeline and return number of chunks indexed."""
    from app.ingestion.chunker import chunk_document
    from app.ingestion.indexer import index_chunks

    all_docs = []

    if "pubmed" in sources:
        from app.ingestion.sources.pubmed import fetch_pubmed_abstracts, search_pubmed
        pmids = await search_pubmed(topic, max_results)
        all_docs.extend(await fetch_pubmed_abstracts(pmids))

    if "pmc" in sources:
        from app.ingestion.sources.pmc import fetch_pmc_fulltext, search_pmc
        pmc_ids = await search_pmc(topic, min(max_results, 15))
        for pmc_id in pmc_ids[:10]:
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


def _run_ingestion_bg(topic: str, max_results: int, sources: list) -> None:
    """Synchronous wrapper for background task execution."""
    try:
        chunks = asyncio.run(_run_ingestion(topic, max_results, sources))
        logger.info("Background ingestion complete: %d chunks for '%s'", chunks, topic)
    except Exception as exc:
        logger.error("Background ingestion failed: %s", exc)
