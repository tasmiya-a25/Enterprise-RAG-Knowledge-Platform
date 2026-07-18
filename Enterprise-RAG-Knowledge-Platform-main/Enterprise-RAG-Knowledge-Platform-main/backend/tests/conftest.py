"""
Shared pytest fixtures.

Tests run against an isolated in-memory SQLite database (via the portable
GUID column type) and a fake embedder/reranker so the suite runs in CI
with zero external network calls or model downloads. This mirrors exactly
the manual smoke test used to validate the RAG pipeline during development.
"""
import os
import random
import tempfile

# IMPORTANT: DATABASE_URL must be set before *any* app module is imported,
# since `app/database/session.py` creates its engine at import time and
# several modules (e.g. app/services/document_service.py) do
# `from app.database.session import SessionLocal`, binding that name once.
# Using one real file-based SQLite DB for the whole test session -- and
# resetting tables between tests -- means every part of the app (including
# the background indexing task) reads and writes the exact same database,
# just like in production.
_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "enterprise_rag_test.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ.setdefault("QDRANT_LOCAL_PATH", os.path.join(tempfile.gettempdir(), "enterprise_rag_test_qdrant"))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(monkeypatch):
    """A TestClient wired to a fresh-per-test SQLite DB and fake ML models."""

    # --- Fake embedder: no HF download required ---
    import app.rag.embeddings.embedder as embedder_mod

    class FakeEmbedder:
        dim = 32

        def embed_texts(self, texts):
            return [[random.random() for _ in range(32)] for _ in texts]

        def embed_query(self, text):
            return self.embed_texts([text])[0]

    monkeypatch.setattr(embedder_mod, "get_embedder", lambda: FakeEmbedder())

    # --- Fake reranker: no cross-encoder download required ---
    import app.rag.retriever.hybrid as hybrid_mod

    def fake_rerank(query, candidates, top_k):
        for c in candidates:
            c["rerank_score"] = 1.0
        return candidates[:top_k]

    monkeypatch.setattr(hybrid_mod, "rerank", fake_rerank)

    import app.main as main_mod
    from app.database.session import Base, engine

    # Reset schema between tests so each test starts from a clean slate.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(main_mod.app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    client.post("/api/v1/auth/register", json={"email": "test@example.com", "password": "supersecret123"})
    r = client.post("/api/v1/auth/login", json={"email": "test@example.com", "password": "supersecret123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
