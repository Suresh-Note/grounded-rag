from src.agents.nodes.finalize import finalize_step_node


def _finding(status: str, page: int, quote: str, analysis: str = "analysis text") -> dict:
    return {
        "rule_id": "R1",
        "parameter": "Data Retention Clause",
        "finding_status": status,
        "evidence_quote": quote,
        "evidence_location": {"document_name": "msa.pdf", "page_number": page, "chunk_hash": "h"},
        "analysis": analysis,
        "confidence": 0.9,
        "risk_score": 50.0,
    }


def _state(current_findings, validated_drafts=None, current_step=0):
    return {
        "current_step": current_step,
        "current_findings": current_findings,
        "validated_drafts": validated_drafts or [],
    }


def test_fresh_finding_is_committed_and_step_advances():
    state = _state([_finding("NON_COMPLIANT", 3, "ninety (90) days")])

    result = finalize_step_node(state)

    assert len(result["validated_drafts"]) == 1
    assert result["current_step"] == 1
    assert result["retry_count"] == 0
    assert result["current_findings"] == []


def test_unverified_evidence_is_tagged_unresolved():
    state = _state([_finding("UNVERIFIED_EVIDENCE", 3, "some quote")])

    result = finalize_step_node(state)

    assert result["validated_drafts"][0]["unresolved_after_retries"] is True


def test_lower_severity_duplicate_does_not_overwrite_existing_non_compliant():
    existing = _finding("NON_COMPLIANT", 3, "ninety (90) days", analysis="first pass")
    incoming = _finding("COMPLIANT", 3, "ninety (90) days", analysis="second pass, different wording")
    state = _state([incoming], validated_drafts=[existing], current_step=1)

    result = finalize_step_node(state)

    assert len(result["validated_drafts"]) == 1
    assert result["validated_drafts"][0]["finding_status"] == "NON_COMPLIANT"
    assert not result["validated_drafts"][0].get("reconciled_conflict")


def test_higher_severity_duplicate_overwrites_and_is_flagged_reconciled():
    existing = _finding("COMPLIANT", 3, "ninety (90) days", analysis="first pass")
    incoming = _finding("NON_COMPLIANT", 3, "ninety (90) days", analysis="second pass, different wording")
    state = _state([incoming], validated_drafts=[existing], current_step=1)

    result = finalize_step_node(state)

    assert len(result["validated_drafts"]) == 1
    assert result["validated_drafts"][0]["finding_status"] == "NON_COMPLIANT"
    assert result["validated_drafts"][0]["reconciled_conflict"] is True


def test_different_clauses_are_not_merged():
    existing = _finding("NON_COMPLIANT", 3, "ninety (90) days retention clause")
    incoming = _finding("NON_COMPLIANT", 9, "processed outside the European Union")
    state = _state([incoming], validated_drafts=[existing], current_step=1)

    result = finalize_step_node(state)

    assert len(result["validated_drafts"]) == 2
