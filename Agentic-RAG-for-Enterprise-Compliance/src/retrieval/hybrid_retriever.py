from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None

try:
    from langchain_ollama import OllamaEmbeddings
except ImportError:
    OllamaEmbeddings = None

from src.config import get_settings
from src.database.qdrant_wrapper import get_db_client

logger = logging.getLogger("aegis.retrieval")
settings = get_settings()

# Global singleton caches to prevent re-initializing HF models on every retrieval call
_GLOBAL_RERANKER_CACHE = None
_GLOBAL_EMBEDDER_CACHE = None
_GLOBAL_QDRANT_CLIENT_CACHE = None


class RetrieveItem(BaseModel):
    point_id: str = Field(..., description="Qdrant point identifier.")
    text: str = Field(..., description="Extracted chunk text.")
    document_name: str = Field(..., description="Document origin name.")
    page_number: int = Field(..., description="Page number where the chunk originates.")
    section_label: str = Field(..., description="Document structural section label.")
    chunk_hash: str = Field(..., description="SHA-256 chunk hash.")
    score: float = Field(..., description="Retrieval score or rerank score.")
    source_metadata: dict[str, Any] = Field(default_factory=dict, description="Full payload metadata.")
    retrieval_method: str = Field(..., description="Stage 1 or stage 2 retrieval method.")


