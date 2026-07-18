import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class Citation(BaseModel):
    document_id: str
    document_name: str
    chunk_id: str
    page_number: int | None = None
    score: float


class ChatRequest(BaseModel):
    message: str
    chat_id: uuid.UUID | None = None  # None = start a new chat
    document_ids: list[uuid.UUID] | None = None  # optional filter to specific docs


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    citations: list[Citation] | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatResponse(BaseModel):
    chat_id: uuid.UUID
    message: MessageOut


class ChatSummary(BaseModel):
    id: uuid.UUID
    title: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatHistoryResponse(BaseModel):
    chat_id: uuid.UUID
    title: str
    messages: list[MessageOut]
