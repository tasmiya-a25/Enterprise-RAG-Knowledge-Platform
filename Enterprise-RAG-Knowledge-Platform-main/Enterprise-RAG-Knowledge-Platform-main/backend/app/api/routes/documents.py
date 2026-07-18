import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.document import DocumentOut, DocumentListResponse
from app.crud import document as document_crud
from app.services.document_service import save_upload, process_document, delete_document_fully
from app.config.settings import get_settings

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@router.post("/upload", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Supported: {sorted(SUPPORTED_EXTENSIONS)}",
        )

    contents = await file.read()
    size_mb = len(contents) / (1024 * 1024)
    if size_mb > settings.MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max upload size of {settings.MAX_UPLOAD_MB}MB",
        )

    stored_path, file_type = save_upload(contents, file.filename, current_user.id)
    document = document_crud.create_document(
        db, filename=file.filename, file_path=stored_path, file_type=file_type,
        size_bytes=len(contents), owner_id=current_user.id,
    )

    background_tasks.add_task(process_document, document.id)
    return document


@router.get("", response_model=DocumentListResponse)
def list_documents(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    docs = document_crud.list_documents(db, current_user.id)
    return DocumentListResponse(documents=docs, total=len(docs))


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = document_crud.get_document(db, document_id)
    if not document or document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    document = document_crud.get_document(db, document_id)
    if not document or document.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    delete_document_fully(db, document)
    return None
