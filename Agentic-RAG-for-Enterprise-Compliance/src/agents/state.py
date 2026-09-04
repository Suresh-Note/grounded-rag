from __future__ import annotations

from typing import Any, TypedDict

from src.agents.schemas import ComplianceFinding


class ComplianceState(TypedDict):
    """
    Unified transactional state for the multi-agent graph.

    - `current_context` holds ONLY the retrieval slice for the active sub-task.
      Reset each finalize step to prevent cross-contamination between sub-tasks.
    - `retrieved_contexts` is append-only — an audit trail of every chunk retrieved,
      never fed back into an LLM prompt.
    - `validated_drafts` receives one finalized entry per sub-task (critic-passed or
      retry-exhausted); intermediate attempts are discarded by finalize.
    """

    request_id: str
    raw_query: str
    contract_meta: dict[str, Any]

    audit_plan: list[str]
    current_step: int
    retry_count: int
    max_retries: int

    current_context: list[dict[str, Any]]
    retrieved_contexts: list[dict[str, Any]]

    current_findings: list[ComplianceFinding]
    validated_drafts: list[dict[str, Any]]

    critic_feedback: str | None
    verification_passed: bool

    final_compliance_report: dict[str, Any]
