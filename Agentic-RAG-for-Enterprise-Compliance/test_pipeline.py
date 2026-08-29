import uuid

from src.agents.graph import build_compliance_graph
from src.agents.state import ComplianceState


def main() -> None:
    print("Compiling LangGraph multi-agent state machine...")
    app = build_compliance_graph()

    initial_state: ComplianceState = {
        "request_id": uuid.uuid4().hex,
        "raw_query": "Verify if our cloud vendor storage architecture breaches EU data sovereignty constraints.",
        "contract_meta": {
            "jurisdiction": "European Union",
            "document_type": "Master Services Agreement (MSA)",
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

    print("Launching state machine...\n")
    final_output = app.invoke(initial_state)

    report = final_output.get("final_compliance_report", {})
    print("\n--- FINAL MULTI-AGENT STATE GRAPH OUTPUT ---")
    print(f"Status            : {report.get('status', 'unknown')}")
    print(f"Risk score         : {report.get('risk_score', 'unknown')}")
    print(f"Jurisdiction        : {report.get('audited_jurisdiction', 'unknown')}")
    print(f"Unresolved sub-tasks: {report.get('unresolved_count', 0)}")
    print(f"Generated file     : {report.get('generated_file_path')}")
    print("-" * 50)
    print(f"Findings count      : {len(report.get('raw_findings_array', []))}")
    print("-" * 50)


if __name__ == "__main__":
    main()
