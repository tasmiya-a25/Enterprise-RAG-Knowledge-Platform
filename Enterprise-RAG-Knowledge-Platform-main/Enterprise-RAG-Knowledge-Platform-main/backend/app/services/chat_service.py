"""
Chat service: manages chat/message persistence around the RAG pipeline.
"""
import time
import uuid
from sqlalchemy.orm import Session

from app.crud import chat as chat_crud
from app.models.chat import MessageRole
from app.rag.pipeline import answer_question


def _make_title(message: str) -> str:
    words = message.strip().split()
    title = " ".join(words[:8])
    return title[:255] if title else "New chat"


def handle_chat_message(db: Session, *, user_id: uuid.UUID, message: str,
                         chat_id: uuid.UUID | None, document_ids: list[uuid.UUID] | None):
    chat = chat_crud.get_chat(db, chat_id, user_id) if chat_id else None
    if chat is None:
        chat = chat_crud.create_chat(db, user_id, title=_make_title(message))

    history = [{"role": m.role.value, "content": m.content} for m in chat.messages]

    chat_crud.add_message(db, chat.id, MessageRole.USER, message)

    start = time.perf_counter()
    result = answer_question(db, question=message, owner_id=user_id, document_ids=document_ids, history=history)
    latency_ms = int((time.perf_counter() - start) * 1000)

    assistant_message = chat_crud.add_message(
        db, chat.id, MessageRole.ASSISTANT, result["answer"],
        citations=result["citations"], latency_ms=latency_ms,
    )

    return chat.id, assistant_message
