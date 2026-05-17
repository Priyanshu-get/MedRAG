"""
Semantic chunker for medical documents.
Splits text into overlapping chunks while preserving sentence boundaries.
"""
from __future__ import annotations

import logging
import re
from typing import Dict, List

import tiktoken

from app.config import settings

logger = logging.getLogger(__name__)

_TOKENIZER = tiktoken.get_encoding("cl100k_base")  # Compatible with GPT-4 / Claude

CHUNK_SIZE_TOKENS = 400      # ~512 tokens target
CHUNK_OVERLAP_TOKENS = 64    # ~10% overlap for context continuity

# Medical section headers to use as natural split points
_SECTION_BREAKS = re.compile(
    r"\n(?=(?:Background|Introduction|Methods?|Materials?|Results?|"
    r"Discussion|Conclusions?|Abstract|Limitations?|"
    r"Intervention|Primary Outcome|Secondary Outcome|"
    r"Patient Population|Study Design)[:\s])",
    re.IGNORECASE,
)


def chunk_document(text: str, doc_metadata: Dict) -> List[Dict]:
    """
    Split a document into semantically coherent chunks.
    - First tries to split at medical section boundaries.
    - Falls back to token-based splitting with sentence overlap.
    Each chunk carries full source metadata for citation purposes.
    """
    if not text or not text.strip():
        return []

    # Try section-based splitting first
    sections = _SECTION_BREAKS.split(text)
    sections = [s.strip() for s in sections if s.strip()]

    if len(sections) > 1:
        # Recursively chunk any over-size sections
        chunks = []
        for section in sections:
            section_chunks = _token_chunk(section, doc_metadata)
            chunks.extend(section_chunks)
    else:
        chunks = _token_chunk(text, doc_metadata)

    # Assign chunk IDs
    base_id = _make_base_id(doc_metadata)
    for i, chunk in enumerate(chunks):
        chunk["metadata"]["chunk_id"] = f"{base_id}_{i}"
        chunk["metadata"]["chunk_index"] = i

    logger.debug(
        "Chunked document '%s': %d chunks",
        doc_metadata.get("title", "?")[:60],
        len(chunks),
    )
    return chunks


def _token_chunk(text: str, doc_metadata: Dict) -> List[Dict]:
    """Split text into token-bounded chunks with overlap."""
    tokens = _TOKENIZER.encode(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + CHUNK_SIZE_TOKENS, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = _TOKENIZER.decode(chunk_tokens)

        # Trim to the last complete sentence
        chunk_text = _trim_to_sentence(chunk_text)

        if chunk_text.strip():
            chunks.append(
                {
                    "text": chunk_text.strip(),
                    "metadata": dict(doc_metadata),  # copy
                }
            )

        if end >= len(tokens):
            break
        start = end - CHUNK_OVERLAP_TOKENS  # overlap

    return chunks


def _trim_to_sentence(text: str) -> str:
    """Trim text to end at a sentence boundary (. ! ?)."""
    sentence_end = max(
        text.rfind(". "),
        text.rfind("! "),
        text.rfind("? "),
        text.rfind(".\n"),
    )
    if sentence_end > len(text) * 0.7:
        return text[: sentence_end + 1]
    return text


def _make_base_id(meta: Dict) -> str:
    """Create a stable base ID from document identifiers."""
    pmid   = meta.get("pmid",   "")
    pmc_id = meta.get("pmc_id", "")
    doi    = meta.get("doi",    "").replace("/", "_").replace(".", "_")
    nct    = meta.get("nct_id", "")

    if pmid:
        return f"pubmed_{pmid}"
    if pmc_id:
        return f"pmc_{pmc_id}"
    if doi:
        return f"doi_{doi[:40]}"
    if nct:
        return f"ct_{nct}"
    # Fallback: hash of title
    import hashlib
    title_hash = hashlib.md5(meta.get("title", "").encode()).hexdigest()[:8]
    return f"doc_{title_hash}"
