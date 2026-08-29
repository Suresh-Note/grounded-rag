from __future__ import annotations
import json
import queue
import threading
from typing import Any
import requests
import streamlit as st

API_BASE_URL = "http://localhost:8000/api/v1"
INGEST_URL = f"{API_BASE_URL}/ingest"
AUDIT_URL = f"{API_BASE_URL}/audit"
STREAM_URL_TEMPLATE = f"{API_BASE_URL}/audit/stream/{{job_id}}"
DOWNLOAD_URL_TEMPLATE = f"{API_BASE_URL}/audit/{{job_id}}/download"

def initialize_session() -> None:
    if "job_id" not in st.session_state:
        st.session_state.job_id = ""
    if "job_events" not in st.session_state:
        st.session_state.job_events = []
    if "stream_queue" not in st.session_state:
        st.session_state.stream_queue = queue.Queue()
    if "stream_thread" not in st.session_state:
        st.session_state.stream_thread = None
    if "last_error" not in st.session_state:
        st.session_state.last_error = ""
    if "report_ready" not in st.session_state:
        st.session_state.report_ready = False
    if "job_status" not in st.session_state:
        st.session_state.job_status = "idle"

def start_stream_listener(job_id: str, event_queue: queue.Queue) -> None:
    if not job_id:
        return

    def _listen(q: queue.Queue) -> None:
        url = STREAM_URL_TEMPLATE.format(job_id=job_id)
        try:
            with requests.get(url, stream=True, timeout=300) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    if isinstance(line, bytes):
                        line = line.decode("utf-8", errors="ignore")
                    if line.startswith("data:"):
                        payload = line[len("data:"):].strip()
                        try:
                            event = json.loads(payload)
                            q.put(event)
                            if event.get("status") in {"completed", "failed"}:
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as exc:
            q.put({
                "stage": "stream_error",
                "progress_percent": 0,
                "status": "error",
                "last_message": f"Stream error: {exc}",
            })

    thread = threading.Thread(target=_listen, args=(event_queue,), daemon=True)
    thread.start()

def drain_event_queue() -> None:
    while not st.session_state.stream_queue.empty():
        try:
            event = st.session_state.stream_queue.get_nowait()
            st.session_state.job_events.append(event)
            if event.get("status") == "completed":
                st.session_state.report_ready = True
            if event.get("stage") == "failed":
                st.session_state.job_status = "failed"
            elif event.get("stage") == "completed":
                st.session_state.job_status = "completed"
            elif event.get("status") == "running":
                st.session_state.job_status = "running"
        except queue.Empty:
            break

def submit_audit_job(raw_query: str, jurisdiction: str, document_name: str, execution_year: int, max_retries: int, pdf_bytes: bytes) -> str:
    clean_filename = document_name.strip()
    if not clean_filename.lower().endswith(".pdf"):
        clean_filename = f"{clean_filename}.pdf"

    files = {"file": (clean_filename, pdf_bytes, "application/pdf")}
    data = {"jurisdiction": jurisdiction, "execution_year": str(execution_year)}

    ingest_response = requests.post(INGEST_URL, files=files, data=data, timeout=180)
    ingest_response.raise_for_status()

    audit_payload = {
        "raw_query": raw_query,
        "jurisdiction": jurisdiction,
        "document_name": clean_filename,
        "execution_year": execution_year,
        "max_retries": max_retries,
    }
    audit_response = requests.post(AUDIT_URL, json=audit_payload, timeout=60)
    audit_response.raise_for_status()
    return audit_response.json()["job_id"]

def format_stage_card(event: dict[str, Any]) -> str:
    badge = event.get("status", "running").upper()
    color = "#10B981" if badge == "COMPLETED" else "#F59E0B" if badge in {"FAILED", "ERROR"} else "#F97316"
    return (
        f"<div class='stage-card'><div class='stage-title'>Stage: {event.get('stage', 'unknown')}</div>"
        f"<div class='stage-metadata'>Status: <span style='color:{color}; font-weight:700;'>{badge}</span> | Progress: {event.get('progress_percent', 0):.0f}%</div>"
        f"<div class='message'>{event.get('last_message', 'No message')}</div></div>"
    )

