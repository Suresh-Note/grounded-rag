export const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export type FindingStatus = "COMPLIANT" | "NON_COMPLIANT" | "UNVERIFIED_EVIDENCE";

export interface EvidenceLocation {
  document_name: string;
  page_number: number;
  chunk_hash: string;
  bbox?: Record<string, number>;
  offset_start?: number;
  offset_end?: number;
}

export interface Finding {
  rule_id: string;
  parameter: string;
  finding_status: FindingStatus;
  evidence_quote: string;
  evidence_location: EvidenceLocation;
  analysis: string;
  confidence: number;
  risk_score: number;
  unresolved_after_retries?: boolean;
  reconciled_conflict?: boolean;
  remediation?: string;
}

export interface JobReport {
  status: string;
  risk_score: number;
  audited_jurisdiction: string;
  critic_evaluation: string;
  unresolved_count: number;
  request_id: string;
  document_type: string;
  generated_at: string;
  raw_findings_array: Finding[];
  generated_file_path: string | null;
  generation_error: string | null;
}

export interface JobState {
  job_id: string;
  stage: string;
  progress_percent: number;
  verified_findings_count: number;
  status: "pending" | "queued" | "running" | "completed" | "failed" | string;
  last_message: string;
  payload: {
    document_name?: string;
    jurisdiction?: string;
    execution_year?: number;
    report_path?: string | null;
    validated_drafts?: Finding[];
    job_report?: JobReport;
    error?: string;
  };
}

export interface AuditJobResponse {
  job_id: string;
  document_name: string;
  status_url: string;
  stream_url: string;
  download_url: string;
}

export async function submitAudit(
  file: File,
  rawQuery: string,
  jurisdiction: string,
  executionYear: number
): Promise<AuditJobResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("raw_query", rawQuery);
  formData.append("jurisdiction", jurisdiction);
  formData.append("execution_year", String(executionYear));

  const res = await fetch(`${API_BASE}/api/v1/audit/file`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Audit submission failed (${res.status}).`);
  }
  return res.json();
}

export async function getJobState(jobId: string): Promise<JobState> {
  const res = await fetch(`${API_BASE}/api/v1/audit/${jobId}`);
  if (!res.ok) throw new Error(`Failed to fetch job state (${res.status}).`);
  return res.json();
}

export function getDownloadUrl(jobId: string): string {
  return `${API_BASE}/api/v1/audit/${jobId}/download`;
}

export function getStreamUrl(jobId: string): string {
  return `${API_BASE}/api/v1/audit/stream/${jobId}`;
}
