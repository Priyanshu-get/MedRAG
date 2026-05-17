"""
ClinicalTrials.gov REST API v2 fetcher.
API docs: https://clinicaltrials.gov/data-api/api
"""
from __future__ import annotations

import logging
from typing import Dict, List

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.text_cleaner import clean_text

logger = logging.getLogger(__name__)

CT_BASE = "https://clinicaltrials.gov/api/v2/studies"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
async def search_clinical_trials(query: str, max_results: int = 30) -> List[Dict]:
    """
    Search ClinicalTrials.gov for relevant studies.
    Returns list of normalized trial dicts.
    """
    params = {
        "query.term":  query,
        "pageSize":    min(max_results, 100),
        "format":      "json",
        "fields": (
            "NCTId,BriefTitle,OfficialTitle,BriefSummary,DetailedDescription,"
            "Condition,InterventionName,Phase,OverallStatus,"
            "StartDate,CompletionDate,StudyType,Keyword"
        ),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(CT_BASE, params=params)
        resp.raise_for_status()
        data = resp.json()
        studies = data.get("studies", [])
        logger.info("ClinicalTrials '%s': found %d studies", query[:60], len(studies))
        return [_normalize_study(s) for s in studies if _has_description(s)]


def _has_description(study: Dict) -> bool:
    proto = study.get("protocolSection", {})
    desc = proto.get("descriptionModule", {})
    return bool(
        desc.get("briefSummary") or desc.get("detailedDescription")
    )


def _normalize_study(study: Dict) -> Dict:
    """Normalize ClinicalTrials study dict to MedRAG document format."""
    proto = study.get("protocolSection", {})

    ident = proto.get("identificationModule", {})
    nct_id = ident.get("nctId", "")
    title = clean_text(
        ident.get("officialTitle") or ident.get("briefTitle", "Untitled")
    )

    desc = proto.get("descriptionModule", {})
    brief = clean_text(desc.get("briefSummary", ""))
    detailed = clean_text(desc.get("detailedDescription", ""))
    abstract = brief or detailed

    status_mod = proto.get("statusModule", {})
    start_date = status_mod.get("startDateStruct", {}).get("date", "")
    pub_date = start_date[:4] if start_date else ""

    cond_mod = proto.get("conditionsModule", {})
    conditions = cond_mod.get("conditions", [])

    interv_mod = proto.get("armsInterventionsModule", {})
    interventions = [
        i.get("interventionName", "")
        for i in interv_mod.get("interventions", [])
    ]

    # Build rich abstract from available fields
    rich_abstract_parts = [abstract]
    if conditions:
        rich_abstract_parts.append(f"Conditions: {', '.join(conditions[:5])}")
    if interventions:
        rich_abstract_parts.append(f"Interventions: {', '.join(interventions[:5])}")
    phase = proto.get("designModule", {}).get("phases", [])
    if phase:
        rich_abstract_parts.append(f"Phase: {', '.join(phase)}")

    return {
        "pmid":        None,
        "pmc_id":      None,
        "doi":         None,
        "title":       title,
        "authors":     [],
        "journal":     "ClinicalTrials.gov",
        "pub_date":    pub_date,
        "abstract":    "\n".join(rich_abstract_parts),
        "source_type": "clinical_trials",
        "url": f"https://clinicaltrials.gov/study/{nct_id}" if nct_id else None,
        "nct_id":      nct_id,
    }
