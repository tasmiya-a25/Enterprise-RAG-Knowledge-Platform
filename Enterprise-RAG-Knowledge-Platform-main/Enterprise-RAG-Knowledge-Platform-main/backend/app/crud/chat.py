import uuid
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import Chat, Message, MessageRole


def create_chat(db: Session, user_id: uuid.UUID, title: str = "New chat") -> Chat:
    chat = Chat(user_id=user_id, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def get_chat(db: Session, chat_id: uuid.UUID, user_id: uuid.UUID) -> Chat | None:
    return db.scalar(select(Chat).where(Chat.id == chat_id, Chat.user_id == user_id))


def list_chats(db: Session, user_id: uuid.UUID) -> list[Chat]:
    return list(db.scalars(select(Chat).where(Chat.user_id == user_id).order_by(Chat.updated_at.desc())))


def delete_chat(db: Session, chat: Chat) -> None:
    db.delete(chat)
    db.commit()


def add_message(db: Session, chat_id: uuid.UUID, role: MessageRole, content: str,
                 citations: list | None = None, latency_ms: int | None = None) -> Message:
    msg = Message(chat_id=chat_id, role=role, content=content, citations=citations, latency_ms=latency_ms)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg
