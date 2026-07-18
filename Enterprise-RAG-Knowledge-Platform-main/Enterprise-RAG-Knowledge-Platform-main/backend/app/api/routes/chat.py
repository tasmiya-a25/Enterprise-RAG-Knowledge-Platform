import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, MessageOut, ChatHistoryResponse, ChatSummary
from app.crud import chat as chat_crud
from app.services.chat_service import handle_chat_message

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def ask(payload: ChatRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat_id, message = handle_chat_message(
        db, user_id=current_user.id, message=payload.message,
        chat_id=payload.chat_id, document_ids=payload.document_ids,
    )
    return ChatResponse(chat_id=chat_id, message=MessageOut.model_validate(message))


@router.get("/history", response_model=list[ChatSummary])
def list_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return chat_crud.list_chats(db, current_user.id)


@router.get("/{chat_id}", response_model=ChatHistoryResponse)
def get_chat_detail(chat_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = chat_crud.get_chat(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    return ChatHistoryResponse(
        chat_id=chat.id, title=chat.title,
        messages=[MessageOut.model_validate(m) for m in chat.messages],
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(chat_id: uuid.UUID, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chat = chat_crud.get_chat(db, chat_id, current_user.id)
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    chat_crud.delete_chat(db, chat)
    return None
