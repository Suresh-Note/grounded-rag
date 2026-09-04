from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from enum import Enum
from typing import Any

logger = logging.getLogger("aegis.verifier")


class VerificationOutcome(str, Enum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"


def _normalize_text(text: str) -> str:
    # Collapse all whitespace, newlines, and non-alphanumeric punctuation for fuzzy checking
    text_clean = re.sub(r"\s+", " ", text.strip())
    return text_clean


def _fuzzy_find_quote(quote: str, context: str, threshold: float = 0.82) -> tuple[bool, str]:
    """
    Performs exact substring search first, falling back to sliding-window fuzzy matching
    to accommodate LLM whitespace variations or minor punctuation trimming.
    """
    if not quote or not context:
        return False, quote

    clean_quote = _normalize_text(quote)
    clean_context = _normalize_text(context)

    # 1. Direct normalized match
    if clean_quote.lower() in clean_context.lower():
        return True, quote

    # 2. Sliding window fuzzy match for long quotes
    quote_len = len(clean_quote)
    if quote_len < 10:
        return False, quote

    best_ratio = 0.0
    best_match_segment = quote

    # Slide window across context in increments
    step = max(1, quote_len // 4)
    for i in range(0, max(1, len(clean_context) - quote_len + 1), step):
        window = clean_context[i : i + quote_len + 20]
        ratio = SequenceMatcher(None, clean_quote.lower(), window.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match_segment = window

        if best_ratio >= threshold:
            logger.info("Fuzzy evidence match confirmed with score %.2f", best_ratio)
            return True, quote

    return False, quote


def grade_finding_with_evidence(finding: dict[str, Any], contexts: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Evaluates evidence quote groundedness against the retrieved context chunks using
    fuzzy matching, per chunk rather than against one flattened blob. This also lets
    us recover *which* chunk the quote actually came from, so evidence_location can
    be overwritten with the real document/page metadata instead of trusting the
    LLM's self-reported location — an LLM can quote real text correctly while still
    hallucinating the page number it claims that quote came from.
    """
    quote = finding.get("evidence_quote", "").strip()
    status = finding.get("finding_status", "NON_COMPLIANT")

    matched_metadata: dict[str, Any] | None = None
    for chunk in contexts:
        is_grounded, _ = _fuzzy_find_quote(quote, chunk.get("text", ""))
        if is_grounded:
            matched_metadata = chunk.get("metadata", {})
            break

    if matched_metadata is not None:
        if status == "UNVERIFIED_EVIDENCE":
            finding["finding_status"] = "NON_COMPLIANT"
        finding["confidence"] = max(finding.get("confidence", 0.8), 0.9)

        loc = dict(finding.get("evidence_location") or {})
        loc["document_name"] = matched_metadata.get("document_name", loc.get("document_name", ""))
        loc["page_number"] = matched_metadata.get("page_number", loc.get("page_number", 0))
        loc["chunk_hash"] = matched_metadata.get("chunk_hash", loc.get("chunk_hash", ""))
        # bbox/offsets are real, PDF-derived coordinates the LLM cannot actually
        # know — always prefer the retrieved chunk's values over anything the
        # model guessed, when the chunk actually carries them.
        if matched_metadata.get("bbox"):
            loc["bbox"] = matched_metadata["bbox"]
        if "offset_start" in matched_metadata:
            loc["offset_start"] = matched_metadata["offset_start"]
        if "offset_end" in matched_metadata:
            loc["offset_end"] = matched_metadata["offset_end"]
        finding["evidence_location"] = loc
    else:
        logger.warning("Evidence quote failed fuzzy verification against all retrieved chunks: '%s...'", quote[:50])
        finding["finding_status"] = "UNVERIFIED_EVIDENCE"
        finding["confidence"] = min(finding.get("confidence", 0.5), 0.3)

    return finding
