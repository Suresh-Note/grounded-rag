from src.verification.evidence_verifier import grade_finding_with_evidence


def _finding(quote: str, status: str = "NON_COMPLIANT", location: dict | None = None) -> dict:
    return {
        "evidence_quote": quote,
        "finding_status": status,
        "confidence": 0.6,
        "evidence_location": location or {"document_name": "unknown", "page_number": 0, "chunk_hash": ""},
    }


def _chunk(text: str, document_name: str, page_number: int, chunk_hash: str = "hash") -> dict:
    return {"text": text, "metadata": {"document_name": document_name, "page_number": page_number, "chunk_hash": chunk_hash}}


def test_exact_quote_is_grounded_and_confidence_boosted():
    finding = _finding("Vendor shall retain data for ninety (90) days.")
    contexts = [_chunk("Clause 2.2. Vendor shall retain data for ninety (90) days. See appendix.", "msa.pdf", 3)]

    result = grade_finding_with_evidence(finding, contexts)

    assert result["finding_status"] == "NON_COMPLIANT"
    assert result["confidence"] >= 0.9


def test_quote_not_found_anywhere_is_marked_unverified():
    finding = _finding("This exact sentence does not appear anywhere.")
    contexts = [_chunk("Completely unrelated contract text about something else entirely.", "msa.pdf", 1)]

    result = grade_finding_with_evidence(finding, contexts)

    assert result["finding_status"] == "UNVERIFIED_EVIDENCE"
    assert result["confidence"] <= 0.3


def test_unverified_status_is_promoted_once_grounded():
    finding = _finding("Vendor shall retain data for ninety (90) days.", status="UNVERIFIED_EVIDENCE")
    contexts = [_chunk("Vendor shall retain data for ninety (90) days.", "msa.pdf", 3)]

    result = grade_finding_with_evidence(finding, contexts)

    assert result["finding_status"] == "NON_COMPLIANT"


def test_evidence_location_is_overwritten_from_the_matching_chunk_not_the_llms_claim():
    # The LLM claims page 10, but the quote actually lives in the page-3 chunk.
    # Regression test for the bug where a real, grounded quote could carry a
    # hallucinated page/document citation straight into the report.
    finding = _finding(
        "Vendor shall retain data for ninety (90) days.",
        location={"document_name": "wrong.pdf", "page_number": 10, "chunk_hash": "stale"},
    )
    contexts = [
        _chunk("Some unrelated clause about indemnification.", "msa.pdf", 9, chunk_hash="hash-9"),
        _chunk("Clause 2.2. Vendor shall retain data for ninety (90) days.", "msa.pdf", 3, chunk_hash="hash-3"),
    ]

    result = grade_finding_with_evidence(finding, contexts)

    assert result["evidence_location"]["page_number"] == 3
    assert result["evidence_location"]["document_name"] == "msa.pdf"
    assert result["evidence_location"]["chunk_hash"] == "hash-3"


def test_whitespace_differences_are_normalized_away():
    finding = _finding("Vendor shall retain   data for   ninety (90) days.")
    contexts = [_chunk("Clause 2.2. Vendor shall retain data for ninety (90) days. See appendix.", "msa.pdf", 3)]

    result = grade_finding_with_evidence(finding, contexts)

    assert result["finding_status"] != "UNVERIFIED_EVIDENCE"
