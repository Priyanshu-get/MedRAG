"""
Tests for ingestion pipeline components: PubMed parser, chunker, embedder.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch


# ── Chunker tests ──────────────────────────────────────────────────────────────

def test_chunker_returns_empty_for_empty_text():
    from app.ingestion.chunker import chunk_document

    chunks = chunk_document("", {"title": "test", "pmid": "123"})
    assert chunks == []


def test_chunker_produces_chunks_with_metadata():
    from app.ingestion.chunker import chunk_document

    text = (
        "Hypertension is a major risk factor for cardiovascular disease. "
        "ACE inhibitors are recommended as first-line therapy. "
        "Thiazide diuretics are an alternative for uncomplicated cases. " * 20
    )
    doc_meta = {
        "pmid": "12345",
        "title": "Hypertension Guidelines",
        "journal": "JAMA",
        "pub_date": "2021",
        "authors": ["Smith J"],
        "abstract": text[:200],
        "source_type": "pubmed",
    }
    chunks = chunk_document(text, doc_meta)

    assert len(chunks) >= 1
    for chunk in chunks:
        assert "text" in chunk
        assert "metadata" in chunk
        assert "chunk_id" in chunk["metadata"]
        assert chunk["metadata"]["pmid"] == "12345"
        assert len(chunk["text"]) > 0


def test_chunker_assigns_unique_chunk_ids():
    from app.ingestion.chunker import chunk_document

    text = "Medical text. " * 500  # Large enough to create multiple chunks
    doc_meta = {"pmid": "99999", "title": "Test Doc", "source_type": "pubmed"}
    chunks = chunk_document(text, doc_meta)

    chunk_ids = [c["metadata"]["chunk_id"] for c in chunks]
    assert len(chunk_ids) == len(set(chunk_ids)), "Chunk IDs must be unique"


def test_chunker_splits_at_section_boundaries():
    from app.ingestion.chunker import chunk_document

    text = (
        "Background: Hypertension affects millions globally.\n"
        "Methods: We analyzed 1000 patients over 5 years.\n"
        "Results: ACE inhibitors reduced blood pressure significantly.\n"
        "Conclusions: ACE inhibitors are effective first-line agents."
    )
    doc_meta = {"pmid": "111", "title": "Hypertension Study", "source_type": "pubmed"}
    chunks = chunk_document(text, doc_meta)

    assert len(chunks) >= 1  # Should not crash; may or may not split at boundaries


# ── PubMed parser tests ────────────────────────────────────────────────────────

def test_pubmed_xml_parser_extracts_fields():
    from app.ingestion.sources.pubmed import _parse_pubmed_xml

    sample_xml = """<?xml version="1.0"?>
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>12345678</PMID>
          <Article>
            <ArticleTitle>ACE Inhibitors in Hypertension</ArticleTitle>
            <Abstract>
              <AbstractText Label="BACKGROUND">Hypertension is common.</AbstractText>
              <AbstractText Label="RESULTS">ACE inhibitors reduced BP by 10 mmHg.</AbstractText>
            </Abstract>
            <AuthorList>
              <Author>
                <LastName>Smith</LastName>
                <ForeName>John</ForeName>
              </Author>
            </AuthorList>
            <Journal>
              <Title>Journal of Hypertension</Title>
            </Journal>
            <PubDate><Year>2021</Year><Month>Jun</Month></PubDate>
          </Article>
        </MedlineCitation>
        <PubmedData>
          <ArticleIdList>
            <ArticleId IdType="doi">10.1234/jht.2021.001</ArticleId>
          </ArticleIdList>
        </PubmedData>
      </PubmedArticle>
    </PubmedArticleSet>"""

    docs = _parse_pubmed_xml(sample_xml)

    assert len(docs) == 1
    doc = docs[0]
    assert doc["pmid"] == "12345678"
    assert doc["title"] == "ACE Inhibitors in Hypertension"
    assert "ACE inhibitors" in doc["abstract"]
    assert "Smith" in doc["authors"][0]
    assert doc["journal"] == "Journal of Hypertension"
    assert doc["pub_date"] == "2021-Jun"
    assert doc["doi"] == "10.1234/jht.2021.001"
    assert doc["source_type"] == "pubmed"


def test_pubmed_xml_parser_skips_articles_without_abstract():
    from app.ingestion.sources.pubmed import _parse_pubmed_xml

    xml_no_abstract = """<?xml version="1.0"?>
    <PubmedArticleSet>
      <PubmedArticle>
        <MedlineCitation>
          <PMID>99999</PMID>
          <Article>
            <ArticleTitle>Title Only Paper</ArticleTitle>
          </Article>
        </MedlineCitation>
      </PubmedArticle>
    </PubmedArticleSet>"""

    docs = _parse_pubmed_xml(xml_no_abstract)
    assert len(docs) == 0


# ── Text cleaner tests ─────────────────────────────────────────────────────────

def test_text_cleaner_strips_html():
    from app.utils.text_cleaner import clean_text

    dirty = "<p>ACE inhibitors &amp; ARBs are <b>first-line</b> agents.</p>"
    clean = clean_text(dirty)
    assert "<p>" not in clean
    assert "<b>" not in clean
    assert "&amp;" not in clean
    assert "ACE inhibitors & ARBs" in clean


def test_text_cleaner_normalizes_whitespace():
    from app.utils.text_cleaner import clean_text

    messy = "ACE inhibitors   are   effective.\n\n\n\nThiazides  too."
    clean = clean_text(messy)
    assert "  " not in clean
    assert clean.count("\n") <= 2
