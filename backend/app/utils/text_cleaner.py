"""
Text cleaning utilities for raw medical document text.
Handles HTML, XML artifacts, whitespace normalization, and encoding issues.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


# ── HTML/XML cleanup ──────────────────────────────────────────────────────────

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")
_MULTIPLE_NEWLINES = re.compile(r"\n{3,}")
_UNICODE_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def strip_html(text: str) -> str:
    """Remove HTML/XML tags and decode common entities."""
    if not text:
        return ""
    # Replace common HTML entities
    replacements = {
        "&amp;": "&", "&lt;": "<", "&gt;": ">",
        "&quot;": '"', "&#39;": "'", "&nbsp;": " ",
        "&mdash;": "—", "&ndash;": "–", "&hellip;": "…",
    }
    for entity, char in replacements.items():
        text = text.replace(entity, char)
    text = _HTML_TAG_RE.sub(" ", text)
    return text


def normalize_whitespace(text: str) -> str:
    """Collapse multiple spaces/newlines."""
    text = _MULTIPLE_SPACES.sub(" ", text)
    text = _MULTIPLE_NEWLINES.sub("\n\n", text)
    return text.strip()


def remove_control_chars(text: str) -> str:
    """Remove non-printable control characters."""
    return _UNICODE_CONTROL.sub("", text)


def normalize_unicode(text: str) -> str:
    """NFC-normalize Unicode and replace exotic dashes/quotes."""
    text = unicodedata.normalize("NFC", text)
    # Normalize various dash types
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    # Normalize quotes
    text = re.sub(r"[\u2018\u2019]", "'", text)
    text = re.sub(r'[\u201c\u201d]', '"', text)
    return text


def clean_text(text: str) -> str:
    """Full cleaning pipeline: HTML → Unicode → control chars → whitespace."""
    if not text:
        return ""
    text = strip_html(text)
    text = normalize_unicode(text)
    text = remove_control_chars(text)
    text = normalize_whitespace(text)
    return text


# ── Medical text specific ─────────────────────────────────────────────────────

_SECTION_HEADERS = re.compile(
    r"^(abstract|background|methods?|results?|conclusions?|introduction|"
    r"discussion|references?|acknowledgements?|author contributions?|"
    r"conflict of interest|funding|supplementary|keywords?|"
    r"materials? and methods?|study design|limitations?)[\s:]*$",
    re.IGNORECASE | re.MULTILINE,
)


def extract_section(text: str, section_name: str) -> Optional[str]:
    """
    Extract a named section from a structured medical abstract.
    E.g., extract_section(text, "Background") → background text
    """
    pattern = re.compile(
        rf"(?:^|\n){re.escape(section_name)}[\s:]*\n?(.*?)(?=\n[A-Z][a-z]+:|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    m = pattern.search(text)
    if m:
        return clean_text(m.group(1))
    return None


def truncate_text(text: str, max_chars: int = 300) -> str:
    """Truncate text at a sentence boundary near max_chars."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Try to end at sentence boundary
    last_period = truncated.rfind(". ")
    if last_period > max_chars * 0.6:
        return truncated[: last_period + 1] + "…"
    return truncated + "…"
