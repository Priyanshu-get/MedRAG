"""
PubMed / MEDLINE fetcher using NCBI E-utilities REST API.
Docs: https://www.ncbi.nlm.nih.gov/books/NBK25499/
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

_BASE_PARAMS = {
    "api_key": settings.ncbi_api_key,
    "email":   settings.ncbi_email,
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def search_pubmed(query: str, max_results: int = 50) -> List[str]:
    """
    Search PubMed and return a list of PMIDs.
    Rate limit: 10/sec with API key, 3/sec without.
    """
    params = {
        **_BASE_PARAMS,
        "db":         "pubmed",
        "term":       query,
        "retmax":     max_results,
        "retmode":    "json",
        "usehistory": "y",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{NCBI_BASE}/esearch.fcgi", params=params)
        resp.raise_for_status()
        data = resp.json()
        pmids = data.get("esearchresult", {}).get("idlist", [])
        logger.info("PubMed search '%s': found %d PMIDs", query[:60], len(pmids))
        return pmids


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_pubmed_abstracts(pmids: List[str]) -> List[Dict]:
    """
    Fetch structured abstract data for a list of PMIDs using efetch (XML).
    Returns list of dicts with: pmid, title, abstract, authors, journal, pub_date, doi.
    """
    if not pmids:
        return []

    params = {
        **_BASE_PARAMS,
        "db":      "pubmed",
        "id":      ",".join(pmids),
        "retmode": "xml",
        "rettype": "abstract",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(f"{NCBI_BASE}/efetch.fcgi", params=params)
        resp.raise_for_status()
        return _parse_pubmed_xml(resp.text)


def _parse_pubmed_xml(xml_text: str) -> List[Dict]:
    """Parse PubMed efetch XML into structured document dicts."""
    documents = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.error("Failed to parse PubMed XML: %s", exc)
        return []

    for article in root.findall(".//PubmedArticle"):
        try:
            doc = _extract_article(article)
            if doc and doc.get("abstract"):
                documents.append(doc)
        except Exception as exc:
            logger.warning("Failed to parse PubMed article: %s", exc)

    return documents


def _extract_article(article: ET.Element) -> Optional[Dict]:
    """Extract fields from a single PubmedArticle XML element."""
    medline = article.find("MedlineCitation")
    if medline is None:
        return None

    # PMID
    pmid_el = medline.find("PMID")
    pmid = pmid_el.text if pmid_el is not None else ""

    art = medline.find("Article")
    if art is None:
        return None

    # Title
    title_el = art.find("ArticleTitle")
    title = clean_text(ET.tostring(title_el, encoding="unicode", method="text")) if title_el is not None else "Untitled"

    # Abstract
    abstract_parts = art.findall(".//AbstractText")
    abstract_texts = []
    for part in abstract_parts:
        label = part.get("Label", "")
        text = clean_text(part.text or "")
        if label:
            abstract_texts.append(f"{label}: {text}")
        elif text:
            abstract_texts.append(text)
    abstract = " ".join(abstract_texts)

    if not abstract:
        return None  # Skip articles without abstract

    # Authors
    authors = []
    for author in art.findall(".//Author"):
        last = author.findtext("LastName", "")
        first = author.findtext("ForeName", "")
        if last:
            authors.append(f"{last} {first}".strip())

    # Journal
    journal_el = art.find(".//Journal/Title")
    journal = journal_el.text if journal_el is not None else ""

    # Publication date
    pub_date = _extract_pub_date(art)

    # DOI
    doi = None
    for id_el in article.findall(".//ArticleId"):
        if id_el.get("IdType") == "doi":
            doi = id_el.text
            break

    return {
        "pmid":     pmid,
        "pmc_id":   None,
        "doi":      doi,
        "title":    title,
        "authors":  authors,
        "journal":  journal,
        "pub_date": pub_date,
        "abstract": abstract,
        "source_type": "pubmed",
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
    }


def _extract_pub_date(article_el: ET.Element) -> str:
    """Extract publication date in YYYY-MM or YYYY format."""
    pub_date = article_el.find(".//PubDate")
    if pub_date is None:
        return ""
    year = pub_date.findtext("Year", "")
    month = pub_date.findtext("Month", "")
    if year and month:
        return f"{year}-{month}"
    return year
