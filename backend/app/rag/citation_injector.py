"""
Citation Injector — formats source metadata into structured SourceMetadata objects
for the API response, and validates citation integrity.
"""
from __future__ import annotations

import re
from typing import Dict, List, Set

from app.models.response import SourceMetadata
from app.utils.text_cleaner import truncate_text


def extract_cited_indices(answer: str) -> Set[int]:
    """
    Extract 1-based source indices referenced in the answer text.
    Matches patterns like [Source 1], [Source 2], [source 3].
    """
    matches = re.findall(r"\[Source\s*(\d+)\]", answer, re.IGNORECASE)
    return {int(m) for m in matches}


def build_source_metadata(
    chunks: List[Dict],
    answer: str,
) -> List[SourceMetadata]:
    """
    Convert chunk metadata dicts into SourceMetadata objects.
    Only includes sources that are actually cited in the answer.
    Sources are ordered by their appearance index in the answer.
    """
    cited_indices = extract_cited_indices(answer)
    sources: List[SourceMetadata] = []

    for i, chunk in enumerate(chunks):
        source_num = i + 1
        # Include if cited, or if answer has no citations (include all)
        if cited_indices and source_num not in cited_indices:
            continue

        meta = chunk.get("metadata", {})
        authors = meta.get("authors", [])

        # Build citation URL: prefer DOI, then PubMed, then URL
        doi = meta.get("doi")
        pmid = meta.get("pmid")
        url = meta.get("url")
        citation_url = (
            f"https://doi.org/{doi}" if doi
            else (f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid
            else url)
        )

        # Authors short form
        if len(authors) <= 3:
            authors_short = ", ".join(authors)
        elif authors:
            authors_short = f"{authors[0]} et al."
        else:
            authors_short = ""

        # Abstract snippet for citation card
        abstract_snippet = truncate_text(meta.get("abstract", ""), max_chars=250)

        sources.append(
            SourceMetadata(
                chunk_id=meta.get("chunk_id", f"source_{source_num}"),
                title=meta.get("title", "Untitled"),
                authors=authors,
                authors_short=authors_short,
                journal=meta.get("journal", ""),
                pub_date=meta.get("pub_date", ""),
                doi=doi,
                pmid=pmid,
                url=url,
                citation_url=citation_url,
                abstract_snippet=abstract_snippet,
                rerank_score=round(chunk.get("rerank_score", 0.0), 4),
            )
        )

    return sources


def format_answer_with_links(answer: str) -> str:
    """
    Transform [Source N] references into HTML anchor tags for frontend rendering.
    Frontend can further style these as clickable citation badges.
    """
    return re.sub(
        r"\[Source\s*(\d+)\]",
        r'<cite data-source="\1">[Source \1]</cite>',
        answer,
        flags=re.IGNORECASE,
    )
