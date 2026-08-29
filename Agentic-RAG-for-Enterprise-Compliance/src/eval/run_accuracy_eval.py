"""
End-to-end accuracy evaluation against documents with known, deliberately planted
violations. Unlike run_benchmark.py (which only measures retrieval recall), this
runs the FULL audit graph on each document and checks whether the reported findings
actually caught the known violations — and flags any internal contradictions that
slipped past finalize.py's reconciliation and the consistency editor pass.
"""
import sys
import time
import uuid
from pathlib import Path

from src.agents.graph import build_compliance_graph
from src.agents.nodes.finalize import _clause_identity_key
from src.database.pdf_processor import ingest_pdf_to_qdrant

TEST_CASES = [
    {
        "pdf_path": "sample_corporate_msa.pdf",
        "document_name": "sample_corporate_msa.pdf",
        "jurisdiction": "European Union",
        "execution_year": 2026,
        "raw_query": "Perform a comprehensive regulatory compliance audit on data retention, cross-border transfer, and liability exposure.",
        "expected_violations": [
            {"keyword": "ninety", "label": "90-day EU retention breach"},
            {"keyword": "outside the european union", "label": "cross-border transfer without safeguards"},
        ],
    },
    {
        "pdf_path": "sample_employee_data_agreement.pdf",
        "document_name": "sample_employee_data_agreement.pdf",
        "jurisdiction": "European Union",
        "execution_year": 2026,
        "raw_query": "Perform a comprehensive regulatory compliance audit on employee data sharing consent and breach notification obligations.",
        "expected_violations": [
            {"keyword": "biometric", "label": "biometric data shared without consent"},
            {"keyword": "notif", "label": "undefined breach notification timeline"},
        ],
    },
]


def _run_case(case: dict) -> dict:
    pdf_path = Path(case["pdf_path"])
    if not pdf_path.exists():
        return {"skipped": True, "reason": f"{pdf_path} not found — generate it first."}

    print(f"\n{'=' * 70}\nEvaluating: {case['document_name']}\n{'=' * 70}")
    ingest_pdf_to_qdrant(
        file_path=str(pdf_path),
        document_name=case["document_name"],
        jurisdiction=case["jurisdiction"],
        execution_year=case["execution_year"],
    )

    graph = build_compliance_graph()
    initial_state = {
        "request_id": uuid.uuid4().hex,
        "raw_query": case["raw_query"],
        "contract_meta": {
            "jurisdiction": case["jurisdiction"],
            "document_name": case["document_name"],
            "execution_year": case["execution_year"],
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

    start = time.time()
    final_state = graph.invoke(initial_state)
    elapsed = time.time() - start

    findings = final_state.get("validated_drafts", [])
    report = final_state.get("final_compliance_report", {})

    # Did each expected violation get flagged (NON_COMPLIANT/UNVERIFIED_EVIDENCE) by
    # at least one finding whose quote or analysis mentions the expected keyword?
    caught = []
    for expected in case["expected_violations"]:
        kw = expected["keyword"].lower()
        hit = any(
            kw in (str(f.get("evidence_quote", "")) + str(f.get("analysis", ""))).lower()
            and f.get("finding_status") in ("NON_COMPLIANT", "UNVERIFIED_EVIDENCE")
            for f in findings
        )
        caught.append({"label": expected["label"], "caught": hit})

    # Did any finding contradict another about the same underlying clause? Should be
    # zero given finalize.py's reconciliation + the consistency editor — a non-zero
    # count here is a real reconciliation gap, not just a benign duplicate.
    by_key: dict[str, set[str]] = {}
    for f in findings:
        key = _clause_identity_key(f)
        if not key:
            continue
        by_key.setdefault(key, set()).add(str(f.get("finding_status", "UNKNOWN")))
    contradictions = sum(1 for statuses in by_key.values() if len(statuses) > 1)

    return {
        "skipped": False,
        "elapsed_seconds": round(elapsed, 1),
        "total_findings": len(findings),
        "expected_violations": caught,
        "contradictions": contradictions,
        "report_status": report.get("status"),
        "risk_score": report.get("risk_score"),
    }


def main() -> None:
    results = [_run_case(case) for case in TEST_CASES]

    print(f"\n{'=' * 70}\nACCURACY EVAL SUMMARY\n{'=' * 70}")
    all_passed = True
    for case, result in zip(TEST_CASES, results):
        if result.get("skipped"):
            print(f"\n{case['document_name']}: SKIPPED ({result['reason']})")
            continue

        print(
            f"\n{case['document_name']} ({result['elapsed_seconds']}s, "
            f"{result['total_findings']} findings, risk={result['risk_score']})"
        )
        for v in result["expected_violations"]:
            status = "CAUGHT" if v["caught"] else "MISSED"
            if not v["caught"]:
                all_passed = False
            print(f"  [{status}] {v['label']}")
        contradiction_flag = "OK" if result["contradictions"] == 0 else f"FOUND {result['contradictions']}"
        if result["contradictions"] > 0:
            all_passed = False
        print(f"  [Contradictions: {contradiction_flag}]")

    print(f"\n{'=' * 70}")
    print("OVERALL: PASS" if all_passed else "OVERALL: FAIL — see MISSED/contradiction lines above")
    print(f"{'=' * 70}")
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
