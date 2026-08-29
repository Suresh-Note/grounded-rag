from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, AsyncGenerator

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from src.api.job_manager import job_manager
from src.config import get_settings
from src.database.pdf_processor import ingest_pdf_to_qdrant
from src.database.qdrant_wrapper import initialize_compliance_collection
from src.events.broadcaster import broadcaster

logger = logging.getLogger("aegis.api")
settings = get_settings()


async def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """
    Gated only when settings.API_KEY is actually configured, so local/dev use
    is unaffected by default — set API_KEY in the environment to lock this down.
    """
    if not settings.API_KEY:
        return
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key.")


async def _save_upload_with_limit(file: UploadFile, tmp) -> None:
    """Streams the upload to disk in chunks, rejecting it once it exceeds MAX_UPLOAD_SIZE_MB
    instead of buffering an unbounded file into memory/disk first."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total = 0
    chunk_size = 1024 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"File exceeds the maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB} MB.",
            )
        tmp.write(chunk)


def cleanup_stale_artifacts() -> None:
    artifacts_dir = Path(settings.ARTIFACTS_DIR)
    if not artifacts_dir.exists():
        return
    cutoff = time.time() - settings.ARTIFACT_RETENTION_DAYS * 86400
    removed = 0
    for pdf_path in artifacts_dir.glob("*.pdf"):
        try:
            if pdf_path.stat().st_mtime < cutoff:
                pdf_path.unlink()
                removed += 1
        except OSError:
            continue
    if removed:
        logger.info("Cleaned up %s stale artifact PDF(s) older than %s days.", removed, settings.ARTIFACT_RETENTION_DAYS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Production Application Lifespan:
    Executes mandatory startup routines (Qdrant collection creation)
    and graceful shutdown cleanup.
    """
    logger.info("🚀 Booting GroundedRAG API Gateway...")
    try:
        await asyncio.to_thread(initialize_compliance_collection)
        logger.info("✅ Qdrant Compliance Collection verified and ready.")
    except Exception as exc:
        logger.error("❌ Failed initializing Qdrant vector index: %s", exc)
    await asyncio.to_thread(cleanup_stale_artifacts)
    yield
    logger.info("🛑 Shutting down Aegis API Gateway...")


app = FastAPI(
    title="GroundedRAG — Multi-Agent RAG with Hallucination Mitigation",
    description="Multi-Agent LangGraph RAG Engine with Actor-Critic Verification & RRF Hybrid Search",
    version="2.4.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


class AuditRequest(BaseModel):
    raw_query: str = Field(..., example="Audit contract for GDPR Chapter V cross-border transfer violations.")
    jurisdiction: str = Field("European Union", example="European Union")
    document_name: str = Field(..., example="Uploaded_Contract.pdf")
    execution_year: int = Field(2026)
    max_retries: int = Field(default=settings.MAX_AUDIT_RETRIES)


@app.get("/health", tags=["System"])
async def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "engine_version": "v2.4-Agentic",
        "rrf_retriever": "active",
        "critic_guardrail": "enabled",
    }


