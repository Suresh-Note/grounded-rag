from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

class FindingStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNVERIFIED_EVIDENCE = "UNVERIFIED_EVIDENCE"

class EvidenceLocation(BaseModel):
    document_name: str = Field(..., description="Document filename where evidence was found.")
    page_number: int = Field(..., description="Page number for evidence quote.")
    chunk_hash: str = Field(..., description="SHA-256 hash of source chunk.")
    bbox: dict[str, float] = Field(default_factory=dict, description="Bounding box coords.")
    offset_start: int = Field(0, description="Start offset.")
    offset_end: int = Field(0, description="End offset.")

class ComplianceFinding(BaseModel):
    rule_id: str = Field(..., description="Rule or clause ID.")
    parameter: str = Field(..., description="Parameter under review.")
    finding_status: FindingStatus = Field(..., description="Compliance verdict.")
    evidence_quote: str = Field(..., description="Exact verbatim quote.")
    evidence_location: EvidenceLocation = Field(..., description="Location metadata.")
    analysis: str = Field(..., description="Analysis grounded in quote.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score.")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Risk score.")

class AuditorOutput(BaseModel):
    findings: list[ComplianceFinding] = Field(default_factory=list)

class CriticVerification(BaseModel):
    passed: bool = Field(..., description="True if grounded.")
    issues: list[str] = Field(default_factory=list, description="Itemized failure reasons.")
    feedback: str = Field(..., description="Correction instructions.")

class AuditPlan(BaseModel):
    sub_queries: list[str] = Field(..., description="Search sub-queries.")

class AuditReportMetadata(BaseModel):
    job_id: str = Field(..., description="Unique job ID.")
    jurisdiction: str = Field(..., description="Target jurisdiction.")
    document_name: str = Field(..., description="Source document name.")
    execution_year: int = Field(..., description="Evaluation year.")
    generated_at: str = Field(..., description="Timestamp.")
    document_sha256: str = Field(..., description="SHA-256 fingerprint.")
