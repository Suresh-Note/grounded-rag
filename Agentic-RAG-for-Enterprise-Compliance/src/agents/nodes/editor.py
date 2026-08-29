import concurrent.futures
import logging
from typing import List

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.agents.nodes.finalize import _STATUS_SEVERITY
from src.agents.state import ComplianceState
from src.inference.gateway import build_safe_chat_client, invoke_with_timeout

logger = logging.getLogger("aegis.editor")

SYSTEM_PROMPT = (
    "You are a senior compliance editor performing a final consistency pass over a completed audit's findings.\n"
    "Each finding was produced by an independent sub-task and may refer to the exact same underlying clause as "
    "another finding, worded differently, on the same or a nearby page — sub-tasks cannot see each other's work.\n\n"
    "YOUR ONLY JOB: identify groups of findings (by index) that refer to the SAME underlying clause or evidence, "
    "even if the page number, quote wording, or verdict differs between them. Do not evaluate whether a verdict is "
    "correct, do not rewrite anything, and do not invent new findings — only group indices that are duplicates of "
    "each other. If nothing is duplicated, return an empty list.\n\n"
    "JSON SCHEMA:\n{json_schema}"
)


class ConflictGroup(BaseModel):
    indices: List[int] = Field(..., description="0-based indices of findings that refer to the same clause/evidence.")
    reason: str = Field(..., description="Brief reason these are the same underlying clause.")


class ConsistencyReview(BaseModel):
    duplicate_groups: List[ConflictGroup] = Field(default_factory=list)


def _status_of(f: dict) -> str:
    status = f.get("finding_status")
    return status.value if hasattr(status, "value") else str(status)


def _summarize_findings(drafts: list[dict]) -> str:
    lines = []
    for i, f in enumerate(drafts):
        quote = str(f.get("evidence_quote", ""))[:100]
        loc = f.get("evidence_location") or {}
        lines.append(
            f"[{i}] parameter=\"{f.get('parameter', '')}\" status={_status_of(f)} "
            f"page={loc.get('page_number', '?')} quote=\"{quote}\""
        )
    return "\n".join(lines)


def consistency_editor_node(state: ComplianceState) -> dict:
    """
    Node 5.5: Final Whole-Report Consistency Pass.

    finalize.py already reconciles duplicates it can detect mechanically (same
    document/page/quote-prefix). This node catches the ones that slip past that —
    the same clause worded or cited differently across independent sub-tasks —
    by asking the LLM to GROUP duplicate indices only. The actual keep/drop
    decision is still made in code using the same severity policy already used
    in finalize.py (never let a COMPLIANT verdict silently override a
    NON_COMPLIANT/UNVERIFIED_EVIDENCE one), and evidence_quote/evidence_location
    are never touched — this pass can only merge or flag, never rewrite evidence.
    """
    drafts = list(state.get("validated_drafts", []))
    if len(drafts) < 2:
        return {}

    llm = build_safe_chat_client()
    structured_llm = llm.with_structured_output(ConsistencyReview)
    schema_str = ConsistencyReview.model_json_schema()

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", "Findings from this completed audit run:\n{findings}\n\nGroup any duplicates."),
        ]
    )
    chain = prompt | structured_llm

    try:
        review: ConsistencyReview = invoke_with_timeout(
            chain, {"json_schema": schema_str, "findings": _summarize_findings(drafts)}
        )
    except concurrent.futures.TimeoutError:
        logger.warning("Consistency editor LLM call timed out; skipping this pass, findings unchanged.")
        return {}
    except Exception as exc:
        logger.warning("Consistency editor failed (%s); skipping this pass, findings unchanged.", exc)
        return {}

    if review is None or not review.duplicate_groups:
        logger.info("Consistency editor found no additional duplicate clauses across %s findings.", len(drafts))
        return {}

    removed_indices: set[int] = set()
    merged_count = 0
    for group in review.duplicate_groups:
        valid = sorted({i for i in group.indices if 0 <= i < len(drafts)} - removed_indices)
        if len(valid) < 2:
            continue
        best_idx = max(valid, key=lambda i: _STATUS_SEVERITY.get(_status_of(drafts[i]), 0))
        drafts[best_idx]["reconciled_conflict"] = True
        for i in valid:
            if i != best_idx:
                removed_indices.add(i)
        merged_count += len(valid) - 1

    if not removed_indices:
        return {}

    final_drafts = [f for i, f in enumerate(drafts) if i not in removed_indices]
    logger.info(
        "Consistency editor merged %s duplicate finding(s) found across sub-tasks (%s -> %s total).",
        merged_count,
        len(state.get("validated_drafts", [])),
        len(final_drafts),
    )
    return {"validated_drafts": final_drafts}
