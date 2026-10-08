from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import User
from backend.app.services.pushplus import PushPlusError, get_or_create_binding, send_pushplus

router = APIRouter()


class PushSettingsOut(BaseModel):
    token: str
    enabled: bool
    remind_hours: list[int]
    last_success_at: str | None
    last_error: str | None


class PushSettingsIn(BaseModel):
    token: str | None = None
    enabled: bool | None = None
    remind_hours: list[int] | None = None


@router.get("/settings")
def get_settings_route(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PushSettingsOut:
    row = get_or_create_binding(db, user.id)
    hours = json.loads(row.remind_hours_json or "[12,21]")
    return PushSettingsOut(
        token=row.token,
        enabled=row.enabled,
        remind_hours=hours,
        last_success_at=row.last_success_at.isoformat() + "Z" if row.last_success_at else None,
        last_error=row.last_error,
    )


@router.put("/settings")
def put_settings(
    body: PushSettingsIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PushSettingsOut:
    row = get_or_create_binding(db, user.id)
    if body.token is not None:
        row.token = body.token.strip()
    if body.enabled is not None:
        row.enabled = body.enabled
    if body.remind_hours is not None:
        cleaned = sorted({int(h) for h in body.remind_hours if 0 <= int(h) <= 23})
        row.remind_hours_json = json.dumps(cleaned or [12, 21])
    db.commit()
    db.refresh(row)
    hours = json.loads(row.remind_hours_json)
    return PushSettingsOut(
        token=row.token,
        enabled=row.enabled,
        remind_hours=hours,
        last_success_at=row.last_success_at.isoformat() + "Z" if row.last_success_at else None,
        last_error=row.last_error,
    )


class TestBody(BaseModel):
    title: str = Field(default="双人减 · 测试")
    content: str = Field(default="PushPlus 绑定成功。")


@router.post("/test")
def test_push(
    body: TestBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    row = get_or_create_binding(db, user.id)
    if not (row.token or "").strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="token not set")
    try:
        send_pushplus(row.token.strip(), body.title, body.content)
    except PushPlusError as exc:
        row.last_error = str(exc)[:500]
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    row.last_error = None
    from datetime import datetime

    row.last_success_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
