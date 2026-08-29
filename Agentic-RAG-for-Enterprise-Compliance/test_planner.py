import asyncio
from src.agents.nodes.planner import planner_node
from src.agents.state import ComplianceState

def main():
    print("Initializing Local Agentic Core Test...")
    
    # 1. Simulate an incoming compliance audit payload matching our state ledger layout
    mock_state: ComplianceState = {
        "request_id": "test-request-id",
        "raw_query": "Verify if our vendor data retention protocols breach the strict GDPR 2026 data privacy updates.",
        "contract_meta": {
            "jurisdiction": "European Union",
            "document_type": "Data Processing Addendum (DPA)",
            "execution_year": 2026,
        },
        "audit_plan": [],
        "current_step": 0,
        "retry_count": 0,
        "max_retries": 2,
        "current_context": [],
        "retrieved_contexts": [],
        "current_findings": [],
        "validated_drafts": [],
        "critic_feedback": None,
        "verification_passed": False,
        "final_compliance_report": {},
    }
    
    # 2. Fire the Planning Node to run local token inference via Ollama
    print("Triggering Deconstruction & Planning Agent (Node 1)...")
    updated_state = planner_node(mock_state)
    
    # 3. Print out the structured array results
    print("\n🎯 --- AGENT EXECUTION RESULTS ---")
    print(f"Current Graph Step Pointer: {updated_state['current_step']}")
    print("Generated Sub-Queries for Qdrant Retrieval Mapping:")
    for idx, query in enumerate(updated_state["audit_plan"], 1):
        print(f"  {idx}. {query}")

if __name__ == "__main__":
    main()
