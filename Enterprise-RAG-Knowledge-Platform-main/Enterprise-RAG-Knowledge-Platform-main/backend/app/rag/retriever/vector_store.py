"""
Vector store wrapper around Qdrant.

Runs in embedded/local mode by default (on-disk, no separate server --
great for a day-1 build and small deployments). Setting QDRANT_URL in
config switches to a real Qdrant server (e.g. the one in docker-compose)
with zero code changes, which is the recommended path once you're
indexing more than a few thousand documents concurrently.
"""
import uuid
from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.config.settings import get_settings

settings = get_settings()


@lru_cache
def get_qdrant_client() -> QdrantClient:
    if settings.QDRANT_URL:
        return QdrantClient(url=settings.QDRANT_URL)
    return QdrantClient(path=settings.QDRANT_LOCAL_PATH)


def ensure_collection(dim: int) -> None:
    client = get_qdrant_client()
    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE),
        )


def upsert_chunks(chunk_ids: list[uuid.UUID], vectors: list[list[float]], payloads: list[dict]) -> None:
    client = get_qdrant_client()
    ensure_collection(len(vectors[0]))
    points = [
        qmodels.PointStruct(id=str(cid), vector=vec, payload=payload)
        for cid, vec, payload in zip(chunk_ids, vectors, payloads)
    ]
    client.upsert(collection_name=settings.QDRANT_COLLECTION, points=points)


def search(query_vector: list[float], top_k: int, document_ids: list[uuid.UUID] | None = None,
           owner_id: uuid.UUID | None = None) -> list[dict]:
    client = get_qdrant_client()
    must = []
    if document_ids:
        must.append(qmodels.FieldCondition(key="document_id", match=qmodels.MatchAny(any=[str(d) for d in document_ids])))
    if owner_id:
        must.append(qmodels.FieldCondition(key="owner_id", match=qmodels.MatchValue(value=str(owner_id))))

    query_filter = qmodels.Filter(must=must) if must else None

    existing = [c.name for c in client.get_collections().collections]
    if settings.QDRANT_COLLECTION not in existing:
        # Nothing has been indexed yet.
        return []

    response = client.query_points(
        collection_name=settings.QDRANT_COLLECTION,
        query=query_vector,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    )

    return [
        {"chunk_id": r.id, "score": r.score, **(r.payload or {})}
        for r in response.points
    ]


def delete_by_document(document_id: uuid.UUID) -> None:
    client = get_qdrant_client()
    try:
        client.delete(
            collection_name=settings.QDRANT_COLLECTION,
            points_selector=qmodels.FilterSelector(
                filter=qmodels.Filter(
                    must=[qmodels.FieldCondition(key="document_id", match=qmodels.MatchValue(value=str(document_id)))]
                )
            ),
        )
    except Exception:
        pass