@dataclass
class HybridRetriever:
    client: QdrantClient | None
    embedder: OllamaEmbeddings | None
    reranker: CrossEncoder | None = None

    @classmethod
    def create(cls) -> "HybridRetriever":
        global _GLOBAL_RERANKER_CACHE, _GLOBAL_EMBEDDER_CACHE, _GLOBAL_QDRANT_CLIENT_CACHE

        if _GLOBAL_QDRANT_CLIENT_CACHE is None:
            try:
                _GLOBAL_QDRANT_CLIENT_CACHE = get_db_client()
            except Exception as exc:
                logger.warning("Unable to initialize Qdrant client: %s", exc)

        if _GLOBAL_EMBEDDER_CACHE is None and OllamaEmbeddings is not None:
            try:
                _GLOBAL_EMBEDDER_CACHE = OllamaEmbeddings(base_url=settings.OLLAMA_BASE_URL, model=settings.LOCAL_EMBED_MODEL)
            except Exception as exc:
                logger.warning("Failed to initialize Ollama embeddings: %s", exc)

        if _GLOBAL_RERANKER_CACHE is None and CrossEncoder is not None:
            try:
                _GLOBAL_RERANKER_CACHE = CrossEncoder(settings.CROSS_ENCODER_MODEL)
                logger.info("Loaded singleton cross-encoder reranker: %s", settings.CROSS_ENCODER_MODEL)
            except Exception as exc:
                logger.warning("Failed to load cross-encoder reranker: %s", exc)

        return cls(
            client=_GLOBAL_QDRANT_CLIENT_CACHE,
            embedder=_GLOBAL_EMBEDDER_CACHE,
            reranker=_GLOBAL_RERANKER_CACHE,
        )

    def embed_query(self, query: str) -> list[float]:
        if self.embedder is None:
            return [0.0] * settings.EMBEDDING_DIM
        return self.embedder.embed_query(query)

    def _token_overlap_score(self, query: str, document_text: str) -> float:
        query_tokens = set(re.findall(r"\w+", query.lower()))
        doc_tokens = set(re.findall(r"\w+", document_text.lower()))
        if not query_tokens or not doc_tokens:
            return 0.0
        return len(query_tokens & doc_tokens) / len(query_tokens | doc_tokens)

    def _bm25_lexical_score(self, query: str, document_text: str) -> float:
        query_terms = [t.lower() for t in re.findall(r"\w+", query) if len(t) > 2]
        if not query_terms:
            return 0.0
        doc_lower = document_text.lower()
        score = 0.0
        for term in query_terms:
            tf = doc_lower.count(term)
            if tf > 0:
                # BM25 term frequency saturation scaling
                score += (tf * 2.2) / (tf + 1.2)
        return score

    def _compute_rrf(self, dense_hits: list[RetrieveItem], query: str, k: int = 60) -> list[RetrieveItem]:
        if not dense_hits:
            return []
        
        # 1. Rank Dense Hits
        dense_hits_sorted = sorted(dense_hits, key=lambda x: x.score, reverse=True)
        dense_ranks = {item.point_id: rank + 1 for rank, item in enumerate(dense_hits_sorted)}

        # 2. Rank Sparse Hits using Lexical BM25
        sparse_hits_sorted = sorted(
            dense_hits,
            key=lambda x: self._bm25_lexical_score(query, x.text),
            reverse=True
        )
        sparse_ranks = {item.point_id: rank + 1 for rank, item in enumerate(sparse_hits_sorted)}

        # 3. Apply Reciprocal Rank Fusion Formula
        fused_items = []
        for item in dense_hits:
            r_dense = dense_ranks.get(item.point_id, 999)
            r_sparse = sparse_ranks.get(item.point_id, 999)
            
            rrf_score = (1.0 / (k + r_dense)) + (1.0 / (k + r_sparse))
            
            # Copy item with updated RRF score
            fused_item = item.model_copy()
            fused_item.score = rrf_score
            fused_item.retrieval_method = "rrf_hybrid_fusion"
            fused_items.append(fused_item)

        fused_items.sort(key=lambda x: x.score, reverse=True)
        return fused_items

    def retrieve(
        self,
        query: str,
        jurisdiction: str,
        document_name: str | None = None,
        execution_year: int | None = None,
    ) -> list[RetrieveItem]:
        if self.client is None:
            return []

        query_vector = self.embed_query(query)
        hits = []

        try:
            if hasattr(self.client, "query_points"):
                response = self.client.query_points(
                    collection_name=settings.COMPLIANCE_COLLECTION_NAME,
                    query=query_vector,
                    limit=settings.RETRIEVAL_TOP_K * 2,
                )
                hits = response.points
            elif hasattr(self.client, "search"):
                hits = self.client.search(
                    collection_name=settings.COMPLIANCE_COLLECTION_NAME,
                    query_vector=query_vector,
                    limit=settings.RETRIEVAL_TOP_K * 2,
                )
        except Exception as exc:
            logger.error("Failed to query Qdrant points: %s", exc)
            return []

        candidates: list[RetrieveItem] = []
        for hit in hits:
            payload = getattr(hit, "payload", {}) or {}
            score = getattr(hit, "score", 0.0) or 0.0
            point_id = str(getattr(hit, "id", ""))

            candidates.append(
                RetrieveItem(
                    point_id=point_id,
                    text=payload.get("text", ""),
                    document_name=str(payload.get("document_name", "unknown")),
                    page_number=int(payload.get("page_number", 0)),
                    section_label=str(payload.get("section_label", "unknown")),
                    chunk_hash=str(payload.get("chunk_hash", "")),
                    score=float(score),
                    source_metadata=payload,
                    retrieval_method="dense_vector",
                )
            )

        candidates = self._compute_rrf(candidates, query)

        if self.reranker and candidates:
            query_texts = [query] * len(candidates)
            rerank_inputs = [[query_texts[i], candidates[i].text] for i in range(len(candidates))]
            try:
                rerank_scores = self.reranker.predict(rerank_inputs)
                for idx, score in enumerate(rerank_scores):
                    candidates[idx].score = float(score)
                    candidates[idx].retrieval_method = "cross_encoder_rerank"
                candidates.sort(key=lambda item: item.score, reverse=True)
                return candidates[: settings.RERANK_TOP_K]
            except Exception as exc:
                logger.warning("Cross-encoder reranker failed: %s", exc)

        for candidate in candidates:
            overlap_score = self._token_overlap_score(query, candidate.text)
            candidate.score += overlap_score * settings.TOKEN_OVERLAP_FALLBACK_THRESHOLD
            candidate.retrieval_method = "dense_vector_fallback"

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[: settings.RERANK_TOP_K]
