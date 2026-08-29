from src.agents.nodes import editor as editor_module
from src.agents.nodes.editor import ConflictGroup, ConsistencyReview, consistency_editor_node


def _finding(status: str, param: str, quote: str) -> dict:
    return {
        "parameter": param,
        "finding_status": status,
        "evidence_quote": quote,
        "evidence_location": {"page_number": 1},
    }


def test_no_op_with_fewer_than_two_findings():
    state = {"validated_drafts": [_finding("NON_COMPLIANT", "A", "q")]}
    assert consistency_editor_node(state) == {}


def test_merges_duplicate_group_keeping_more_severe_status(monkeypatch):
    drafts = [
        _finding("COMPLIANT", "Retention Clause", "quote A"),
        _finding("NON_COMPLIANT", "Retention Clause (worded differently)", "quote A, slightly reworded"),
    ]
    state = {"validated_drafts": drafts}

    fake_review = ConsistencyReview(duplicate_groups=[ConflictGroup(indices=[0, 1], reason="same clause")])
    monkeypatch.setattr(editor_module, "invoke_with_timeout", lambda chain, inputs: fake_review)

    result = consistency_editor_node(state)

    assert len(result["validated_drafts"]) == 1
    kept = result["validated_drafts"][0]
    assert kept["finding_status"] == "NON_COMPLIANT"
    assert kept["reconciled_conflict"] is True
    # Evidence must never be rewritten by this pass — only merged/kept as-is.
    assert kept["evidence_quote"] == "quote A, slightly reworded"


def test_no_duplicate_groups_is_a_no_op(monkeypatch):
    drafts = [_finding("NON_COMPLIANT", "A", "q1"), _finding("COMPLIANT", "B", "q2")]
    state = {"validated_drafts": drafts}
    monkeypatch.setattr(editor_module, "invoke_with_timeout", lambda chain, inputs: ConsistencyReview(duplicate_groups=[]))

    assert consistency_editor_node(state) == {}


def test_llm_failure_is_handled_gracefully(monkeypatch):
    drafts = [_finding("NON_COMPLIANT", "A", "q1"), _finding("COMPLIANT", "B", "q2")]
    state = {"validated_drafts": drafts}

    def _raise(chain, inputs):
        raise RuntimeError("boom")

    monkeypatch.setattr(editor_module, "invoke_with_timeout", _raise)

    assert consistency_editor_node(state) == {}
