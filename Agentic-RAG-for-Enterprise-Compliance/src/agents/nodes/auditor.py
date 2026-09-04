from __future__ import annotations

import concurrent.futures
import json
import logging

from langchain_core.prompts import ChatPromptTemplate

from src.agents.schemas import AuditorOutput
from src.agents.state import ComplianceState
from src.config import get_settings
from src.inference.gateway import build_safe_chat_client, invoke_with_timeout

logger = logging.getLogger("aegis.auditor")
settings = get_settings()

SYSTEM_PROMPT = (
    "You are an expert enterprise Regulatory Compliance Auditor specializing in contract and legal audit findings.\n"
    "Evaluate only the retrieved contract context and the audit objective. Do not invent any text or claim beyond the exact evidence available.\n\n"
    "CRITICAL EVIDENCE GROUNDING RULES:\n"
    "1. evidence_quote MUST be an EXACT, VERBATIM substring copied directly from the retrieved contract context. Do not paraphrase, reformat, or alter punctuation.\n"
    "2. If you cannot find an exact verbatim quote matching your finding in the retrieved context, set finding_status to 'UNVERIFIED_EVIDENCE'.\n"
    "3. Return ONLY valid JSON matching the required schema below. No conversational text.\n"
    "4. Always include complete evidence_location metadata.\n"
    "5. Use finding_status values: COMPLIANT, NON_COMPLIANT, or UNVERIFIED_EVIDENCE only.\n"
    "6. risk_score MUST be a numeric float between 0.0 and 100.0.\n"
    "7. confidence MUST be a numeric float between 0.0 and 1.0.\n"
    "8. RELEVANCE CHECK: Before writing a finding, confirm the retrieved context actually addresses the audit "
    "objective's specific topic. If a chunk is unrelated boilerplate (e.g. generic infrastructure, formatting, or "
    "signature text that does not speak to the objective), DO NOT force it into an unrelated category (such as "
    "labeling infrastructure text a 'liability clause' just because the objective asked about liability). Omit it "
    "from findings entirely rather than inventing a verdict on irrelevant text. Returning zero findings for this "
    "sub-task is valid and preferred over a fabricated one.\n"
    "9. CONSISTENCY CHECK: You will be shown findings already recorded by earlier sub-tasks in this same audit run. "
    "If the current context is discussing the same clause as one already recorded, your verdict MUST match the "
    "earlier one unless the current context contains genuinely different evidence the earlier sub-task did not see. "
    "Never contradict a prior finding about the same clause without a concrete evidentiary reason.\n\n"
    "JSON SCHEMA TO ADHERE TO:\n{json_schema}"
)


def _build_context_str(contexts: list[dict]) -> str:
    if not contexts:
        return "No specific contract text retrieved for this task slice."
    return "\n".join(
        f"--- CONTEXT CHUNK (Source: {c.get('metadata', {}).get('document_name', 'unknown')} page {c.get('metadata', {}).get('page_number', 'unknown')}) ---\n{c.get('text', '')}"
        for c in contexts
    )


def _summarize_prior_findings(validated_drafts: list) -> str:
    if not validated_drafts:
        return "None yet — this is the first sub-task in this audit run."
    lines = []
    for f in validated_drafts[:20]:
        payload = f.model_dump() if hasattr(f, "model_dump") else dict(f)
        param = payload.get("parameter") or payload.get("rule_id") or "Unknown clause"
        status = payload.get("finding_status", "UNKNOWN")
        status = status.value if hasattr(status, "value") else status
        lines.append(f"- {param}: {status}")
    return "\n".join(lines)


def auditor_node(state: ComplianceState) -> dict:
    """
    Node 3: Ground-Truth Legal Auditor Agent.
    """
    current_step = state.get("current_step", 0)
    current_retry = state.get("retry_count", 0)
    logger.info(
        "NODE 3: auditor agent — step %s, retry %s",
        current_step,
        current_retry,
    )

    llm = build_safe_chat_client()
    schema_dict = AuditorOutput.model_json_schema()
    schema_str = json.dumps(schema_dict, indent=2)

    structured_llm = llm.with_structured_output(AuditorOutput)

    raw_feedback = state.get("critic_feedback")
    if current_retry > 0 and raw_feedback:
        feedback_str = (
            f"ATTENTION: Your previous findings failed Quality Control validation for the following reason:\n"
            f"{raw_feedback}\n\n"
            f"FIX DIRECTIVE: Look at the CONTEXT CHUNKS below and COPY the evidence quotes EXACTLY as written character-for-character."
        )
    else:
        feedback_str = "None. First attempt for this sub-task."

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "user",
                (
                    "Audit Objective:\n{raw_query}\n\n"
                    "Retrieved Contract Context (this sub-task only):\n{contexts}\n\n"
                    "Findings Already Recorded By Earlier Sub-Tasks (stay consistent with these):\n{prior_findings}\n\n"
                    "Prior Quality-Control Feedback:\n{feedback}\n\n"
                    "Produce the grounded findings for this sub-task."
                ),
            ),
        ]
    )

    context_str = _build_context_str(state.get("current_context", []))
    prior_findings_str = _summarize_prior_findings(state.get("validated_drafts", []))

    chain = prompt | structured_llm
    try:
        result: AuditorOutput = invoke_with_timeout(
            chain,
            {
                "json_schema": schema_str,
                "raw_query": state["raw_query"],
                "contexts": context_str,
                "prior_findings": prior_findings_str,
                "feedback": feedback_str,
            },
        )
        if result is None:
            result = AuditorOutput(findings=[])
    except concurrent.futures.TimeoutError:
        logger.error(
            "Auditor LLM call exceeded %ss timeout (backend may be unresponsive or out of memory); "
            "returning no findings for this sub-task.",
            settings.BACKEND_TIMEOUT_SECONDS,
        )
        result = AuditorOutput(findings=[])
    except Exception as exc:
        logger.error("Auditor structured generation failed: %s", exc)
        result = AuditorOutput(findings=[])

    return {"current_findings": result.findings}
