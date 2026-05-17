"""
PubMed Central (PMC) Open Access full-text fetcher.
Only open-access articles have full-text available.
API docs: https://www.ncbi.nlm.nih.gov/pmc/tools/oa-service/
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

PMC_OA_BASE = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

_BASE_PARAMS = {
    "api_key": settings.ncbi_api_key,
    "email":   settings.ncbi_email,
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
async def search_pmc(query: str, max_results: int = 30) -> List[str]:
    """Search PMC and return list of PMCIDs."""
    params = {
        **_BASE_PARAMS,
        "db":      "pmc",
        "term":    f"{query} AND open access[filter]",
        "retmax":  max_results,
        "retmode": "json",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(f"{NCBI_BASE}/esearch.fcgi", params=params)
        resp.raise_for_status()
        data = resp.json()
        pmc_ids = data.get("esearchresult", {}).get("idlist", [])
        logger.info("PMC search '%s': found %d articles", query[:60], len(pmc_ids))
        return pmc_ids


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
async def fetch_pmc_fulltext(pmc_id: str) -> Optional[Dict]:
    """
    Fetch full-text XML of a PMC open-access article.
    Returns structured dict with title, abstract, body sections.
    """
    # Normalize ID format
    if not pmc_id.startswith("PMC"):
        pmc_id = f"PMC{pmc_id}"

    params = {
        "verb":            "GetRecord",
        "identifier":      f"oai:pubmedcentral.nih.gov:{pmc_id.replace('PMC', '')}",
        "metadataPrefix":  "pmc",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.get(PMC_OA_BASE, params=params)
        resp.raise_for_status()
        return _parse_pmc_xml(resp.text, pmc_id)


def _parse_pmc_xml(xml_text: str, pmc_id: str) -> Optional[Dict]:
    """Parse PMC OAI-PMH XML to extract article text."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None

    # Extract all text nodes from body
    ns = {"pmc": "https://dtd.nlm.nih.gov/ns/archiving/2.3/"}

    title = ""
    title_el = root.find(".//article-title")
    if title_el is not None:
        title = clean_text(ET.tostring(title_el, encoding="unicode", method="text"))

    # Abstract
    abstract_parts = []
    for abstract_el in root.findall(".//abstract"):
        text = clean_text(ET.tostring(abstract_el, encoding="unicode", method="text"))
        if text:
            abstract_parts.append(text)
    abstract = " ".join(abstract_parts)

    # Body sections (for full-text indexing)
    body_sections = []
    for sec in root.findall(".//sec"):
        sec_title_el = sec.find("title")
        sec_title = sec_title_el.text if sec_title_el is not None else ""
        paragraphs = sec.findall(".//p")
        sec_text = " ".join(
            clean_text(ET.tostring(p, encoding="unicode", method="text"))
            for p in paragraphs
        )
        if sec_text:
            body_sections.append(f"{sec_title}: {sec_text}" if sec_title else sec_text)

    full_text = abstract + "\n\n" + "\n\n".join(body_sections)

    if not abstract and not body_sections:
        return None

    # Journal
    journal_el = root.find(".//journal-title")
    journal = journal_el.text if journal_el is not None else ""

    # Authors
    authors = []
    for contrib in root.findall(".//contrib[@contrib-type='author']"):
        surname = contrib.findtext(".//surname", "")
        given = contrib.findtext(".//given-names", "")
        if surname:
            authors.append(f"{surname} {given}".strip())

    # DOI
    doi = None
    for article_id in root.findall(".//article-id"):
        if article_id.get("pub-id-type") == "doi":
            doi = article_id.text
            break

    # Pub date
    pub_year = root.findtext(".//pub-date/year", "")
    pub_month = root.findtext(".//pub-date/month", "")
    pub_date = f"{pub_year}-{pub_month}" if pub_month else pub_year

    return {
        "pmid":        None,
        "pmc_id":      pmc_id,
        "doi":         doi,
        "title":       title or "Untitled",
        "authors":     authors,
        "journal":     journal,
        "pub_date":    pub_date,
        "abstract":    abstract,
        "full_text":   full_text,
        "source_type": "pmc",
        "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/",
    }
