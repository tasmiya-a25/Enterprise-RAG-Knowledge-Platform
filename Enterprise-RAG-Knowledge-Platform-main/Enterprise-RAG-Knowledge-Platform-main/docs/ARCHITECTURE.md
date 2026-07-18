# Architecture

## Request flow: asking a question

1. `POST /api/v1/chat` (`app/api/routes/chat.py`) authenticates the user
   (JWT via `app/api/deps.py`) and calls `chat_service.handle_chat_message`.
2. `chat_service` (`app/services/chat_service.py`) creates or loads a
   `Chat`, persists the user's message, and calls
   `rag.pipeline.answer_question`.
3. `pipeline.answer_question` (`app/rag/pipeline.py`) is the single RAG
   entry point:
   - `hybrid_search` (`app/rag/retriever/hybrid.py`) embeds the query,
     runs vector search against Qdrant and BM25 against the user's
     accessible chunks (fetched from Postgres), fuses both rankings with
     Reciprocal Rank Fusion, then reranks the fused candidates with a
     local cross-encoder.
   - `generation.generate_answer` (`app/rag/generation.py`) either calls
     OpenAI (if `OPENAI_API_KEY` is set) or falls back to a deterministic
     extractive synthesizer -- both return text with `[source:N]` markers.
   - Citations are assembled from the reranked chunks' metadata (document
     name, chunk id, page number, relevance score).
4. The assistant message (with citations as JSON) is persisted and
   returned to the client.

## Request flow: uploading a document

1. `POST /api/v1/documents/upload` validates the extension and size,
   saves the raw file to disk, creates a `Document` row (`status=pending`),
   and schedules `document_service.process_document` as a FastAPI
   `BackgroundTask`.
2. `process_document` (`app/services/document_service.py`) runs with its
   own DB session (the request's session is already closed by then):
   - `rag.ingestion.loaders.load_document` extracts text per-page (where
     the format has a page concept, e.g. PDF) or as one blob (TXT/MD/DOCX).
   - `rag.ingestion.chunker.chunk_text` splits each page's text using the
     configured strategy (recursive by default, markdown-aware for `.md`).
   - Chunk rows are written to Postgres (`Chunk` model), then embedded via
     the configured embedder and upserted into Qdrant with
     `document_id`/`owner_id`/`page_number` payload for later filtering.
   - The `Document.status` is updated to `indexed` or `failed` (with an
     error message) at each stage so the frontend can poll and show
     progress.

## Why Reciprocal Rank Fusion for hybrid search

Vector cosine similarity and BM25 scores live on incompatible scales (one
is bounded [-1, 1], the other is an unbounded, corpus-size-dependent TF-IDF
variant). Blending them with a weighted sum requires manual, corpus-specific
tuning. RRF instead only uses each list's *rank order* -- a chunk ranked
#1 by BM25 and #3 by vector search gets a combined score regardless of the
underlying scores' scale, which is robust across corpus sizes with zero
tuning. This is the same technique used by Elasticsearch's and Azure AI
Search's built-in hybrid search.

## Why a cross-encoder reranker on top of that

Bi-encoder similarity (used for the first-pass vector search) encodes the
query and each chunk independently, then compares embeddings -- fast
enough to run over an entire corpus, but limited because the model never
sees the query and chunk together. A cross-encoder feeds the (query,
chunk) pair through the model jointly, which is far more precise at
judging relevance, at the cost of being too slow to run over more than a
few dozen candidates. Using vector+BM25 to cheaply narrow the field, then
a cross-encoder to precisely rank the survivors, is the standard
production pattern for RAG retrieval quality.

## Why the LLM step is pluggable rather than required

Requiring an API key to run the project at all would make the "day 1"
build undemoable for anyone without one, and would tie the whole platform
to a single vendor. The extractive fallback (`generation.py`) is
deliberately simple and honest about being a fallback -- it never
fabricates an answer, it only ever returns sentences that are actually
present in the retrieved chunks. Swapping in OpenAI, Anthropic, or a
self-hosted model only requires implementing one function
(`generate_answer`) with the same signature.

## Portable UUID column type

Postgres has a native `UUID` column type, but SQLite (used by the test
suite) doesn't. `app/database/guid.py` implements a `TypeDecorator` that
uses the native type on Postgres and a `CHAR(32)` representation
everywhere else, so the exact same models work against a throwaway SQLite
database in tests and a real Postgres database in production -- no
test-only model duplication.
