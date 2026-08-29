import logging
from typing import List

from src.agents.state import ComplianceState
from src.config import get_settings
from src.retrieval.hybrid_retriever import HybridRetriever

logger = logging.getLogger("aegis.retrieval")
settings = get_settings()


def retrieval_node(state: ComplianceState) -> dict:
    """
    Node 2: Hybrid retrieval agent combining dense vector search with reranking.
    """
    current_idx = state.get("current_step", 0)
    logger.info("NODE 2: retrieval agent — step %s", current_idx)

    plan = state["audit_plan"]
    if current_idx >= len(plan):
        logger.warning("current_step (%s) exceeds plan length (%s)", current_idx, len(plan))
        return {"current_context": []}

    target_query = plan[current_idx]
    logger.info("Retrieving hybrid context for query: %s", target_query)

    retriever = HybridRetriever.create()
    raw_results = retriever.retrieve(
        target_query,
        state["contract_meta"].get("jurisdiction", ""),
        document_name=state["contract_meta"].get("document_name"),
        execution_year=state["contract_meta"].get("execution_year"),
    )

    if not raw_results:
        logger.warning("No hybrid retrieval hits for sub-query '%s'", target_query)
        fallback = [
            {
                "text": "No matching clause was found in the indexed contract set for this sub-query.",
                "metadata": {
                    "document_name": "unknown",
                    "jurisdiction": state["contract_meta"].get("jurisdiction"),
                    "page_number": 0,
                    "section_label": "Operative Clause",
                    "chunk_hash": "",
                    "retrieval_score": 0.0,
                    "retrieval_method": "none",
                },
            }
        ]
        step_context = fallback
    else:
        step_context = [
            {
                "text": item.text,
                "metadata": {
                    "document_name": item.document_name,
                    "jurisdiction": state["contract_meta"].get("jurisdiction"),
                    "page_number": item.page_number,
                    "section_label": item.section_label,
                    "chunk_hash": item.chunk_hash,
                    "retrieval_score": item.score,
                    "retrieval_method": item.retrieval_method,
                    **item.source_metadata,
                },
            }
            for item in raw_results
        ]

    trail = list(state.get("retrieved_contexts", []))
    trail.extend(step_context)
    return {
        "current_context": step_context,
        "retrieved_contexts": trail,
    }
