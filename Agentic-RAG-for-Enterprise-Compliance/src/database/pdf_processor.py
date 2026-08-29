from __future__ import annotations

import hashlib
import logging
import re
import uuid
from pathlib import Path
from typing import Any

import fitz
from pydantic import BaseModel, Field
from qdrant_client.http import models

from src.config import get_settings
from src.database.qdrant_wrapper import get_db_client
from src.database.vectorizer import get_embedding_engine

logger = logging.getLogger("aegis.pdf_processor")
settings = get_settings()


class PdfChunk(BaseModel):
    id: str = Field(..., description="Globally unique identifier for the extracted chunk.")
    document_hash: str = Field(..., description="SHA-256 hash of the source document bytes.")
    chunk_hash: str = Field(..., description="SHA-256 hash of the extracted text chunk.")
    document_name: str = Field(..., description="Original source document name.")
    jurisdiction: str = Field(..., description="Target jurisdiction metadata.")
    execution_year: int = Field(..., description="Target statutory evaluation year.")
    page_number: int = Field(..., description="Page number in the source PDF.")
    section_label: str = Field(..., description="Detected structural section label for the chunk.")
    bbox: dict[str, float] = Field(default_factory=lambda: {"x0": 0.0, "y0": 0.0, "x1": 0.0, "y1": 0.0})
    offset_start: int = Field(default=0)
    offset_end: int = Field(default=0)
    text: str = Field(..., description="The normalized chunk text content.")


def _compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _guess_section_label(text: str) -> str:
    normalized = text.strip().lower()
    if "recital" in normalized or "whereas" in normalized:
        return "Recitals"
    if "definition" in normalized:
        return "Definitions"
    if "schedule" in normalized or "annex" in normalized:
        return "Schedule"
    if "signed" in normalized or "signature" in normalized:
        return "Signature Block"
    return "Operative Clause"


# Matches the numbered clause/section headers this project's contracts actually use
# (e.g. "Clause 2.2:", "SECTION 8:", "Article 5"), so a clause never gets fragmented
# mid-sentence by a fixed-size window the way plain character chunking would.
_CLAUSE_HEADER_RE = re.compile(r"^(?:SECTION|Section|Clause|Article|ARTICLE)\s+\d+(?:\.\d+)*[:.]?\s")


def _split_by_clause_boundaries(text: str, chunk_size: int, overlap: int) -> list[str]:
    lines = text.split("\n")
    groups: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if _CLAUSE_HEADER_RE.match(line.strip()) and current:
            groups.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        groups.append(current)

    if len(groups) <= 1:
        # No recognizable clause headers on this page — fall back to plain windowing.
        return _split_text_into_chunks(text, chunk_size, overlap)

    chunks: list[str] = []
    for group_lines in groups:
        group_text = "\n".join(group_lines).strip()
        if not group_text:
            continue
        if len(group_text) <= chunk_size * 1.5:
            # Keep a whole clause together even if slightly over chunk_size —
            # a clause split mid-sentence is worse than a slightly oversized chunk.
            chunks.append(group_text)
        else:
            chunks.extend(_split_text_into_chunks(group_text, chunk_size, overlap))
    return chunks


def _locate_bbox(page: "fitz.Page", chunk_text: str) -> dict[str, float]:
    """Finds the real on-page bounding box for a chunk via PyMuPDF's text search,
    using a short prefix since search_for() matches best on short contiguous runs
    rather than long multi-line strings. Falls back to zeros if nothing is found."""
    for probe_len in (80, 30):
        probe = chunk_text.strip()[:probe_len]
        if not probe:
            continue
        try:
            rects = page.search_for(probe)
        except Exception:
            rects = []
        if rects:
            rect = rects[0]
            return {"x0": round(rect.x0, 2), "y0": round(rect.y0, 2), "x1": round(rect.x1, 2), "y1": round(rect.y1, 2)}
    return {"x0": 0.0, "y0": 0.0, "x1": 0.0, "y1": 0.0}


