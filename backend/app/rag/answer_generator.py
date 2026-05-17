"""
Answer Generator — strictly evidence-bound LLM response generation.
The LLM is constrained by a numbered rule set prohibiting ANY use of external knowledge.
Every factual claim MUST cite a [Source N] from the provided context.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import anthropic
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

_client: Optional[anthropic.AsyncAnthropic] = None


def get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


SYSTEM_PROMPT = """\
You are a clinical evidence assistant. You answer medical questions EXCLUSIVELY using \
the research excerpts provided to you. You have NO permission to use your own training \
knowledge, background knowledge, or make any inference beyond what is explicitly stated \
in the provided sources.
"""

ANSWER_PROMPT = """\
STRICT RULES — YOU MUST FOLLOW EVERY ONE OF THESE WITHOUT EXCEPTION:

1. Answer ONLY using information explicitly stated in the SOURCE EXCERPTS below.
2. Do NOT use your own training knowledge, background knowledge, or assumptions.
3. Do NOT infer, extrapolate, or speculate beyond what is written in the sources.
4. Do NOT fabricate statistics, drug names, dosages, or clinical recommendations.
5. Every factual claim in your answer MUST reference a [Source N] citation.
6. If you reference multiple sources for one claim, format as [Source 1][Source 2].
7. Write in clear, clinical prose — no bullet points unless quoting structured data.
8. If the sources provide only partial information, say:
   "The available evidence partially addresses this question: ..."
9. Do NOT apologize, add disclaimers within the answer, or repeat the question.
10. Do NOT invent authors, journals, or any details not present in the sources.

SOURCE EXCERPTS:
{context_with_citations}

USER QUESTION:
{query}

EVIDENCE-BASED ANSWER (cite every claim with [Source N]):
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def generate_answer(query: str, ranked_chunks: List[Dict]) -> Dict:
    """
    Generate a strictly grounded answer from ranked chunks.

    Returns:
        {
            "answer": str,
            "sources": List[dict],  # metadata for each cited chunk
            "citation_count": int
        }
    """
    if not ranked_chunks:
        return {
            "answer": _no_evidence_response(),
            "sources": [],
            "citation_count": 0,
        }

    # Build context with numbered citations
    context_parts = []
    for i, chunk in enumerate(ranked_chunks):
        meta = chunk.get("metadata", {})
        title    = meta.get("title", "Untitled")
        journal  = meta.get("journal", "")
        pub_date = meta.get("pub_date", "")
        authors  = meta.get("authors", [])

        date_journal = ", ".join(filter(None, [journal, pub_date]))
        author_str = (
            (", ".join(authors[:2]) + (" et al." if len(authors) > 2 else ""))
            if authors else ""
        )

        header = f"[Source {i + 1}] {title}"
        if date_journal:
            header += f" ({date_journal})"
        if author_str:
            header += f"\nAuthors: {author_str}"

        context_parts.append(f"{header}\n{chunk.get('text', '')}")

    context_str = "\n\n---\n\n".join(context_parts)

    try:
        client = get_client()
        response = await client.messages.create(
            model=settings.llm_model,
            max_tokens=1500,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": ANSWER_PROMPT.format(
                        context_with_citations=context_str,
                        query=query,
                    ),
                }
            ],
        )
        answer = response.content[0].text.strip()

        # Count citation references in the answer
        import re
        citations_found = set(re.findall(r"\[Source\s*(\d+)\]", answer, re.IGNORECASE))
        citation_count = len(citations_found)

        # Post-process Layer 4: if answer has 0 citations, it may be hallucinated
        if citation_count == 0 and len(ranked_chunks) > 0:
            logger.warning(
                "Answer generated with 0 citations — may contain unsupported claims. "
                "Replacing with no-evidence response."
            )
            return {
                "answer": _no_evidence_response(),
                "sources": [],
                "citation_count": 0,
            }

        logger.info(
            "Answer generated: %d chars, %d unique citations",
            len(answer), citation_count
        )

        return {
            "answer": answer,
            "sources": [c.get("metadata", {}) for c in ranked_chunks],
            "citation_count": citation_count,
        }

    except Exception as exc:
        logger.error("Answer generation failed: %s", exc)
        return {
            "answer": _no_evidence_response(),
            "sources": [],
            "citation_count": 0,
        }


def _no_evidence_response() -> str:
    return (
        "I was unable to find relevant evidence in the indexed medical literature "
        "to answer this question. Please consult a licensed medical professional "
        "or consider refining your query with more specific clinical terminology."
    )
