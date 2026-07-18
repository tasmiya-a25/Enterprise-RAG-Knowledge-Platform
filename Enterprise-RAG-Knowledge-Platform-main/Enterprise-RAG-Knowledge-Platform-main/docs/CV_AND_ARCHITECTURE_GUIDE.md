# Enterprise RAG Platform — Architecture, Workflow & CV Guide

This document exists for one purpose: to help you *talk about this project*
confidently — in a CV, in a cover letter, and in an interview where someone
asks "walk me through this." It covers what the system does, how it's put
together, why each choice was made, what to put on your resume, and how to
grow it toward a genuinely senior-level portfolio piece.

---

## 1. The 30-second pitch

> "I built a Retrieval-Augmented Generation platform that lets users upload
> documents and ask questions grounded in them, with citations back to the
> source. It uses hybrid search (vector + keyword) fused with Reciprocal
> Rank Fusion, a cross-encoder reranker, JWT auth with role-based access,
> and runs fully offline with local embedding models — no API key required
> — but upgrades to a fully generative LLM the moment you add one. It's
> Dockerized, has a tested backend (18 passing tests), and a React/
> TypeScript frontend."

That single paragraph already signals: you understand modern RAG
architecture (not just "call an LLM"), you think about production
concerns (auth, testing, offline-by-default), and you can make and defend
engineering tradeoffs.

---

## 2. What the system actually does (plain-English workflow)

**Uploading a document:**
1. User uploads a PDF/DOCX/TXT/MD file through the web UI.
2. The backend saves the file, creates a database record with status
   `pending`, and immediately returns — the user isn't kept waiting.
3. In the background: the text is extracted, split into overlapping
   chunks, converted into vector embeddings (numbers that capture
   meaning), and stored in a vector database (Qdrant) plus a regular
   database (Postgres) for the text itself.
4. The document's status flips to `indexed` once done. The frontend polls
   and updates automatically.

**Asking a question:**
1. User types a question in the chat UI.
2. The backend turns the question into an embedding and runs **two**
   searches in parallel: a *vector search* (finds chunks with similar
   meaning) and a *keyword search* (BM25 — finds chunks with matching
   words). This "hybrid" approach catches things either method alone
   would miss (e.g. exact product codes that vector search might blur,
   or paraphrased questions that keyword search would miss entirely).
3. Both result lists are merged using **Reciprocal Rank Fusion** — a
   technique that combines rankings without needing to compare
   incompatible scores.
4. The merged candidates are then **reranked** by a cross-encoder model
   that looks at the question and each chunk *together*, which is far
   more accurate than the first-pass search, at the cost of being too
   slow to run on the whole document library.
5. The top chunks are handed to an LLM (or a local fallback if no API key
   is configured) to generate an answer, with citations attached back to
   the exact source chunk, document, and page.
6. The conversation is saved so the user can continue asking follow-ups.

---

## 3. Architecture diagram

```
┌─────────────┐        ┌──────────────────────────────────────────────┐
│   React      │  HTTP  │                FastAPI Backend                │
│   Frontend   │───────►│                                                │
│ (Vite + TS)  │◄───────│  Auth (JWT)  │  Documents  │  Chat  │  Feedback │
└─────────────┘        └───────┬─────────────┬──────────────┬──────────┘
                                │             │              │
                                ▼             ▼              ▼
                        ┌──────────────┐ ┌─────────┐  ┌──────────────┐
                        │  PostgreSQL   │ │ Qdrant  │  │  LLM          │
                        │  (users,      │ │ (vector │  │  (OpenAI or   │
                        │  documents,   │ │  index) │  │  local        │
                        │  chats)       │ │         │  │  extractive)  │
                        └──────────────┘ └─────────┘  └──────────────┘
```

**Retrieval pipeline in detail:**

```
question → embed → ┬─ vector search (Qdrant) ─┐
                    └─ BM25 keyword search ────┘
                              │
                    Reciprocal Rank Fusion
                              │
                    Cross-encoder reranking
                              │
                    Prompt construction + generation
                              │
                    Answer + citations
```

---

## 4. Full tech stack (what to list on your CV)

