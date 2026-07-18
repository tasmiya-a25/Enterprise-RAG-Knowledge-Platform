# Enterprise RAG Knowledge Platform

A working Retrieval-Augmented Generation (RAG) platform: upload company
documents, ask natural-language questions, and get answers grounded in
those documents with citations back to the source.

Runs **fully offline by default** -- local embeddings, local reranking, no
external API key required to get a working system. Add an `OPENAI_API_KEY`
later to upgrade from extractive to fully generative answers with zero
code changes.

> This is a "Phase 1" build: the core pipeline (auth, ingestion, hybrid
> retrieval, reranking, cited answers, chat, tests, Docker) is real and
> tested end-to-end. See [`docs/ROADMAP.md`](docs/ROADMAP.md) for an
> honest list of what's simplified and what a Phase 2 would add.

## Features

- **Auth**: register/login/refresh with JWT + bcrypt, role field (admin/editor/user)
- **Document ingestion**: PDF, DOCX, TXT, Markdown -> extraction -> chunking -> embeddings -> vector index
- **Hybrid retrieval**: vector search (Qdrant) + BM25, fused with Reciprocal Rank Fusion
- **Reranking**: local cross-encoder rescoring before generation
- **Cited answers**: every answer includes document name, chunk id, page number, and relevance score
- **Pluggable LLM**: works offline (extractive fallback) or with OpenAI (fully generative)
- **Chat**: multi-turn history, per-chat titles, delete, feedback (thumbs up/down)
- **Frontend**: React + TypeScript + Vite + Tailwind + React Query -- login, document manager, chat UI
- **Ops**: Docker Compose, Alembic migrations, structured request logging, health endpoint, pytest suite (18 tests)

## Architecture

```
                 ┌──────────────┐
   question ───► │  Hybrid       │  vector search (Qdrant) + BM25
                 │  Retrieval    │  merged via Reciprocal Rank Fusion
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │  Reranker     │  local cross-encoder
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐
                 │  Prompt +     │  OpenAI if configured,
                 │  Generation   │  else local extractive synthesis
                 └──────┬───────┘
                        ▼
                 answer + citations
```

Documents are extracted -> chunked (recursive / markdown-aware / sliding
window) -> embedded locally (BGE via sentence-transformers) -> vectors
stored in Qdrant, chunk text + metadata stored in Postgres.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full backend
folder layout and [`docs/ROADMAP.md`](docs/ROADMAP.md) for what's built
vs. deferred.

## Folder structure

```
enterprise-rag/
  backend/
    app/
      api/routes/       # auth, users, documents, chat, feedback
      auth/             # password hashing, JWT
      config/           # pydantic-settings config
      crud/             # DB access functions
      database/         # engine/session, portable GUID column type
      models/            # SQLAlchemy models
      schemas/           # Pydantic request/response models
      rag/
        embeddings/      # local + OpenAI embedder
        ingestion/       # loaders (pdf/docx/txt/md) + chunkers
        retriever/       # vector store, BM25, hybrid fusion, reranker
        prompts/         # prompt templates
        pipeline.py      # end-to-end RAG orchestration
        generation.py    # pluggable LLM / extractive fallback
      services/          # document ingestion service, chat service
      middleware/        # request logging
      main.py
    alembic/             # DB migrations
    tests/               # pytest suite (auth, documents, chat/RAG)
  frontend/
    src/
      api/               # axios client + typed endpoints
      context/           # auth context
      pages/             # Login, Register, Documents, Chat
      components/        # layout, protected route
  docker-compose.yml
  .env.example
  docs/
```

## Running it

### 1. Docker Compose (recommended)

```bash
cp .env.example .env
# optionally set OPENAI_API_KEY in .env for generative answers
docker compose up --build
```

- Backend: http://localhost:8000 (docs at `/docs`)
- Frontend: http://localhost:5173

The first embedding/reranker call downloads small open models from
Hugging Face on first use (a few hundred MB, one-time, then cached in the
`backend_storage` volume).

### 2. Running locally without Docker

**Backend** (needs a running Postgres -- `docker compose up postgres` is
the easiest way to get one):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg2://rag_user:rag_password@localhost:5432/rag_db
alembic upgrade head          # or rely on create_all() at startup
uvicorn app.main:app --reload
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

### 3. Running the tests

```bash
cd backend
pip install -r requirements.txt pytest
pytest -v
```

Tests run against an isolated SQLite database with a fake embedder/reranker
(see `tests/conftest.py`) -- no network access, model downloads, or API
keys required.

## API overview

All routes are under `/api/v1`. Full interactive docs at `/docs` (Swagger)
once the backend is running.

| Method | Path                     | Description                     |
|--------|--------------------------|----------------------------------|
| POST   | `/auth/register`         | Create an account                |
| POST   | `/auth/login`            | Get access + refresh tokens      |
| POST   | `/auth/refresh`          | Rotate access token               |
| POST   | `/auth/logout`           | Client-side token discard         |
| GET    | `/me`                    | Current user                      |
| PUT    | `/me`                    | Update profile                    |
| POST   | `/documents/upload`      | Upload + index a document         |
| GET    | `/documents`             | List your documents               |
| GET    | `/documents/{id}`        | Document detail / status          |
| DELETE | `/documents/{id}`        | Delete a document                 |
| POST   | `/chat`                  | Ask a question (creates chat if needed) |
| GET    | `/chat/history`          | List your chats                   |
| GET    | `/chat/{id}`             | Full message history for a chat   |
| DELETE | `/chat/{id}`             | Delete a chat                     |
| POST   | `/feedback`              | Thumbs up/down on an answer       |
| GET    | `/health`                | Health check                      |

## Configuration

See [`.env.example`](.env.example) and `backend/app/config/settings.py`
for every configurable value (chunk size/overlap, retrieval top-k,
embedding model, reranker model, etc.).

## Deployment

The included Dockerfiles and `docker-compose.yml` are a reasonable
starting point for a single-host deployment (e.g. an EC2 instance) behind
an NGINX reverse proxy for TLS termination. For production you'd want to:
put Postgres on managed storage (RDS), point `QDRANT_URL` at a real Qdrant
server rather than embedded mode, and move document processing to a
Celery/RQ worker queue -- see `docs/ROADMAP.md`.

## Future improvements

See [`docs/ROADMAP.md`](docs/ROADMAP.md) for the full, honest list:
Google OAuth, email verification, admin analytics dashboard, CSV/PPTX/XLSX/OCR
ingestion, streaming responses, global search/filters, refresh-token
revocation, rate limiting, and metrics.

## License

MIT
