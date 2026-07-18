import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.chat import Feedback

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackIn(BaseModel):
    message_id: uuid.UUID
    rating: int = Field(ge=-1, le=1)
    comment: str | None = None


@router.post("", status_code=201)
def submit_feedback(payload: FeedbackIn, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fb = Feedback(message_id=payload.message_id, user_id=current_user.id,
                  rating=payload.rating, comment=payload.comment)
    db.add(fb)
    db.commit()
    return {"status": "recorded"}
