"""
Pytest configuration and shared fixtures for MedRAG tests.
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def sample_query() -> str:
    return "What is the first-line treatment for hypertension?"


@pytest.fixture
def relevant_context() -> str:
    return (
        "ACE inhibitors and thiazide diuretics are recommended as first-line "
        "antihypertensive agents according to JNC 8 guidelines published in JAMA 2014. "
        "For most patients with hypertension, the goal blood pressure is less than 140/90 mmHg. "
        "Lifestyle modifications including sodium restriction and weight loss are adjunct therapies. "
        "Angiotensin receptor blockers (ARBs) are an alternative for patients intolerant of ACE inhibitors."
    )


@pytest.fixture
def irrelevant_context() -> str:
    return (
        "Photosynthesis is the process by which plants convert light energy into chemical energy. "
        "Chlorophyll absorbs red and blue wavelengths of light. "
        "The Calvin cycle produces glucose from carbon dioxide. "
        "This process occurs in the chloroplasts of plant cells."
    )


@pytest.fixture
def sample_chunks() -> list:
    return [
        {
            "chunk_id": "pubmed_12345_0",
            "text": (
                "ACE inhibitors are recommended as first-line therapy for hypertension "
                "in patients with diabetes mellitus and chronic kidney disease."
            ),
            "similarity_score": 0.91,
            "rerank_score": 2.3,
            "source_index": 1,
            "metadata": {
                "chunk_id":    "pubmed_12345_0",
                "pmid":        "12345678",
                "doi":         "10.1001/jama.2014.4711",
                "title":       "2014 Evidence-Based Guideline for the Management of High Blood Pressure in Adults",
                "authors":     ["James PA", "Oparil S", "Carter BL"],
                "journal":     "JAMA",
                "pub_date":    "2014-02",
                "abstract":    "Guidelines for hypertension management based on systematic evidence review.",
                "source_type": "pubmed",
                "url":         "https://pubmed.ncbi.nlm.nih.gov/12345678/",
            },
        },
        {
            "chunk_id": "pubmed_67890_0",
            "text": (
                "Thiazide diuretics remain effective first-line agents for uncomplicated "
                "hypertension, particularly in elderly patients and those of African descent."
            ),
            "similarity_score": 0.85,
            "rerank_score": 1.9,
            "source_index": 2,
            "metadata": {
                "chunk_id":    "pubmed_67890_0",
                "pmid":        "67890123",
                "doi":         None,
                "title":       "Thiazide Diuretics in Hypertension Management",
                "authors":     ["Smith AB"],
                "journal":     "New England Journal of Medicine",
                "pub_date":    "2021",
                "abstract":    "Review of thiazide diuretic efficacy in blood pressure control.",
                "source_type": "pubmed",
                "url":         "https://pubmed.ncbi.nlm.nih.gov/67890123/",
            },
        },
    ]
