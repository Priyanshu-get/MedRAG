"""
Query Rewriter — expands medical queries into optimized PubMed search terms.
Uses Gemini to inject MeSH vocabulary, expand abbreviations, and decompose
complex queries into retrievable sub-questions.
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings

logger = logging.getLogger(__name__)

_model: Optional[genai.GenerativeModel] = None


def get_model() -> genai.GenerativeModel:
    global _model
    if _model is None:
        genai.configure(api_key=settings.gemini_api_key)
        _model = genai.GenerativeModel(
            model_name=settings.llm_model,
            generation_config=genai.GenerationConfig(
                temperature=0.3,
            ),
        )
    return _model


REWRITE_PROMPT = """\
You are a medical information retrieval specialist with expertise in PubMed search optimization.

Given a user's medical query, rewrite it into 3 distinct, optimized search queries suitable \
for searching PubMed and medical literature databases.

Requirements:
1. Use official medical terminology and MeSH (Medical Subject Headings) terms.
2. Expand any abbreviations (e.g., "MI" → "myocardial infarction").
3. Include related clinical concepts, synonyms, and alternative terms.
4. Make each query distinct — covering different aspects or phrasings.
5. Each query should be concise (under 15 words) and highly specific.

Return ONLY a valid JSON array of exactly 3 query strings. No explanation, no markdown, \
no extra text — just the JSON array.

Example input: "best drug for high blood pressure"
Example output: ["hypertension first-line pharmacotherapy ACE inhibitors", \
"antihypertensive medication guidelines JNC 8", \
"thiazide diuretics calcium channel blockers blood pressure treatment"]

User Query: {query}
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
async def rewrite_query(user_query: str) -> List[str]:
    """
    Expand user query into 3 medical-vocabulary-optimized search queries.
    Falls back to the original query if LLM call fails.
    """
    try:
        model = get_model()
        response = await model.generate_content_async(
            REWRITE_PROMPT.format(query=user_query)
        )
        text = response.text.strip()
        
        # Robustly extract JSON using regex
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
            
        queries = json.loads(text)
        if isinstance(queries, list) and len(queries) >= 1:
            # Always include the original query as a safety net
            queries = [q for q in queries if isinstance(q, str) and q.strip()]
            if user_query not in queries:
                queries.append(user_query)
            logger.debug("Query rewritten to %d variants", len(queries))
            return queries[:4]  # max 4 queries

    except json.JSONDecodeError as exc:
        logger.warning("Query rewriter returned invalid JSON: %s", exc)
    except Exception as exc:
        logger.warning("Query rewriter failed: %s", exc)

    # Fallback: return original query only
    return [user_query]
