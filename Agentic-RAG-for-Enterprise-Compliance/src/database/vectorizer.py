from __future__ import annotations

import hashlib
import logging
import uuid

from langchain_ollama import OllamaEmbeddings
from qdrant_client.http import models

from src.config import get_settings
from src.database.qdrant_wrapper import get_db_client

logger = logging.getLogger("aegis.vectorizer")
settings = get_settings()


def get_embedding_engine() -> OllamaEmbeddings:
    return OllamaEmbeddings(base_url=settings.OLLAMA_BASE_URL, model=settings.LOCAL_EMBED_MODEL)


def _validate_dim(vector: list[float]) -> list[float]:
    if len(vector) != settings.EMBEDDING_DIM:
        raise RuntimeError(
            f"Embedding model returned {len(vector)} dims, expected {settings.EMBEDDING_DIM}. "
            "Update EMBEDDING_DIM (and recreate the Qdrant collection) to match your embedding model — "
            "never truncate or zero-pad an embedding vector."
        )
    return vector


def chunk_and_upload_text(text: str, document_name: str, jurisdiction: str, execution_year: int) -> None:
    """Chunks raw text, embeds each paragraph, and upserts into Qdrant."""
    client = get_db_client()
    embeddings = get_embedding_engine()
    collection_name = settings.COMPLIANCE_COLLECTION_NAME

    logger.info("Embedding pipeline starting for '%s'", document_name)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    points = []
    for idx, chunk in enumerate(paragraphs):
        logger.info("Vectorizing chunk [%s/%s]", idx + 1, len(paragraphs))
        vector = _validate_dim(embeddings.embed_query(chunk))
        points.append(
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    # Flat schema — must match src/database/pdf_processor.py exactly,
                    # since src/retrieval/hybrid_retriever.py reads these keys at the
                    # top level, not nested under "metadata".
                    "text": chunk,
                    "document_name": document_name,
                    "jurisdiction": jurisdiction,
                    "year": execution_year,
                    "page_number": 0,
                    "section_label": "Operative Clause",
                    "chunk_hash": hashlib.sha256(chunk.encode("utf-8")).hexdigest(),
                    "chunk_index": idx,
                },
            )
        )

    if points:
        client.upsert(collection_name=collection_name, points=points)
    logger.info("Uploaded %s vector chunks for '%s'", len(points), document_name)
