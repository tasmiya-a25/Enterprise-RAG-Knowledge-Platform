"""
Document ingestion service.

Orchestrates the full pipeline that runs after a file is uploaded:
extract text -> chunk -> embed -> store vectors in Qdrant + metadata in
Postgres. Runs synchronously in a FastAPI BackgroundTask for this build;
swapping to a Celery/RQ worker queue later only means moving the call
to `process_document` behind a task broker instead of a BackgroundTask.
"""
import os
import uuid
from pathlib import Path

from loguru import logger
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.document import Document, DocumentStatus
from app.crud import document as document_crud
from app.rag.ingestion.loaders import load_document, UnsupportedFileTypeError
from app.rag.ingestion.chunker import chunk_text
from app.rag.embeddings.embedder import get_embedder
from app.rag.retriever.vector_store import upsert_chunks, delete_by_document
from app.database.session import SessionLocal

settings = get_settings()


def save_upload(file_bytes: bytes, original_filename: str, owner_id: uuid.UUID) -> tuple[str, str]:
    """Persists the raw upload to disk and returns (stored_path, file_type)."""
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    ext = Path(original_filename).suffix.lower()
    stored_name = f"{owner_id}_{uuid.uuid4()}{ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_name)
    with open(stored_path, "wb") as f:
        f.write(file_bytes)
    return stored_path, ext.lstrip(".") or "unknown"


def process_document(document_id: uuid.UUID) -> None:
    """
    Runs in a background task with its own DB session (the request's
    session is closed by the time the background task executes).
    """
    db: Session = SessionLocal()
    try:
        document = document_crud.get_document(db, document_id)
        if document is None:
            logger.warning(f"process_document: document {document_id} not found")
            return

        document_crud.update_status(db, document, DocumentStatus.PROCESSING)

        try:
            pages = load_document(document.file_path)
        except UnsupportedFileTypeError as exc:
            document_crud.update_status(db, document, DocumentStatus.FAILED, str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Extraction failed for {document_id}")
            document_crud.update_status(db, document, DocumentStatus.FAILED, f"Extraction error: {exc}")
            return

        strategy = "markdown" if document.file_type == "md" else "recursive"

        chunk_records: list[dict] = []
        for page_number, page_text in pages:
            for idx, chunk in enumerate(chunk_text(page_text, strategy=strategy)):
                chunk_records.append({
                    "content": chunk,
                    "chunk_index": len(chunk_records) + idx,
                    "page_number": page_number,
                    "token_count": len(chunk.split()),
                })

        if not chunk_records:
            document_crud.update_status(db, document, DocumentStatus.FAILED, "No extractable text found in document.")
            return

        chunk_rows = document_crud.add_chunks(db, document_id, chunk_records)

        try:
            embedder = get_embedder()
            vectors = embedder.embed_texts([row.content for row in chunk_rows])
            payloads = [
                {
                    "document_id": str(document.id),
                    "owner_id": str(document.owner_id),
                    "content": row.content,
                    "page_number": row.page_number,
                }
                for row in chunk_rows
            ]
            upsert_chunks([row.id for row in chunk_rows], vectors, payloads)
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"Embedding/indexing failed for {document_id}")
            document_crud.update_status(db, document, DocumentStatus.FAILED, f"Indexing error: {exc}")
            return

        document_crud.update_status(db, document, DocumentStatus.INDEXED)
        logger.info(f"Document {document_id} indexed with {len(chunk_rows)} chunks")
    finally:
        db.close()


def delete_document_fully(db: Session, document: Document) -> None:
    delete_by_document(document.id)
    try:
        os.remove(document.file_path)
    except OSError:
        pass
    document_crud.delete_document(db, document)