| Layer | Technology | What it's for |
|---|---|---|
| **Backend framework** | FastAPI (Python 3.12) | REST API, async-ready, auto-generated OpenAPI docs |
| **ORM / DB** | SQLAlchemy 2.0, PostgreSQL, Alembic | Data modeling, migrations |
| **Auth** | JWT (python-jose), bcrypt | Stateless auth, secure password storage |
| **Validation** | Pydantic v2 | Request/response schemas, settings management |
| **Vector DB** | Qdrant | Semantic (embedding) search |
| **Keyword search** | BM25 (rank-bm25) | Classic TF-IDF-style search, complements vector search |
| **Embeddings** | sentence-transformers (BGE model) | Local, offline text-to-vector conversion |
| **Reranking** | Cross-encoder (sentence-transformers) | High-precision relevance scoring |
| **LLM integration** | OpenAI SDK, pluggable interface | Generative answers when configured |
| **Document parsing** | pypdf, python-docx | Multi-format text extraction |
| **Frontend framework** | React 18, TypeScript, Vite | Fast, typed, modern SPA tooling |
| **Frontend state/data** | React Query, React Router, Axios | Server-state caching, routing, HTTP client |
| **Styling** | Tailwind CSS | Utility-first styling |
| **Testing** | pytest | Automated backend test suite |
| **Containerization** | Docker, Docker Compose | Reproducible multi-service deployment |
| **CI** | GitHub Actions | Automated lint/test/build on every push |
| **Logging** | Loguru | Structured, readable request logging |

This table alone is a legitimate "Tech Stack" section for a CV or
portfolio site.

---

## 5. Why this is a strong CV project (and how to phrase it)

Most junior/portfolio RAG projects are a single Colab notebook that calls
`openai.ChatCompletion` on top of a naive vector search. What makes this
one stand out:

1. **It's a real, multi-service application** — not a notebook. Auth,
   database migrations, background processing, a typed frontend, tests,
   Docker — this is what "software engineering" looks like, not just
   "calling an API."
2. **It works with zero API keys.** This is a genuinely uncommon design
   choice and a good talking point: you understood that requiring a paid
   API key makes a demo project inaccessible, so you built local
   embeddings + a local reranker + an extractive fallback, and made the
   LLM step swappable.
3. **Hybrid retrieval + reranking is the real production RAG pattern.**
   Naive single-vector-search RAG is a beginner pattern; hybrid search +
   RRF fusion + cross-encoder reranking is what companies like Elastic,
   Azure AI Search, and serious RAG teams actually use. Being able to
   explain *why* (see Section 6) is a strong signal of depth.
4. **You debugged real, non-obvious issues.** (See Section 7 — this is
   genuinely great interview material.)
5. **You know what's missing and why.** The `ROADMAP.md` in this repo is
   itself a signal of maturity: a senior engineer always knows the gap
   between "demo-ready" and "production-ready," and can prioritize what
   to build next.

### Suggested CV bullet points

Pick 2-4 depending on space, adapt to the role you're applying for:

- *"Built a full-stack Retrieval-Augmented Generation platform (FastAPI,
  React/TypeScript, PostgreSQL, Qdrant) implementing hybrid vector +
  BM25 search fused via Reciprocal Rank Fusion and cross-encoder
  reranking, with cited, source-grounded answers."*
- *"Designed a pluggable LLM architecture allowing the system to run
  fully offline with local embedding/reranking models, falling back
  gracefully when no external API key is configured."*
- *"Implemented JWT-based authentication with refresh token rotation,
  bcrypt password hashing, and role-based access control."*
- *"Wrote a 18-test pytest suite covering auth, document ingestion, and
  the end-to-end RAG pipeline using dependency injection and test
  doubles for ML components, enabling CI runs with zero external
  dependencies."*
- *"Containerized the full stack (Postgres, backend, frontend) with
  Docker Compose and set up GitHub Actions CI for linting, testing, and
  build verification."*

---

## 6. Talking points for interviews (the "why", not just the "what")

Interviewers care much more about *why* you made a choice than *what*
you built. Here are the design decisions worth being ready to defend:

- **"Why hybrid search instead of just vector search?"**
  Vector search is great at *semantic* similarity but can miss exact
  matches (product codes, names, numbers) that a keyword search catches
  trivially. Combining both, fused by rank rather than raw score (since
  BM25 and cosine similarity live on incompatible scales), gets the best
  of both without manual score-weight tuning.

- **"Why rerank if you already did vector + BM25 search?"**
  First-pass retrieval (bi-encoder) scores the query and each document
  independently, then compares embeddings — fast, but the model never
  sees them together. A cross-encoder scores the (query, chunk) pair
  jointly, which is much more accurate, but too slow to run over an
  entire corpus. So: cheap retrieval narrows the field, expensive
  reranking picks the best from a small shortlist.

- **"Why make the LLM optional?"**
  Two reasons: (1) it makes the whole system runnable and demoable with
  zero cost/API keys, which matters for a portfolio project anyone can
  clone and run; (2) it avoids vendor lock-in — swapping providers only
  means implementing one function with the same interface.

- **"What would you change for real production scale?"**
  BM25 is currently rebuilt in-memory per query, fine for thousands of
  chunks but not millions — I'd swap it for Elasticsearch/OpenSearch.
  Background processing uses FastAPI's in-process BackgroundTasks; at
  scale I'd move to Celery/RQ with Redis so indexing survives a restart
  and can scale horizontally. Qdrant currently runs embedded/local; a
  real deployment would run it as its own service.

