import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.document import DocumentStatus


class DocumentOut(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    size_bytes: int
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime
    indexed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentListResponse(BaseModel):
    documents: list[DocumentOut]
    total: int
