"""
Trip Medical Database fetcher.
Docs: https://www.tripdatabase.com/
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.text_cleaner import clean_text
from app.ingestion.sources.pubmed import fetch_pubmed_abstracts
from app.ingestion.sources.crossref import lookup_doi

logger = logging.getLogger(__name__)

TRIP_SEARCH_URL = "https://www.tripdatabase.com/api/search"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def search_trip(query: str, max_results: int = 20) -> List[Dict]:
    """
    Search Trip Database for clinical evidence.
    Resolves abstracts using PubMed/Crossref if PMID/DOI is found.
    """
    params = {
        "criteria": query,
        "search_type": "standard",
        "skip": 0,
        "response_type": "json",
    }
    
    logger.info("Searching Trip Database for '%s'", query)
    
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(TRIP_SEARCH_URL, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        # Trip API returns: {"documents": {"document": [...]}}
        doc_wrapper = data.get("documents", {}) or {}
        documents = doc_wrapper.get("document", [])
        if not isinstance(documents, list):
            if isinstance(documents, dict):
                documents = [documents]
            else:
                documents = []
                
        logger.info("Trip Database '%s': found %d results", query[:60], len(documents))
        
        results = []
        for doc in documents:
            if len(results) >= max_results:
                break
            normalized = await _normalize_trip_document(doc)
            if normalized and normalized.get("abstract"):
                results.append(normalized)
                
        return results


async def _normalize_trip_document(doc: Dict) -> Optional[Dict]:
    """
    Normalize Trip Database document structure.
    Tries to enrich document with full abstract from PubMed or CrossRef.
    """
    title = clean_text(doc.get("title", "Untitled"))
    link = doc.get("link") or ""
    doi = doc.get("doi")
    
    # Try parsing PMID from the link
    pmid = None
    pmid_match = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", link)
    if pmid_match:
        pmid = pmid_match.group(1)
        
    # 1. Try resolving via PubMed (Best for medical abstracts)
    if pmid:
        try:
            logger.debug("Resolving Trip document PMID %s via PubMed", pmid)
            pubmed_docs = await fetch_pubmed_abstracts([pmid])
            if pubmed_docs:
                pubmed_doc = pubmed_docs[0]
                pubmed_doc["source_type"] = "trip"
                if link:
                    pubmed_doc["url"] = link
                return pubmed_doc
        except Exception as exc:
            logger.warning("Failed to resolve Trip PMID %s via PubMed: %s", pmid, exc)

    # 2. Try resolving via CrossRef (Fallback for non-PubMed DOIs)
    if doi:
        try:
            logger.debug("Resolving Trip document DOI %s via CrossRef", doi)
            crossref_doc = await lookup_doi(doi)
            if crossref_doc:
                crossref_doc["source_type"] = "trip"
                crossref_doc["pmid"] = pmid
                if link:
                    crossref_doc["url"] = link
                return crossref_doc
        except Exception as exc:
            logger.warning("Failed to resolve Trip DOI %s via CrossRef: %s", doi, exc)

    # 3. Fallback: skip if no abstract can be resolved (to maintain database context quality)
    return None
