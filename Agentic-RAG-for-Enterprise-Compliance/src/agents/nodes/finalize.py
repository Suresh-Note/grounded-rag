from __future__ import annotations

import logging
import re
from src.agents.state import ComplianceState

logger = logging.getLogger("aegis.finalize")

# Used to reconcile conflicting verdicts about the same underlying clause: a
# NON_COMPLIANT or UNVERIFIED_EVIDENCE call must never be silently overwritten
# by a later COMPLIANT one for the same evidence — false negatives are the
# expensive failure mode for a compliance tool, not false positives.
_STATUS_SEVERITY = {"NON_COMPLIANT": 2, "UNVERIFIED_EVIDENCE": 1, "COMPLIANT": 0}


def _clause_identity_key(f: dict) -> str:
    """
    Identifies "the same underlying clause" across independent sub-tasks, since the
    Planner's overlapping sub-queries frequently re-retrieve and re-judge the same
    contract text. Keyed on (document, page, quote-prefix) rather than the LLM's
    paraphrased `analysis` text, which differs on every call even for identical
    evidence. Relies on evidence_location being grounded to the real retrieved
    chunk (see evidence_verifier.grade_finding_with_evidence), not the LLM's
    self-reported page number.
    """
    loc = f.get("evidence_location") or {}
    doc = str(loc.get("document_name", "")).strip().lower()
    page = str(loc.get("page_number", "")).strip()
    quote_key = re.sub(r"[^a-z0-9]", "", str(f.get("evidence_quote", "")).lower())[:40]
    if quote_key:
        return f"{doc}|{page}|{quote_key}"
    param_key = re.sub(r"[^a-z0-9]", "", str(f.get("parameter", "")).lower())[:40]
    return f"{doc}|{page}|{param_key}" if param_key else ""


def finalize_step_node(state: ComplianceState) -> dict:
    """
    Flushes verified intermediate execution buffers into historical logs,
    increments the system task index, and clears tracking states for the next loop.
    """
    current_idx = state.get("current_step", 0)
    logger.info("NODE 5: finalize — committing step %s", current_idx)

    # 1. Extract current findings and history
    current_findings = state.get("current_findings", [])
    validated_drafts = list(state.get("validated_drafts", []))

    # 2. Normalize to dicts and explicitly flag anything the Critic never grounded.
    # This path is reached either because verification passed, or because retries
    # were exhausted (route_after_critic) — an UNVERIFIED_EVIDENCE finding here means
    # the latter, so it must be tagged rather than silently promoted into a clean entry.
    committable: list[dict] = []
    for f in current_findings:
        f_dict = f.model_dump() if hasattr(f, "model_dump") else dict(f)
        status = f_dict.get("finding_status")
        status_value = status.value if hasattr(status, "value") else status
        if status_value == "UNVERIFIED_EVIDENCE":
            f_dict["unresolved_after_retries"] = True
        committable.append(f_dict)

    # 3. Commit findings, reconciling duplicates that refer to the same clause.
    if committable:
        key_to_index = {
            _clause_identity_key(f): idx
            for idx, f in enumerate(validated_drafts)
            if _clause_identity_key(f)
        }

        added_count = 0
        reconciled_count = 0
        for f in committable:
            key = _clause_identity_key(f)
            existing_idx = key_to_index.get(key) if key else None

            if existing_idx is None:
                if key:
                    key_to_index[key] = len(validated_drafts)
                validated_drafts.append(f)
                added_count += 1
                continue

            existing = validated_drafts[existing_idx]
            existing_status = existing.get("finding_status")
            new_status = f.get("finding_status")
            if _STATUS_SEVERITY.get(new_status, 0) > _STATUS_SEVERITY.get(existing_status, 0):
                f["reconciled_conflict"] = True
                validated_drafts[existing_idx] = f
                reconciled_count += 1
            # else: an equal-or-lower-severity duplicate of an already-recorded clause; drop it.

        unresolved_count = sum(1 for f in validated_drafts if f.get("unresolved_after_retries"))
        logger.info(
            "Committed %s findings (%s conflicts reconciled, %s unresolved)",
            added_count,
            reconciled_count,
            unresolved_count,
        )
    else:
        logger.warning("Finalization step triggered with no active findings.")

    # 4. Reset state for the next sub-task
    return {
        "validated_drafts": validated_drafts,
        "current_step": current_idx + 1,
        "retry_count": 0,               # Reset loop tracking completely for next task item
        "current_findings": [],         # Flush buffer clear
        "critic_feedback": None,        # Flush feedback clear
        "verification_passed": False    # Clear loop gate condition flag
    }