"""
Hallucination Guard — the most critical component of the pipeline.

Uses LLM-as-judge to validate whether retrieved context is sufficient to
answer the user's query BEFORE generating an answer. If confidence is below
the threshold, the system returns "I don't know" — no answer is generated.

This is Layer 2 of the 7-layer anti-hallucination strategy.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, Optional

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


GUARD_PROMPT = """\
You are a strict medical evidence auditor. Your ONLY job is to determine whether \
the provided retrieved context contains DIRECT, SPECIFIC evidence to answer the user's query.

USER QUERY:
{query}

RETRIEVED CONTEXT:
{context}

CRITICAL RULES — READ CAREFULLY:
1. Do NOT use any knowledge outside of the RETRIEVED CONTEXT above.
2. Evaluate ONLY whether the context explicitly addresses the query.
3. "Tangentially related" or "partially relevant" = has_answer: false.
4. The context must directly state or strongly imply the answer to the specific query.
5. If the context is about a different disease, drug, or condition than asked → false.
6. If the context provides general background but not a specific answer → false.
7. Confidence = how directly and completely the context answers the query (0.0 to 1.0).
8. If has_answer = false, confidence MUST be below 0.5.

Respond with ONLY this JSON object, no other text:
{{
  "has_answer": true or false,
  "confidence": 0.0 to 1.0,
  "reasoning": "one sentence explaining your decision"
}}
"""


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=5))
async def validate_context(query: str, context: str) -> Dict:
    """
    Validate whether the retrieved context can ground an answer to the query.

    Returns:
        {
            "can_answer": bool,
            "confidence": float,
            "reasoning": str
        }
    """
    if not context.strip():
        logger.debug("Hallucination guard: empty context → cannot answer")
        return {
            "can_answer": False,
            "confidence": 0.0,
            "reasoning": "No context was retrieved.",
        }

    try:
        client = get_client()
        response = await client.messages.create(
            model=settings.llm_model,
            max_tokens=200,
            messages=[
                {
                    "role": "user",
                    "content": GUARD_PROMPT.format(query=query, context=context[:6000]),
                }
            ],
        )
        raw = response.content[0].text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        result = json.loads(raw)

        has_answer = bool(result.get("has_answer", False))
        confidence = float(result.get("confidence", 0.0))
        reasoning  = str(result.get("reasoning", ""))

        # Enforce rule: if has_answer=False, confidence must be < 0.5
        if not has_answer and confidence >= 0.5:
            confidence = min(confidence, 0.49)

        threshold = settings.hallucination_confidence_threshold
        can_answer = has_answer and (confidence >= threshold)

        logger.info(
            "Hallucination guard: has_answer=%s, confidence=%.2f, can_answer=%s | %s",
            has_answer, confidence, can_answer, reasoning[:80],
        )

        return {
            "can_answer": can_answer,
            "confidence": confidence,
            "reasoning": reasoning,
        }

    except json.JSONDecodeError as exc:
        logger.warning("Guard returned invalid JSON: %s", exc)
    except Exception as exc:
        logger.error("Hallucination guard call failed: %s", exc)

    # On failure, be conservative: refuse to answer
    return {
        "can_answer": False,
        "confidence": 0.0,
        "reasoning": "Guard evaluation failed — defaulting to no-answer for safety.",
    }
