from __future__ import annotations

import json
import os
from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    COMPLIANCE_COLLECTION_NAME: str = "aegis_compliance_idx"

    LLM_BACKEND: str = "ollama"
    EMBEDDING_BACKEND: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LOCAL_LLM_MODEL: str = "llama3.2:3b"
    LOCAL_EMBED_MODEL: str = "nomic-embed-text"
    LOCAL_TORCH_LLM_MODEL: str | None = None
    LOCAL_TORCH_EMBED_MODEL: str | None = None
    USE_LOCAL_TORCH_INFERENCE: bool = False
    CROSS_ENCODER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    FORCE_CPU_INFERENCE: bool = False
    REDIS_URL: str = DEFAULT_REDIS_URL
    CELERY_BROKER_URL: str = DEFAULT_REDIS_URL
    CELERY_RESULT_BACKEND: str = DEFAULT_REDIS_URL

    EMBEDDING_DIM: int = 768
    MAX_AUDIT_RETRIES: int = 2
    RETRIEVAL_TOP_K: int = 5
    RERANK_TOP_K: int = 5
    TOKEN_OVERLAP_FALLBACK_THRESHOLD: float = 0.25

    ALLOWED_ORIGINS: list[str] | str = ["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:8000"]
    ARTIFACTS_DIR: str = "artifacts"
    STATE_TTL_SECONDS: int = 86400
    PDF_CHUNK_SIZE: int = 900
    PDF_CHUNK_OVERLAP: int = 150
    BACKEND_TIMEOUT_SECONDS: int = 300
    MAX_FRONTEND_RESULTS: int = 50

    MAX_UPLOAD_SIZE_MB: int = 25
    ARTIFACT_RETENTION_DAYS: int = 30
    API_KEY: str = ""

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        return ["*"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
