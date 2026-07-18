import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, Chunk, DocumentStatus


def create_document(db: Session, *, filename: str, file_path: str, file_type: str,
                     size_bytes: int, owner_id: uuid.UUID) -> Document:
    doc = Document(filename=filename, file_path=file_path, file_type=file_type,
                    size_bytes=size_bytes, owner_id=owner_id, status=DocumentStatus.PENDING)
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, document_id: uuid.UUID) -> Document | None:
    return db.get(Document, document_id)


def list_documents(db: Session, owner_id: uuid.UUID) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.owner_id == owner_id).order_by(Document.created_at.desc())))


def update_status(db: Session, document: Document, status: DocumentStatus, error_message: str | None = None) -> Document:
    document.status = status
    document.error_message = error_message
    if status == DocumentStatus.INDEXED:
        from datetime import datetime, timezone
        document.indexed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    return document


def delete_document(db: Session, document: Document) -> None:
    db.delete(document)
    db.commit()


def add_chunks(db: Session, document_id: uuid.UUID, chunks: list[dict]) -> list[Chunk]:
    """chunks: list of {"content", "chunk_index", "page_number", "token_count"}"""
    rows = [
        Chunk(
            document_id=document_id,
            content=c["content"],
            chunk_index=c["chunk_index"],
            page_number=c.get("page_number"),
            token_count=c.get("token_count", 0),
        )
        for c in chunks
    ]
    db.add_all(rows)
    db.commit()
    for r in rows:
        db.refresh(r)
    return rows


def get_chunks_by_ids(db: Session, chunk_ids: list[uuid.UUID]) -> list[Chunk]:
    return list(db.scalars(select(Chunk).where(Chunk.id.in_(chunk_ids))))
