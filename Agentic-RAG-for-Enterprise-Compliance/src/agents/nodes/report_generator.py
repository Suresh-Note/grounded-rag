import logging
from datetime import datetime

from src.agents.state import ComplianceState
from src.config import get_settings
from src.inference.gateway import safe_inference_target
from src.utils.pdf_report import build_compliance_pdf

logger = logging.getLogger("aegis.report_generator")
settings = get_settings()


def report_generator_node(state: ComplianceState) -> dict:
    """
    Node 6: Executive Report Compiler Engine.
    """
    target = safe_inference_target()
    logger.info(
        "Executing NODE 6: Report Generator Engine Cluster. Inference target=%s device=%s",
        target.model_name,
        target.device,
    )

    meta = state.get("contract_meta", {})
    drafts = state.get("validated_drafts", [])
    request_id = state.get("request_id", "unknown")
    critic_feedback_fallback = state.get("critic_feedback", "Evaluated via runtime safety pass rules.")

    # 1. Safely serialize Pydantic structural objects to raw dict arrays
    processed_findings = []
    for f in drafts:
        if hasattr(f, "model_dump"):
            f_dict = f.model_dump()
        elif hasattr(f, "__dict__"):
            f_dict = f.__dict__
        else:
            f_dict = dict(f)
        
        # Ensure finding_status is stringified if it's an Enum
        if f_dict.get("finding_status") and hasattr(f_dict["finding_status"], "value"):
            f_dict["finding_status"] = f_dict["finding_status"].value
            
        processed_findings.append(f_dict)

    has_findings = len(processed_findings) > 0
    verification_passed = state.get("verification_passed", False)
    unresolved_detected = not verification_passed and state.get("retry_count", 0) >= state.get("max_retries", 2)

    # 2. Risk Metrics Matrix Compute
    risk_score = 10
    if has_findings:
        risk_score = 75
    if unresolved_detected:
        risk_score = max(risk_score, 85)

    status = "COMPLETED_CLEAN"
    if has_findings or unresolved_detected:
        status = "COMPLETED_WITH_RISKS"

    # 3. Formulate pure data package with a strict explicit schema contract
    report_payload = {
        "status": status,
        "risk_score": risk_score,
        "audited_jurisdiction": meta.get("jurisdiction", "Global Framework Standard"),
        "critic_evaluation": f"Global Loop Audit Assessment Verdict: {critic_feedback_fallback}",
        "unresolved_count": 1 if unresolved_detected else 0,
        "request_id": request_id,
        "document_type": meta.get("document_type", "Master Services Agreement (MSA)"),
        "generated_at": datetime.now().strftime("%B %d, %Y"),
        "raw_findings_array": processed_findings  # Exclusively passing the clean dict array
    }

    output_path = f"{settings.ARTIFACTS_DIR}/{request_id}_Aegis_Compliance_Audit.pdf"

    try:
        logger.info("Serializing analytics dictionary directly to output target binary space: %s", output_path)
        final_path = build_compliance_pdf(report_payload, output_path)
        report_payload["generated_file_path"] = final_path
        report_payload["generation_error"] = None
    except Exception as exc:
        logger.error("PDF engine compiler encountered a terminal file serialization exception: %s", exc, exc_info=True)
        report_payload["status"] = "GENERATION_ERROR"
        report_payload["generated_file_path"] = None
        report_payload["generation_error"] = str(exc)

    return {"final_compliance_report": report_payload}