"""
End-to-end RAG pipeline:

  question -> hybrid retrieval -> rerank -> prompt construction
  -> generation -> citation assembly

This module is the single entry point the chat service calls; it hides
all the retrieval/rerank/generation wiring behind one function.
"""
import uuid
from sqlalchemy.orm import Session

from app.rag.retriever.hybrid import hybrid_search
from app.rag.generation import generate_answer
from app.models.document import Document


def answer_question(db: Session, *, question: str, owner_id: uuid.UUID,
                     document_ids: list[uuid.UUID] | None = None,
                     history: list[dict] | None = None) -> dict:
    """
    Returns: {"answer": str, "citations": [{"document_id", "document_name",
              "chunk_id", "page_number", "score"}, ...]}
    """
    history = history or []

    ranked_chunks = hybrid_search(db, question, owner_id, document_ids)

    # Attach human-readable document names for the prompt + citations.
    doc_ids = {c["document_id"] for c in ranked_chunks}
    docs_by_id = {}
    if doc_ids:
        docs = db.query(Document).filter(Document.id.in_([uuid.UUID(d) for d in doc_ids])).all()
        docs_by_id = {str(d.id): d.filename for d in docs}

    for c in ranked_chunks:
        c["document_name"] = docs_by_id.get(c["document_id"], "unknown document")

    answer_text = generate_answer(question, ranked_chunks, history)

    citations = [
        {
            "document_id": c["document_id"],
            "document_name": c["document_name"],
            "chunk_id": c["chunk_id"],
            "page_number": c.get("page_number"),
            "score": round(float(c.get("rerank_score", c.get("fusion_score", 0.0))), 4),
        }
        for c in ranked_chunks
    ]

    return {"answer": answer_text, "citations": citations}
