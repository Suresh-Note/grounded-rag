from __future__ import annotations

import logging
from typing import Any

from celery.exceptions import MaxRetriesExceededError

from src.api.celery_app import celery_app
from src.agents.graph import build_compliance_graph
from src.events.broadcaster import broadcaster
from src.state.store import JobState, get_state_store

logger = logging.getLogger("aegis.tasks")


@celery_app.task(
    bind=True,
    name="src.api.tasks.execute_audit_job",
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def execute_audit_job(self, job_id: str, initial_state: dict[str, Any]) -> None:
    state_store = get_state_store()
    try:
        logger.info("Starting Celery audit execution for job %s", job_id)
        state_store.save_state(
            JobState(
                job_id=job_id,
                stage="running",
                progress_percent=5.0,
                verified_findings_count=0,
                status="running",
                last_message="Audit task started and is executing.",
                payload={"job_id": job_id, "request_state": initial_state},
            )
        )
        broadcaster.publish_sync(job_id, state_store.load_state(job_id).model_dump())

        graph = build_compliance_graph()
        final_state = graph.invoke(initial_state)
        report = final_state.get("final_compliance_report", {})

        if not report:
            raise RuntimeError("Audit graph execution completed without producing a report.")

        findings = (
            report.get("validated_drafts")
            or report.get("raw_findings_array")
            or final_state.get("validated_drafts", [])
        )

        completed_state = JobState(
            job_id=job_id,
            stage="completed",
            progress_percent=100.0,
            verified_findings_count=len(findings),
            status="completed",
            last_message="Audit completed successfully.",
            payload={
                "report_path": report.get("generated_file_path"),
                "validated_drafts": findings,
                "job_report": report,
            },
        )
        state_store.save_state(completed_state)
        broadcaster.publish_sync(job_id, completed_state.model_dump())
    except MaxRetriesExceededError as exc:
        logger.exception("Audit job %s failed after max retries: %s", job_id, exc)
        failed_state = JobState(
            job_id=job_id,
            stage="failed",
            progress_percent=100.0,
            verified_findings_count=0,
            status="failed",
            last_message="Audit failed after retry exhaustion.",
            payload={"error": str(exc)},
        )
        state_store.save_state(failed_state)
        broadcaster.publish_sync(job_id, failed_state.model_dump())
        raise
    except Exception as exc:
        logger.exception("Audit job %s encountered an error: %s", job_id, exc)
        try:
            countdown = min(2 ** (self.request.retries + 1) * 10, 300)
            raise self.retry(exc=exc, countdown=countdown)
        except MaxRetriesExceededError:
            failed_state = JobState(
                job_id=job_id,
                stage="failed",
                progress_percent=100.0,
                verified_findings_count=0,
                status="failed",
                last_message=str(exc),
                payload={"error": str(exc)},
            )
            state_store.save_state(failed_state)
            broadcaster.publish_sync(job_id, failed_state.model_dump())
            raise