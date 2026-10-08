from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import Exercise, User
from backend.app.schemas import ExerciseCreate, ExerciseOut

router = APIRouter()

_SLUG_SAFE = re.compile(r"[^a-z0-9-]+")


def _slugify(text: str) -> str:
    base = text.strip().lower().replace(" ", "-")
    base = _SLUG_SAFE.sub("", base)
    return base or "exercise"


def _unique_custom_slug(db: Session, user_id: str, name_zh: str) -> str:
    stem = _slugify(name_zh)
    for _ in range(12):
        candidate = f"custom-{user_id}-{stem}-{uuid.uuid4().hex[:8]}"
        if db.query(Exercise).filter(Exercise.slug == candidate).first() is None:
            return candidate
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not allocate slug")


@router.get("", response_model=list[ExerciseOut])
def list_exercises(
    body_part: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ExerciseOut]:
    q = db.query(Exercise).filter(
        or_(Exercise.is_custom.is_(False), Exercise.owner_user_id == user.id)
    )
    if body_part:
        q = q.filter(Exercise.body_part == body_part)
    rows = q.order_by(Exercise.is_custom.asc(), Exercise.name_zh.asc()).all()
    return [ExerciseOut.model_validate(row) for row in rows]


@router.post("", response_model=ExerciseOut)
def create_custom_exercise(
    body: ExerciseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExerciseOut:
    if not body.name_zh.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="name_zh is required",
        )
    if not body.body_part.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="body_part is required",
        )
    slug = _unique_custom_slug(db, user.id, body.name_zh)
    row = Exercise(
        slug=slug,
        name_zh=body.name_zh.strip(),
        name_en=body.name_en.strip(),
        body_part=body.body_part.strip(),
        gif_url=body.gif_url.strip(),
        instructions_zh=body.instructions_zh.strip(),
        is_custom=True,
        owner_user_id=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ExerciseOut.model_validate(row)
