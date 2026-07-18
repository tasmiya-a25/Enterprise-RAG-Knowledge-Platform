"""
Import all models here so Base.metadata is fully populated for
`Base.metadata.create_all()` and for Alembic autogeneration.
"""
from app.models.user import User, Organization, RoleEnum  # noqa: F401
from app.models.document import Document, Chunk, DocumentStatus  # noqa: F401
from app.models.chat import Chat, Message, Feedback, AuditLog, MessageRole  # noqa: F401