@app.post("/api/v1/ingest", tags=["Ingestion"], dependencies=[Depends(require_api_key)])
async def ingest_document(
    file: UploadFile = File(...),
    jurisdiction: str = Form("European Union"),
    execution_year: int = Form(2026),
) -> dict[str, Any]:
    """
    Direct Vector Document Ingestion Endpoint.
    Parses PDF chunks, extracts structural metadata, and embeds into Qdrant vector space.
    """
    filename = file.filename or "uploaded_contract.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format: Only PDF files are supported.",
        )

    tmp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            await _save_upload_with_limit(file, tmp)

        await asyncio.to_thread(
            ingest_pdf_to_qdrant,
            file_path=tmp_path,
            document_name=filename,
            jurisdiction=jurisdiction,
            execution_year=execution_year,
        )
        return {
            "status": "ingested",
            "document": filename,
            "jurisdiction": jurisdiction,
            "execution_year": execution_year,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Ingestion failed for %s: %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document ingestion failed: {exc}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


@app.post("/api/v1/audit/file", tags=["Audit Workflow"], dependencies=[Depends(require_api_key)])
async def upload_and_audit_atomic(
    file: UploadFile = File(...),
    raw_query: str = Form("Perform a comprehensive regulatory compliance audit on data retention, transfer, and liability."),
    jurisdiction: str = Form("European Union"),
    execution_year: int = Form(2026),
) -> JSONResponse:
    """
    Atomic All-In-One Enterprise Audit Endpoint.
    Ingests the contract PDF into Qdrant and submits the Celery Async Multi-Agent Audit job in a single call.
    """
    filename = file.filename or "uploaded_contract.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported format: Only PDF files are supported.",
        )

    # 1. Ingest PDF
    tmp_path = None
    try:
        with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp_path = tmp.name
            await _save_upload_with_limit(file, tmp)

        await asyncio.to_thread(
            ingest_pdf_to_qdrant,
            file_path=tmp_path,
            document_name=filename,
            jurisdiction=jurisdiction,
            execution_year=execution_year,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Atomic ingestion failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed during atomic audit trigger: {exc}",
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # 2. Submit Audit Job
    job_id = job_manager.submit_job(
        raw_query=raw_query,
        jurisdiction=jurisdiction,
        document_name=filename,
        execution_year=execution_year,
        max_retries=settings.MAX_AUDIT_RETRIES,
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "job_id": job_id,
            "document_name": filename,
            "status_url": f"/api/v1/audit/{job_id}",
            "stream_url": f"/api/v1/audit/stream/{job_id}",
            "download_url": f"/api/v1/audit/{job_id}/download",
        },
    )


@app.post("/api/v1/audit", tags=["Audit Workflow"], dependencies=[Depends(require_api_key)])
async def execute_compliance_audit(payload: AuditRequest) -> JSONResponse:
    """
    Submit an Audit Job on a previously ingested document name.
    """
    job_id = job_manager.submit_job(
        raw_query=payload.raw_query,
        jurisdiction=payload.jurisdiction,
        document_name=payload.document_name,
        execution_year=payload.execution_year,
        max_retries=payload.max_retries,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "job_id": job_id,
            "status_url": f"/api/v1/audit/{job_id}",
            "stream_url": f"/api/v1/audit/stream/{job_id}",
            "download_url": f"/api/v1/audit/{job_id}/download",
        },
    )


@app.get("/api/v1/audit/{job_id}", tags=["Audit Workflow"], dependencies=[Depends(require_api_key)])
async def get_audit_status(job_id: str) -> dict[str, Any]:
    """
    Retrieve real-time state and findings for a specific job ID.
    """
    state = job_manager.get_job_state(job_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found.")
    return state.model_dump()


@app.get("/api/v1/audit/stream/{job_id}", tags=["Live Telemetry Stream"])
async def stream_audit_events(job_id: str) -> StreamingResponse:
    """
    Server-Sent Events (SSE) Streaming Endpoint.
    Pushes real-time agent execution state transitions to frontend 3D visualizers.
    """
    state = job_manager.get_job_state(job_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found.")

    async def sse_event_generator() -> AsyncGenerator[str, None]:
        # broadcaster.stream() already yields fully-formatted "data: {...}\n\n"
        # SSE lines — wrapping them again here would double-prefix every event.
        async for raw_event in broadcaster.stream(job_id):
            yield raw_event

    return StreamingResponse(
        sse_event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Prevents Nginx/Proxy buffering
        },
    )


@app.get("/api/v1/audit/{job_id}/download", tags=["Audit Deliverables"], dependencies=[Depends(require_api_key)])
async def download_audit_report(job_id: str) -> FileResponse:
    """
    Download the generated ReportLab PDF audit ledger.
    """
    state = job_manager.get_job_state(job_id)
    if not state:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit job not found.")

    report_path = state.payload.get("report_path")
    if not report_path or not os.path.exists(report_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit PDF report generation is still in progress or failed.",
        )

    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=os.path.basename(report_path),
    )