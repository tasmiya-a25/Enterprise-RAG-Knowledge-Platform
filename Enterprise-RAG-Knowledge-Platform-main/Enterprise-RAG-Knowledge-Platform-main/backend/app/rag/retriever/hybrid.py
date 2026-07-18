"""
Hybrid retrieval: combines dense vector search (Qdrant) with sparse
BM25 keyword search using Reciprocal Rank Fusion (RRF), then hands the
merged candidate set to the cross-encoder reranker.

RRF is used instead of raw score-blending because vector cosine
similarity and BM25 scores live on incomparable scales -- RRF only
needs each list's *rank order*, which makes fusion robust without
manual score normalization.
"""
import uuid
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.rag.embeddings.embedder import get_embedder
from app.rag.retriever.vector_store import search as vector_search
from app.rag.retriever.bm25 import bm25_search
from app.rag.retriever.reranker import rerank
from app.models.document import Chunk
from sqlalchemy import select

settings = get_settings()

RRF_K = 60  # standard RRF smoothing constant


def _reciprocal_rank_fusion(rank_lists: list[list[uuid.UUID]]) -> dict:
    scores: dict = {}
    for ranked_ids in rank_lists:
        for rank, chunk_id in enumerate(ranked_ids, start=1):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (RRF_K + rank)
    return scores


def hybrid_search(db: Session, query: str, owner_id: uuid.UUID,
                   document_ids: list[uuid.UUID] | None = None) -> list[dict]:
    """
    Returns a reranked list of candidate chunks:
    [{"chunk_id", "content", "document_id", "page_number", "rerank_score"}, ...]
    """
    embedder = get_embedder()
    query_vec = embedder.embed_query(query)

    vector_hits = vector_search(query_vec, settings.RETRIEVAL_TOP_K, document_ids=document_ids, owner_id=owner_id)
    vector_ids = [uuid.UUID(str(h["chunk_id"])) for h in vector_hits]

    # BM25 candidate corpus: chunks belonging to the accessible documents.
    stmt = select(Chunk.id, Chunk.content, Chunk.document_id, Chunk.page_number)
    if document_ids:
        stmt = stmt.where(Chunk.document_id.in_(document_ids))
    else:
        from app.models.document import Document
        stmt = stmt.join(Document, Document.id == Chunk.document_id).where(Document.owner_id == owner_id)

    rows = db.execute(stmt).all()
    corpus = [(row.id, row.content) for row in rows]
    meta_by_id = {row.id: {"document_id": row.document_id, "page_number": row.page_number, "content": row.content} for row in rows}

    bm25_hits = bm25_search(query, corpus, settings.RETRIEVAL_TOP_K)
    bm25_ids = [h["chunk_id"] for h in bm25_hits]

    fused_scores = _reciprocal_rank_fusion([vector_ids, bm25_ids])
    if not fused_scores:
        return []

    top_fused = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)[:settings.RETRIEVAL_TOP_K]

    # Assemble candidates with content for reranking. Prefer Postgres metadata
    # (always available) and fall back to vector-store payload if a chunk was
    # somehow missing from `meta_by_id` (shouldn't normally happen).
    vector_payload_by_id = {uuid.UUID(str(h["chunk_id"])): h for h in vector_hits}
    candidates = []
    for chunk_id, fused_score in top_fused:
        meta = meta_by_id.get(chunk_id)
        if meta is None:
            payload = vector_payload_by_id.get(chunk_id)
            if payload is None:
                continue
            meta = {"document_id": payload.get("document_id"), "page_number": payload.get("page_number"),
                     "content": payload.get("content", "")}
        candidates.append({
            "chunk_id": str(chunk_id),
            "content": meta["content"],
            "document_id": str(meta["document_id"]),
            "page_number": meta["page_number"],
            "fusion_score": fused_score,
        })

    return rerank(query, candidates, settings.RERANK_TOP_K)
