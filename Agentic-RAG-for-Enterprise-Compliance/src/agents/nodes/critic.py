import logging
from typing import Any

from src.agents.schemas import CriticVerification
from src.agents.state import ComplianceState
from src.config import get_settings
from src.inference.gateway import safe_inference_target
from src.verification.evidence_verifier import grade_finding_with_evidence, VerificationOutcome

logger = logging.getLogger("aegis.critic")
settings = get_settings()


def critic_node(state: ComplianceState) -> dict:
    """
    Validates auditor findings against exact retrieved context and enforces strict evidence-grounding rules.
    """
    current_retry = state.get("retry_count", 0)
    current_step = state.get("current_step", 0)
    model_target = safe_inference_target()
    logger.info(
        "Executing NODE 4 (Critic Guardrail) | Step Index: %s | Active Retry Index: %s | target=%s",
        current_step,
        current_retry,
        model_target.model_name,
    )

    findings = state.get("current_findings", [])
    if not findings:
        logger.warning("No findings present in the current execution state buffer.")
        return {
            "critic_feedback": "Empty findings state. Re-evaluate context chunks and extract grounded entries.",
            "verification_passed": False,
            "retry_count": current_retry + 1,
        }

    contexts = state.get("current_context", [])
    problems: list[str] = []
    verified_findings_count = 0
    updated_findings: list[dict[str, Any]] = []

    for finding in findings:
        payload = finding.model_dump() if hasattr(finding, "model_dump") else dict(finding)
        updated = grade_finding_with_evidence(payload, contexts)
        updated_findings.append(updated)

        quote = payload.get("evidence_quote", "").strip()
        status = updated.get("finding_status")

        if status != "UNVERIFIED_EVIDENCE":
            verified_findings_count += 1
        else:
            rule = payload.get("rule_id", payload.get("parameter", "unknown"))
            truncated_quote = quote[:60]
            problems.append(
                f"Rule {rule} quote failure: The quote snippet ({truncated_quote}...) was NOT found in retrieved text. "
                "You MUST copy an exact character-for-character substring from the retrieved context, or set finding_status to UNVERIFIED_EVIDENCE."
            )

    verification_passed = len(problems) == 0
    feedback = (
        "All findings are grounded and verified."
        if verification_passed
        else "CRITICAL FIX REQUIRED: " + " ".join(problems)
    )

    logger.info(
        "Critic validation completed for job step %s: passed=%s verified_findings=%s issues=%s",
        current_step,
        verification_passed,
        verified_findings_count,
        len(problems),
    )

    return {
        "critic_feedback": feedback,
        "verification_passed": verification_passed,
        "retry_count": current_retry if verification_passed else current_retry + 1,
        "verified_findings_count": verified_findings_count,
        "current_findings": updated_findings,
    }
