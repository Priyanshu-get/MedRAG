"""
CrossRef REST API for DOI metadata enrichment.
Docs: https://api.crossref.org/
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)

CROSSREF_BASE = "https://api.crossref.org"
HEADERS = {"User-Agent": "MedRAG/1.0 (medrag@example.com)"}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
async def lookup_doi(doi: str) -> Optional[Dict]:
    """Fetch metadata for a specific DOI from CrossRef."""
    async with httpx.AsyncClient(timeout=20, headers=HEADERS) as client:
        resp = await client.get(f"{CROSSREF_BASE}/works/{doi}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json().get("message", {})
        return _normalize_crossref(data)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
async def search_crossref(query: str, max_results: int = 20) -> List[Dict]:
    """Search CrossRef for papers matching the query."""
    params = {
        "query": query,
        "rows":  min(max_results, 50),
        "filter": "type:journal-article",
        "select": "DOI,title,author,published,container-title,abstract",
    }
    async with httpx.AsyncClient(timeout=30, headers=HEADERS) as client:
        resp = await client.get(f"{CROSSREF_BASE}/works", params=params)
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        results = [_normalize_crossref(item) for item in items]
        return [r for r in results if r and r.get("abstract")]


def _normalize_crossref(item: Dict) -> Optional[Dict]:
    """Normalize CrossRef work dict to MedRAG document format."""
    doi = item.get("DOI", "")
    title_list = item.get("title", [])
    title = clean_text(title_list[0]) if title_list else "Untitled"

    authors = []
    for a in item.get("author", []):
        family = a.get("family", "")
        given = a.get("given", "")
        if family:
            authors.append(f"{family} {given}".strip())

    # Journal
    container = item.get("container-title", [])
    journal = container[0] if container else ""

    # Publication date
    pub_date_parts = item.get("published", {}).get("date-parts", [[]])
    if pub_date_parts and pub_date_parts[0]:
        parts = pub_date_parts[0]
        pub_date = "-".join(str(p) for p in parts[:2])
    else:
        pub_date = ""

    # Abstract (CrossRef often doesn't have full abstracts)
    abstract = clean_text(item.get("abstract", ""))

    return {
        "pmid":        None,
        "pmc_id":      None,
        "doi":         doi,
        "title":       title,
        "authors":     authors,
        "journal":     journal,
        "pub_date":    pub_date,
        "abstract":    abstract,
        "source_type": "crossref",
        "url": f"https://doi.org/{doi}" if doi else None,
    }
