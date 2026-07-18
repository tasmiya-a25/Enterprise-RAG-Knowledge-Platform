# Roadmap

This project was built as a genuine, working "Phase 1" core rather than a
wide set of stubs. This document is an honest map of what's implemented,
what's deliberately simplified, and what a Phase 2 would add -- useful both
for continuing the project and for talking through the tradeoffs (e.g. in
an interview).

## What's fully implemented and tested

- JWT auth (register / login / refresh), bcrypt password hashing, RBAC role
  field on the user model (admin/editor/user)
- Document upload for PDF, DOCX, TXT, Markdown -- extraction, chunking
  (recursive + markdown-aware + sliding window strategies), local embeddings
  (BGE via sentence-transformers, no API key required)
- Hybrid retrieval: vector search (Qdrant, embedded/local mode) + BM25,
  fused with Reciprocal Rank Fusion, then reranked with a local
  cross-encoder
- RAG answer generation with per-claim citations (document, chunk, page,
  score). Pluggable LLM step: fully generative via OpenAI if
  `OPENAI_API_KEY` is set, otherwise a deterministic extractive fallback so
  the whole system runs with zero external API keys
- Chat persistence (multi-turn history, per-chat titles, delete), feedback
  endpoint, structured request logging, audit log table
- Dockerized (Postgres + backend + frontend), Alembic migrations wired to
  the real models, a pytest suite (18 tests) covering auth, documents, and
  the RAG pipeline end-to-end
- React + TypeScript + Vite + Tailwind + React Query frontend: login,
  register, document upload/list/delete with live status polling, and a
  multi-chat interface with inline citations

## Deliberately simplified for a one-day build

- **BM25 corpus**: built in-memory per-query from the user's chunks rather
  than a persistent inverted index. Fine up to a few thousand chunks;
  swap for Elasticsearch/OpenSearch/Whoosh behind the same
  `bm25_search()` interface at real scale.
- **Background processing**: uses FastAPI `BackgroundTasks` (in-process)
  rather than a task queue. Swap for Celery/RQ + Redis when you need
  retries, horizontal scaling, or to survive a process restart mid-index.
- **Vector store**: Qdrant runs embedded/local (on-disk, no server) by
  default. Point `QDRANT_URL` at a real Qdrant server (add one to
  docker-compose) once you need concurrent writers or larger corpora.
- **Sync SQLAlchemy**: simpler to read and reason about for a first build.
  Swapping to `asyncpg` + async sessions is contained to
  `app/database/session.py` and each route's `db: Session` type hints.

## Not yet built (real, meaningful additions -- not just missing checkboxes)

- **Google OAuth login** -- needs a registered OAuth app + callback
  handling; the `User` model and JWT issuance are already OAuth-shaped
  (an OAuth login would just mint the same JWTs after verifying the
  Google token).
- **Email verification / password reset** -- `is_verified` exists on the
  `User` model; wiring this up needs a transactional email provider
  (SendGrid/SES) and short-lived signed tokens.
- **Admin analytics dashboard** -- total users/documents/questions,
  latency, token usage, storage usage. The `latency_ms` field is already
  captured per message as a starting point; this is mostly aggregation
  queries + a frontend page.
- **CSV / PPTX / XLSX / OCR document ingestion** -- the loader registry in
  `app/rag/ingestion/loaders.py` is designed to make adding a new format a
  ~20-line addition (see `LOADERS` dict); OCR specifically needs
  `pytesseract` + Tesseract installed in the container.
- **Streaming chat responses** (token-by-token) -- currently returns the
  full answer in one response. Needs Server-Sent Events or a WebSocket on
  the `/chat` endpoint plus a streaming-aware OpenAI call.
- **Global search, tags, filters by author/date/org** -- the schema
  supports it (organizations, created_at, etc.); needs query params + a
  frontend search UI.
- **Refresh-token revocation / true logout** -- JWTs are stateless right
  now; logout is client-side only. A production build would deny-list
  `jti` values in Redis with a TTL matching the refresh token's expiry.
- **Rate limiting, CI deploy step, Prometheus metrics** -- `/metrics` is a
  placeholder; wiring `prometheus-fastapi-instrumentator` and a real
  rate limiter (e.g. `slowapi`) are both drop-in additions.
