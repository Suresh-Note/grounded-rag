from __future__ import annotations

import json
import logging
import time
from datetime import timedelta
from typing import Any

import redis
from pydantic import BaseModel, Field

from src.config import get_settings

logger = logging.getLogger("aegis.state")
settings = get_settings()


class JobState(BaseModel):
    job_id: str = Field(..., description="Unique audit job identifier.")
    stage: str = Field(..., description="Current processing stage.")
    progress_percent: float = Field(..., ge=0.0, le=100.0, description="Completion percentage.")
    verified_findings_count: int = Field(..., description="Number of confirmed verified findings.")
    status: str = Field(..., description="Job status label.")
    last_message: str = Field(..., description="Human-readable status message.")
    payload: dict[str, Any] = Field(default_factory=dict, description="Optional job payload or metadata.")


class StateStore:
    def __init__(self) -> None:
        self._use_memory = False
        self._ttl = timedelta(seconds=settings.STATE_TTL_SECONDS)
        try:
            self._client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self._client.ping()
            self._memory: dict[str, tuple[str, float]] = {}
        except Exception as exc:
            logger.warning(
                "Redis unavailable for state persistence (%s); falling back to in-memory state store.",
                exc,
            )
            self._client = None
            self._use_memory = True
            self._memory = {}

    def save_state(self, state: JobState) -> None:
        payload = json.dumps(state.model_dump())
        if self._use_memory or self._client is None:
            self._memory[state.job_id] = (payload, time.time())
            logger.debug("Saved job state in-memory for %s", state.job_id)
            return

        try:
            self._client.set(name=self._redis_key(state.job_id), value=payload, ex=int(self._ttl.total_seconds()))
            logger.debug("Saved job state for %s", state.job_id)
        except Exception as exc:
            logger.warning(
                "Redis state save failed for %s; falling back to in-memory store: %s",
                state.job_id,
                exc,
            )
            self._use_memory = True
            self._memory[state.job_id] = (payload, 0.0)

    def load_state(self, job_id: str) -> JobState | None:
        if self._use_memory or self._client is None:
            cached = self._memory.get(job_id)
            if not cached:
                return None
            payload, _ = cached
            raw = json.loads(payload)
            return JobState.model_validate(raw)

        try:
            payload = self._client.get(self._redis_key(job_id))
            if not payload:
                return None
            raw = json.loads(payload)
            return JobState.model_validate(raw)
        except Exception as exc:
            logger.warning("Failed to load job state for %s from Redis; using empty result: %s", job_id, exc)
            return None

    def _redis_key(self, job_id: str) -> str:
        return f"aegis:job_state:{job_id}"


_state_store: StateStore | None = None


def get_state_store() -> StateStore:
    global _state_store
    if _state_store is None:
        _state_store = StateStore()
    return _state_store