def _split_text_into_chunks(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        if end < len(text):
            split_at = text.rfind(" ", start, end)
            if split_at <= start:
                split_at = end
        else:
            split_at = end

        chunk = text[start:split_at].strip()
        if chunk:
            chunks.append(chunk)

        if split_at >= len(text):
            break
        start = max(split_at - overlap, start + 1)
    return chunks


def extract_pdf_chunks(file_path: str, document_name: str, jurisdiction: str, execution_year: int) -> list[PdfChunk]:
    path = Path(file_path)
    with path.open("rb") as source_file:
        raw_bytes = source_file.read()
    document_hash = _compute_sha256(raw_bytes)

    chunks: list[PdfChunk] = []
    with fitz.open(file_path) as document:
        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text("text") or ""
            lines = [line.strip() for line in page_text.splitlines() if line.strip()]
            clean_page_text = "\n".join(lines)
            
            if not clean_page_text:
                continue

            text_chunks = _split_by_clause_boundaries(clean_page_text, settings.PDF_CHUNK_SIZE, settings.PDF_CHUNK_OVERLAP)

            cursor = 0
            for chunk_str in text_chunks:
                idx = clean_page_text.find(chunk_str, cursor)
                if idx == -1:
                    idx = clean_page_text.find(chunk_str)
                if idx != -1:
                    offset_start, offset_end = idx, idx + len(chunk_str)
                    cursor = idx + 1  # allow forward progress even when windows overlap
                else:
                    offset_start = offset_end = 0

                chunks.append(
                    PdfChunk(
                        id=str(uuid.uuid4()),
                        document_hash=document_hash,
                        chunk_hash=_compute_sha256(chunk_str.encode("utf-8")),
                        document_name=document_name,
                        jurisdiction=jurisdiction,
                        execution_year=execution_year,
                        page_number=page_number,
                        section_label=_guess_section_label(chunk_str),
                        bbox=_locate_bbox(page, chunk_str),
                        offset_start=offset_start,
                        offset_end=offset_end,
                        text=chunk_str,
                    )
                )

    logger.info("Extracted %s chunks from %s.", len(chunks), document_name)
    return chunks


def ingest_pdf_to_qdrant(file_path: str, document_name: str, jurisdiction: str, execution_year: int) -> None:
    logger.info("Ingesting PDF document %s into Qdrant collection %s.", document_name, settings.COMPLIANCE_COLLECTION_NAME)

    chunks = extract_pdf_chunks(file_path, document_name, jurisdiction, execution_year)
    if not chunks:
        logger.warning("No chunks extracted from %s; skipping ingestion.", document_name)
        return

    embeddings = get_embedding_engine()
    client = get_db_client()

    # Batched embedding generation for ultra-high throughput
    chunk_texts = [c.text for c in chunks]
    if hasattr(embeddings, "embed_documents"):
        vectors = embeddings.embed_documents(chunk_texts)
    else:
        vectors = [embeddings.embed_query(t) for t in chunk_texts]

    points: list[models.PointStruct] = []
    for chunk, vector in zip(chunks, vectors):
        points.append(
            models.PointStruct(
                id=chunk.id,
                vector=vector,
                payload={
                    "text": chunk.text,
                    "document_name": chunk.document_name,
                    "jurisdiction": chunk.jurisdiction,
                    "year": chunk.execution_year,
                    "page_number": chunk.page_number,
                    "section_label": chunk.section_label,
                    "chunk_hash": chunk.chunk_hash,
                    "document_hash": chunk.document_hash,
                    "bbox": chunk.bbox,
                    "offset_start": chunk.offset_start,
                    "offset_end": chunk.offset_end,
                },
            )
        )

    client.upsert(collection_name=settings.COMPLIANCE_COLLECTION_NAME, points=points)
    logger.info("Ingested %s structural PDF chunks into Qdrant via batch pipeline.", len(points))