def render_findings(events: list[dict[str, Any]]) -> None:
    findings: list[dict[str, Any]] = []
    for event in reversed(events):
        payload = event.get("payload", {})
        report = payload.get("job_report")
        if report and isinstance(report, dict):
            findings = report.get("raw_findings_array", [])
            break

    if not findings:
        st.info("No finalized findings are available yet.")
        return

    for finding in findings:
        status = finding.get("finding_status", "UNVERIFIED_EVIDENCE")
        color = "#DCFCE7" if status == "COMPLIANT" else "#FECACA" if status == "NON_COMPLIANT" else "#FEF3C7"
        border = "#22C55E" if status == "COMPLIANT" else "#EF4444" if status == "NON_COMPLIANT" else "#F59E0B"

        st.markdown(
            f"<div class='finding-card' style='background:{color}; border-left:4px solid {border};'>"
            f"<div class='finding-title'>{finding.get('rule_id', 'Unnamed Rule')} - {status}</div>"
            f"<div class='finding-detail'>{finding.get('analysis', '')}</div>"
            f"<div class='finding-meta'><strong>Evidence:</strong> {finding.get('evidence_quote', '')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

def render_download_link(job_id: str) -> None:
    url = DOWNLOAD_URL_TEMPLATE.format(job_id=job_id)
    st.markdown(f"<a href='{url}' target='_blank' class='download-btn'>Download Executive PDF Report</a>", unsafe_allow_html=True)

initialize_session()
st.set_page_config(page_title="Aegis Executive Dashboard", page_icon="🛡️", layout="wide")

st.markdown("<div class='dashboard-header'>Aegis Audit Control Tower</div>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Audit Control Panel")
    jurisdiction = st.selectbox("Jurisdiction", ["European Union", "United States", "United Kingdom", "Global Framework Standard"])
    document_name = st.text_input("Document Name", value="Uploaded Contract Document.pdf")
    execution_year = st.number_input("Execution Year", min_value=2020, max_value=2035, value=2026)
    max_retries = st.slider("Max Critic Retries", min_value=1, max_value=5, value=2)
    raw_query = st.text_area("Audit Objective", value="Identify any clauses that violate data sovereignty or retention policy requirements.", height=160)
    uploaded_file = st.file_uploader("Upload Contract PDF", type=["pdf"])
    if st.button("Launch Audit Run"):
        if not raw_query.strip():
            st.session_state.last_error = "An audit objective is required."
        elif uploaded_file is None:
            st.session_state.last_error = "Please upload a contract PDF."
        else:
            try:
                st.session_state.last_error = ""
                pdf_bytes = uploaded_file.read()
                job_id = submit_audit_job(
                    raw_query=raw_query,
                    jurisdiction=jurisdiction,
                    document_name=document_name or uploaded_file.name,
                    execution_year=int(execution_year),
                    max_retries=int(max_retries),
                    pdf_bytes=pdf_bytes,
                )
                st.session_state.job_id = job_id
                st.session_state.job_events = []
                st.session_state.report_ready = False
                start_stream_listener(job_id, st.session_state.stream_queue)
                st.rerun()
            except Exception as exc:
                st.session_state.last_error = f"Audit launch failed: {exc}"

if st.session_state.last_error:
    st.error(st.session_state.last_error)

if st.session_state.job_id:
    drain_event_queue()
    st.markdown(f"### Active Job ID: {st.session_state.job_id}")
    latest = st.session_state.job_events[-1] if st.session_state.job_events else {}
    progress = latest.get("progress_percent", 0)
    st.progress(min(max(progress / 100.0, 0.0), 1.0))
    for event in st.session_state.job_events[-8:]:
        st.markdown(format_stage_card(event), unsafe_allow_html=True)
    st.subheader("Verified Findings Preview")
    render_findings(st.session_state.job_events)
    if st.session_state.report_ready:
        render_download_link(st.session_state.job_id)
else:
    st.info("Upload a PDF and launch an audit run to begin.")
