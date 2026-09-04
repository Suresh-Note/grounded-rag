from __future__ import annotations

import logging
from typing import Callable

from langgraph.graph import END, StateGraph

from src.agents.nodes.auditor import auditor_node
from src.agents.nodes.critic import critic_node
from src.agents.nodes.editor import consistency_editor_node
from src.agents.nodes.finalize import finalize_step_node
from src.agents.nodes.planner import planner_node
from src.agents.nodes.report_generator import report_generator_node
from src.agents.nodes.retrieval import retrieval_node
from src.agents.state import ComplianceState
from src.events.broadcaster import broadcaster
from src.state.store import get_state_store, JobState

logger = logging.getLogger("aegis.graph")

STAGE_PROGRESS = {
    "planner": 5.0,
    "retrieve": 25.0,
    "auditor": 55.0,
    "critic": 75.0,
    "finalize_step": 90.0,
    "consistency_editor": 95.0,
    "generate_report": 100.0,
}


def _publish_state_checkpoint(state: ComplianceState, stage: str, verified_findings_count: int = 0) -> None:
    job_id = state.get("request_id")
    if not job_id:
        return

    store = get_state_store()
    progress_percent = STAGE_PROGRESS.get(stage, 0.0)
    payload = {
        "stage": stage,
        "progress_percent": progress_percent,
        "verified_findings_count": verified_findings_count,
        "status": "running" if stage != "generate_report" else "completed",
        "last_message": f"Executing stage: {stage}",
    }

    store.save_state(
        JobState(
            job_id=job_id,
            stage=stage,
            progress_percent=progress_percent,
            verified_findings_count=verified_findings_count,
            status=payload["status"],
            last_message=payload["last_message"],
            payload=payload,
        )
    )
    broadcaster.publish_sync(job_id, payload)


def _checkpointed_node(name: str, node_fn: Callable[[ComplianceState], dict]) -> Callable[[ComplianceState], dict]:
    def wrapper(state: ComplianceState) -> dict:
        result = node_fn(state)
        updated_state = dict(state)
        updated_state.update(result)
        verified_findings_count = len(updated_state.get("validated_drafts", []))
        if name == "critic":
            current_findings = updated_state.get("current_findings", [])
            verified_findings_count = sum(
                1
                for finding in current_findings
                if finding.get("finding_status") != "UNVERIFIED_EVIDENCE"
            )
        _publish_state_checkpoint(updated_state, name, verified_findings_count)
        return result

    return wrapper


def route_after_critic(state: ComplianceState) -> str:
    if state.get("verification_passed", False):
        logger.info("Critic passed -> finalize_step")
        return "finalize_step"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)

    if retry_count >= max_retries:
        logger.warning("Max retries exhausted (%s/%s) -> finalize_step", retry_count, max_retries)
        return "finalize_step"

    logger.info("Critic failed (%s/%s retries) -> retry auditor", retry_count, max_retries)
    return "retry_audit"


def route_after_finalize(state: ComplianceState) -> str:
    current_step = state.get("current_step", 0)
    audit_plan = state.get("audit_plan", [])

    logger.info("Step %s of %s", current_step, len(audit_plan))

    if current_step < len(audit_plan):
        return "retrieve"

    logger.info("All sub-tasks done -> generating report")
    return "generate_report"


def build_compliance_graph() -> StateGraph:
    try:
        workflow = StateGraph(ComplianceState)

        workflow.add_node("planner", _checkpointed_node("planner", planner_node))
        workflow.add_node("retrieve", _checkpointed_node("retrieve", retrieval_node))
        workflow.add_node("auditor", _checkpointed_node("auditor", auditor_node))
        workflow.add_node("critic", _checkpointed_node("critic", critic_node))
        workflow.add_node("finalize_step", _checkpointed_node("finalize_step", finalize_step_node))
        workflow.add_node("consistency_editor", _checkpointed_node("consistency_editor", consistency_editor_node))
        workflow.add_node("generate_report", _checkpointed_node("generate_report", report_generator_node))

        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "retrieve")
        workflow.add_edge("retrieve", "auditor")
        workflow.add_edge("auditor", "critic")
        workflow.add_conditional_edges(
            "critic",
            route_after_critic,
            {
                "retry_audit": "auditor",
                "finalize_step": "finalize_step",
            },
        )
        workflow.add_conditional_edges(
            "finalize_step",
            route_after_finalize,
            {
                "retrieve": "retrieve",
                "generate_report": "consistency_editor",
            },
        )
        workflow.add_edge("consistency_editor", "generate_report")
        workflow.add_edge("generate_report", END)

        return workflow.compile()
    except Exception as exc:
        logger.critical("LangGraph compilation failed: %s", exc)
        raise RuntimeError(f"LangGraph initialization failure: {exc}") from exc
