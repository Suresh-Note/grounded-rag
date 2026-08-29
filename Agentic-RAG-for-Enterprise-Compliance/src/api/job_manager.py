from __future__ import annotations

import logging
import uuid
from typing import Any

from src.api.tasks import execute_audit_job
from src.config import get_settings
from src.state.store import JobState, get_state_store

logger = logging.getLogger("aegis.job_manager")
settings = get_settings()


class AuditJobManager:
    def __init__(self) -> None:
        self.state_store = get_state_store()

    def _build_initial_state(
        self,
        request_id: str,
        raw_query: str,
        jurisdiction: str,
        document_name: str,
        execution_year: int,
        max_retries: int,
    ) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "raw_query": raw_query,
            "contract_meta": {
                "jurisdiction": jurisdiction,
                "document_name": document_name,
                "execution_year": execution_year,
            },
            "audit_plan": [],
            "current_step": 0,
            "retry_count": 0,
            "max_retries": max_retries,
            "current_context": [],
            "retrieved_contexts": [],
            "current_findings": [],
            "validated_drafts": [],
            "critic_feedback": None,
            "verification_passed": False,
            "final_compliance_report": {},
        }

    def submit_job(
        self,
        raw_query: str,
        jurisdiction: str,
        document_name: str,
        execution_year: int,
        max_retries: int,
    ) -> str:
        job_id = uuid.uuid4().hex
        initial_state = self._build_initial_state(
            request_id=job_id,
            raw_query=raw_query,
            jurisdiction=jurisdiction,
            document_name=document_name,
            execution_year=execution_year,
            max_retries=max_retries,
        )

        self.state_store.save_state(
            JobState(
                job_id=job_id,
                stage="queued",
                progress_percent=0.0,
                verified_findings_count=0,
                status="pending",
                last_message="Audit job accepted and enqueued into Celery.",
                payload={
                    "document_name": document_name,
                    "jurisdiction": jurisdiction,
                    "execution_year": execution_year,
                },
            )
        )

        execute_audit_job.apply_async(args=[job_id, initial_state], task_id=job_id)
        logger.info("Successfully enqueued job %s to Celery Redis broker", job_id)
        return job_id

    def get_job_state(self, job_id: str) -> JobState | None:
        return self.state_store.load_state(job_id)


job_manager = AuditJobManager()
