from typing import Any, Dict, List, Optional, TypedDict

from src.agents.schemas import ComplianceFinding


class ComplianceState(TypedDict):
    """
    Unified transactional state for the Aegis multi-agent graph.

    Design notes (this is the piece that fixes the state-leak bug in the
    original implementation):

    - `current_context` holds ONLY the retrieval slice for the sub-task
      currently being worked on. It is reset every time a sub-task is
      finalized. The Auditor and Critic only ever see this slice, never the
      full accumulated history — this keeps prompts small and prevents one
      sub-task's context from contaminating another's verdict.
    - `retrieved_contexts` is a separate, append-only audit trail of every
      chunk retrieved across the whole run. It exists purely for citation
      traceability and is never fed back into an LLM prompt.
    - `validated_drafts` receives exactly ONE finalized entry per sub-task —
      either a critic-passed finding set, or a retry-exhausted one explicitly
      flagged `unresolved_after_retries`. Failed intermediate attempts are
      discarded by the finalize node, so hallucinated drafts can never leak
      into the final report as duplicates.
    """

    request_id: str
    raw_query: str
    contract_meta: Dict[str, Any]

    audit_plan: List[str]
    current_step: int
    retry_count: int
    max_retries: int

    current_context: List[Dict[str, Any]]
    retrieved_contexts: List[Dict[str, Any]]

    current_findings: List[ComplianceFinding]
    validated_drafts: List[Dict[str, Any]]

    critic_feedback: Optional[str]
    verification_passed: bool

    final_compliance_report: Dict[str, Any]
