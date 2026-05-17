"""
Semantic Scholar API fetcher.
Docs: https://api.semanticscholar.org/api-docs/
Free tier: 100 req/5min without key, 1 req/sec with key.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)

SS_BASE = "https://api.semanticscholar.org/graph/v1"

FIELDS = "paperId,externalIds,title,abstract,authors,year,venue,publicationDate,openAccessPdf"


def _get_headers() -> Dict[str, str]:
    headers = {"User-Agent": "MedRAG/1.0"}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key
    return headers


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=20))
async def search_semantic_scholar(query: str, max_results: int = 30) -> List[Dict]:
    """
    Search Semantic Scholar for medical papers.
    Returns list of paper dicts with title, abstract, authors, etc.
    """
    params = {
        "query":  query,
        "limit":  min(max_results, 100),
        "fields": FIELDS,
    }
    async with httpx.AsyncClient(timeout=30, headers=_get_headers()) as client:
        resp = await client.get(f"{SS_BASE}/paper/search", params=params)
        resp.raise_for_status()
        data = resp.json()
        papers = data.get("data", [])
        logger.info("Semantic Scholar '%s': found %d papers", query[:60], len(papers))
        return [_normalize_paper(p) for p in papers if p.get("abstract")]


def _normalize_paper(paper: Dict) -> Dict:
    """Normalize Semantic Scholar paper dict to MedRAG document format."""
    ext_ids = paper.get("externalIds") or {}
    pmid    = ext_ids.get("PubMed")
    doi     = ext_ids.get("DOI")
    pmc_id  = ext_ids.get("PubMedCentral")

    authors = [
        a.get("name", "") for a in (paper.get("authors") or [])
    ]

    pub_date = paper.get("publicationDate") or str(paper.get("year", ""))

    url: Optional[str] = None
    open_access = paper.get("openAccessPdf")
    if isinstance(open_access, dict):
        url = open_access.get("url")
    if not url and doi:
        url = f"https://doi.org/{doi}"

    return {
        "pmid":        pmid,
        "pmc_id":      pmc_id,
        "doi":         doi,
        "title":       clean_text(paper.get("title", "Untitled")),
        "authors":     authors,
        "journal":     paper.get("venue", ""),
        "pub_date":    pub_date,
        "abstract":    clean_text(paper.get("abstract", "")),
        "source_type": "semantic_scholar",
        "url":         url,
    }
