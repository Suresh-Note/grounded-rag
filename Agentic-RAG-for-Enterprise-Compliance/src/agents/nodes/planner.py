import concurrent.futures
import logging

from langchain_core.prompts import ChatPromptTemplate

from src.agents.schemas import AuditPlan
from src.agents.state import ComplianceState
from src.config import get_settings
from src.inference.gateway import build_safe_chat_client, invoke_with_timeout

logger = logging.getLogger("aegis.planner")
settings = get_settings()

SYSTEM_PROMPT = (
    "You are an elite enterprise legal auditor. Break down a high-level compliance audit query "
    "into 2 to 4 independent, specific semantic search strings targeting conflicts, clauses, "
    "timelines, or limitations. Do not include commentary, numbering, or an introduction."
)


def planner_node(state: ComplianceState) -> dict:
    """
    Node 1: Deconstruction & Planning Agent.
    Also acts as the state-reset point: every field a fresh run needs is
    (re)initialized here, so a caller that forgets a key in the initial
    payload can't leave the graph in an inconsistent state.
    """
    logger.info("NODE 1: planning agent")

    llm = build_safe_chat_client()
    structured_llm = llm.with_structured_output(AuditPlan)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("user", "Audit Objective: {raw_query}\nTarget Jurisdiction Meta: {contract_meta}"),
        ]
    )

    chain = prompt | structured_llm
    sub_queries: list[str] = []
    try:
        result: AuditPlan = invoke_with_timeout(
            chain, {"raw_query": state["raw_query"], "contract_meta": str(state["contract_meta"])}
        )
        sub_queries = [q.strip() for q in result.sub_queries if q.strip()]
    except concurrent.futures.TimeoutError:
        logger.error(
            "Planner LLM call exceeded %ss timeout (backend may be unresponsive or out of memory); "
            "falling back to single-query plan.",
            settings.BACKEND_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.error("Planner structured generation failed, falling back to single-query plan: %s", exc)

    if not sub_queries:
        sub_queries = [state["raw_query"]]

    return {
        "audit_plan": sub_queries,
        "current_step": 0,
        "retry_count": 0,
        "max_retries": state.get("max_retries", settings.MAX_AUDIT_RETRIES),
        "current_context": [],
        "retrieved_contexts": [],
        "current_findings": [],
        "validated_drafts": [],
        "critic_feedback": None,
        "verification_passed": False,
    }
