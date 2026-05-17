"""
Context Builder — assembles ranked chunks into a structured, citation-numbered
context string for the LLM, respecting token budget limits.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import tiktoken

from app.config import settings

logger = logging.getLogger(__name__)

_TOKENIZER = tiktoken.get_encoding("cl100k_base")


def build_context(chunks: List[Dict]) -> Tuple[str, List[Dict]]:
    """
    Assemble ranked chunks into a numbered context string.

    Each source is formatted as:
      [Source N] Title (Journal, Date)
      Authors: ...
      Text: ...

    Returns:
        (context_string, included_chunks)
        included_chunks may be fewer than input if token budget is exceeded.
    """
    max_tokens = settings.max_context_tokens
    context_parts: List[str] = []
    included_chunks: List[Dict] = []
    token_count = 0

    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})
        title   = meta.get("title", "Untitled")
        journal = meta.get("journal", "")
        pub_date = meta.get("pub_date", "")
        authors = meta.get("authors", [])
        text    = chunk.get("text", "")

        # Format source header
        date_journal = ", ".join(filter(None, [journal, pub_date]))
        authors_str = (
            ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            if authors else "Authors not listed"
        )

        source_block = (
            f"[Source {i + 1}] {title}"
            + (f" ({date_journal})" if date_journal else "")
            + f"\nAuthors: {authors_str}"
            + f"\n{text}"
        )

        block_tokens = len(_TOKENIZER.encode(source_block))
        if token_count + block_tokens > max_tokens:
            logger.debug(
                "Context budget reached at source %d/%d (%d tokens)",
                i + 1, len(chunks), token_count,
            )
            break

        context_parts.append(source_block)
        included_chunks.append(chunk)
        # Assign source index (1-based) for citation matching
        chunk["source_index"] = i + 1
        token_count += block_tokens

    context_str = "\n\n---\n\n".join(context_parts)
    logger.debug(
        "Built context: %d sources, ~%d tokens", len(included_chunks), token_count
    )
    return context_str, included_chunks
