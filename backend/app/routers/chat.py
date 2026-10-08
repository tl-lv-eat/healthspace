from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import ChatMessage, User
from backend.app.services.chat_coach import ChatError, chat_reply

router = APIRouter()


class ChatIn(BaseModel):
    message: str = Field(..., min_length=1)


class ChatOut(BaseModel):
    reply: str


class HistoryMessage(BaseModel):
    id: int
    role: str
    content: str
    created_at: str


class HistoryOut(BaseModel):
    messages: list[HistoryMessage]


@router.post("")
def post_chat(
    body: ChatIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatOut:
    try:
        reply = chat_reply(db, user, body.message)
    except ChatError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return ChatOut(reply=reply)


@router.get("/history")
def get_history(
    limit: int = Query(50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HistoryOut:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    rows = list(reversed(rows))
    return HistoryOut(
        messages=[
            HistoryMessage(
                id=r.id,
                role=r.role,
                content=r.content,
                created_at=r.created_at.isoformat() + "Z",
            )
            for r in rows
        ]
    )


@router.delete("/history")
def clear_history(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    db.query(ChatMessage).filter(ChatMessage.user_id == user.id).delete()
    db.commit()
    return {"ok": True}