---

## 7. Real bugs found and fixed (great interview stories)

These happened while actually running the system end-to-end — which is
exactly the point. Anyone can write code that *looks* right; being able
to say "I ran it, it broke, here's why, here's the fix" is far more
convincing than a project that was never actually executed.

1. **`passlib` + modern `bcrypt` incompatibility.** The popular
   `passlib` password-hashing library has a known bug where it
   misdetects the installed `bcrypt` version and throws a false
   "password too long" error on *every* hash/verify call. Fix: called
   `bcrypt` directly instead of going through `passlib`'s wrapper —
   simpler code and one fewer (largely unmaintained) dependency.

2. **`qdrant-client` API change.** Newer versions of the Qdrant Python
   client removed the `.search()` method in favor of `.query_points()`.
   The old code was silently swallowing the resulting error and
   returning empty results instead of failing loudly. Fix: switched to
   the current API and made errors surface instead of being hidden.

3. **BM25 edge case with small document sets.** BM25's relevance
   formula includes an "inverse document frequency" term that can turn
   near-zero or even *negative* when a search term appears in most or
   all documents in a small collection (e.g. a single uploaded
   document) — even for an exact, obviously-relevant match. The
   original filter (`only keep BM25 hits with a positive score`) was
   silently discarding genuinely relevant results in exactly this common
   case. Fix: removed the premature filter and let the downstream
   cross-encoder reranker — which is actually good at judging
   relevance — make that call instead.

Being able to narrate any of these three in an interview ("I hit a bug
where X, root-caused it to Y, fixed it by Z") is a much stronger signal
than reciting a list of technologies used.

---

## 8. Roadmap: growing this to the next level

This is organized by effort so you can pick what's realistic for your
timeline. See also `docs/ROADMAP.md` for the original build notes.

### Near-term (a few days each, high resume value)
- **Streaming responses** — token-by-token answers via Server-Sent
  Events, like ChatGPT's typing effect. Strong UX signal, moderate
  effort.
- **Google OAuth login** — the `User` model is already OAuth-shaped;
  this is mostly wiring a callback endpoint.
- **Admin analytics dashboard** — total users/documents/questions,
  latency stats, most-used documents. The data (e.g. `latency_ms` per
  message) is already captured; this is aggregation queries + a
  frontend page. Great for demonstrating full-stack breadth.
- **CSV/PPTX/XLSX ingestion** — the loader system is designed so adding
  a format is a small, contained change (`app/rag/ingestion/loaders.py`).

### Mid-term (1-2 weeks, meaningfully raises the ceiling)
- **Move background processing to Celery + Redis** — real task queue
  with retries, horizontal scaling, and survival across restarts. This
  is the single highest-value "make it production-grade" change.
- **Swap BM25 for Elasticsearch/OpenSearch** — real inverted index that
  scales past a few thousand documents.
- **Run Qdrant as its own service** (already supported via `QDRANT_URL`)
  instead of embedded mode, and add a proper ingestion pipeline that can
  handle concurrent uploads at volume.
- **Evaluation harness** — a small labeled set of (question, expected
  answer/document) pairs and a script that measures retrieval precision
  and answer quality over time. This is what separates "I built a RAG
  demo" from "I understand how to *measure* RAG quality" — a genuinely
  senior-level signal.

### Advanced / "impress a staff engineer" territory
- **Multi-tenancy done properly** — organizations with real data
  isolation, not just a foreign key.
- **Agentic retrieval** — let the model decide whether to search, which
  filters to use, or whether to ask a clarifying question, instead of
  always running the same fixed pipeline.
- **Observability** — real Prometheus metrics (`/metrics` is currently a
  placeholder), request tracing, and a Grafana dashboard showing
  retrieval latency, token usage, and error rates.
- **Load testing + documented benchmarks** — e.g. "handles N concurrent
  users at P95 latency of X ms" — turns a portfolio project into
  something you can quote numbers about.

---

## 9. Quick reference: where things live

| I want to change... | Look in... |
|---|---|
| Chunking strategy / size | `backend/app/rag/ingestion/chunker.py` |
| Which embedding model is used | `backend/app/config/settings.py` (`EMBEDDING_MODEL`) |
| Retrieval fusion logic | `backend/app/rag/retriever/hybrid.py` |
| Prompt wording | `backend/app/rag/prompts/templates.py` |
| Adding a new document format | `backend/app/rag/ingestion/loaders.py` |
| Auth / token logic | `backend/app/auth/security.py` |
| Frontend chat UI | `frontend/src/pages/Chat.tsx` |
| Database schema | `backend/app/models/` + `alembic/versions/` |
