from __future__ import annotations

import json
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import Achievement, User, UserAchievement
from backend.app.services.achievement_eval import (
    achievement_applies_to_user,
    eval_progress,
    user_achievement_status,
)
from backend.app.services.points import grant
from backend.app.settings import get_settings

router = APIRouter()

AchievementScope = Literal["shared", "persona"]
AchievementMetric = Literal[
    "green_days_total",
    "green_streak",
    "workout_sessions",
    "workout_minutes_total",
    "water_ok_days",
    "bmi_in_range",
    "body_fat_max",
]
MineStatus = Literal["incomplete", "claimable", "claimed"]


class AchievementCreate(BaseModel):
    slug: str = Field(..., min_length=1, max_length=64)
    title: str
    description: str = ""
    scope: AchievementScope = "shared"
    metric: AchievementMetric
    target_value: float = Field(..., gt=0)
    points_reward: int = Field(..., gt=0)
    rule_json: dict = Field(default_factory=dict)
    bind_user_id: str | None = None
    bind_sex: str | None = None
    sort_order: int = 0
    enabled: bool = True


class AchievementPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    scope: AchievementScope | None = None
    metric: AchievementMetric | None = None
    target_value: float | None = Field(default=None, gt=0)
    points_reward: int | None = Field(default=None, gt=0)
    rule_json: dict | None = None
    bind_user_id: str | None = None
    bind_sex: str | None = None
    sort_order: int | None = None
    enabled: bool | None = None


class AchievementOut(BaseModel):
    id: int
    slug: str
    title: str
    description: str
    scope: str
    metric: str
    target_value: float
    points_reward: int
    rule_json: dict
    bind_user_id: str | None
    bind_sex: str | None
    sort_order: int
    enabled: bool


class MineAchievementOut(BaseModel):
    achievement: AchievementOut
    progress: float
    target: float
    status: MineStatus
    claimed_at: str | None


class MineAchievementsResponse(BaseModel):
    incomplete: list[MineAchievementOut]
    claimable: list[MineAchievementOut]
    claimed: list[MineAchievementOut]


def _allowed_user_ids() -> frozenset[str]:
    return frozenset(u.id for u in get_settings().users)


def _parse_rule(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _achievement_to_out(row: Achievement) -> AchievementOut:
    return AchievementOut(
        id=row.id,
        slug=row.slug,
        title=row.title,
        description=row.description,
        scope=row.scope,
        metric=row.metric,
        target_value=float(row.target_value),
        points_reward=int(row.points_reward),
        rule_json=_parse_rule(row.rule_json),
        bind_user_id=row.bind_user_id,
        bind_sex=row.bind_sex,
        sort_order=int(row.sort_order),
        enabled=bool(row.enabled),
    )


def _claimed_map(db: Session, user_id: str) -> dict[int, UserAchievement]:
    rows = db.query(UserAchievement).filter(UserAchievement.user_id == user_id).all()
    return {r.achievement_id: r for r in rows}


def _build_mine_item(
    user: User,
    ach: Achievement,
    db: Session,
    claimed_rows: dict[int, UserAchievement],
) -> MineAchievementOut | None:
    if not achievement_applies_to_user(ach, user, db):
        return None
    progress = eval_progress(user, ach, db)
    target = float(ach.target_value)
    claim_row = claimed_rows.get(ach.id)
    claimed = claim_row is not None
    st = user_achievement_status(
        progress=progress,
        target=target,
        metric=ach.metric,
        claimed=claimed,
    )
    claimed_at = None
    if claim_row is not None:
        claimed_at = (
            claim_row.claimed_at.isoformat()
            if isinstance(claim_row.claimed_at, datetime)
            else str(claim_row.claimed_at)
        )
    return MineAchievementOut(
        achievement=_achievement_to_out(ach),
        progress=round(progress, 2),
        target=target,
        status=st,
        claimed_at=claimed_at,
    )


@router.get("", response_model=list[AchievementOut])
def list_catalog(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AchievementOut]:
    del user
    rows = (
        db.query(Achievement)
        .filter(Achievement.enabled.is_(True))
        .order_by(Achievement.sort_order.asc(), Achievement.id.asc())
        .all()
    )
    return [_achievement_to_out(r) for r in rows]


@router.get("/mine", response_model=MineAchievementsResponse)
def list_mine(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MineAchievementsResponse:
    rows = db.query(Achievement).order_by(Achievement.sort_order.asc(), Achievement.id.asc()).all()
    claimed_rows = _claimed_map(db, user.id)
    incomplete: list[MineAchievementOut] = []
    claimable: list[MineAchievementOut] = []
    claimed: list[MineAchievementOut] = []
    for ach in rows:
        if not ach.enabled and ach.id not in claimed_rows:
            continue
        item = _build_mine_item(user, ach, db, claimed_rows)
        if item is None:
            continue
        if item.status == "incomplete":
            incomplete.append(item)
        elif item.status == "claimable":
            claimable.append(item)
        else:
            claimed.append(item)
    return MineAchievementsResponse(incomplete=incomplete, claimable=claimable, claimed=claimed)


@router.post("/{achievement_id}/claim", response_model=MineAchievementOut)
def claim_achievement(
    achievement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MineAchievementOut:
    ach = db.get(Achievement, achievement_id)
    if ach is None or not ach.enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    if not achievement_applies_to_user(ach, user, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Achievement not found")
    claimed_rows = _claimed_map(db, user.id)
    progress = eval_progress(user, ach, db)
    target = float(ach.target_value)
    if ach.id in claimed_rows:
        return _build_mine_item(user, ach, db, claimed_rows)  # type: ignore[return-value]
    from backend.app.services.achievement_eval import is_target_met

    if not is_target_met(progress, target, ach.metric):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not claimable yet")
    idem = f"{user.id}:achievement:{ach.id}:claim"
    grant(
        db,
        user.id,
        int(ach.points_reward),
        "achievement_claim",
        idem,
        meta={"achievement_id": ach.id, "slug": ach.slug},
    )
    row = UserAchievement(user_id=user.id, achievement_id=ach.id)
    db.add(row)
    db.commit()
    db.refresh(row)
    claimed_rows = _claimed_map(db, user.id)
    item = _build_mine_item(user, ach, db, claimed_rows)
    assert item is not None
    return item


@router.post("", response_model=AchievementOut, status_code=status.HTTP_201_CREATED)
def create_achievement(
    body: AchievementCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AchievementOut:
    del user
    if body.bind_user_id and body.bind_user_id not in _allowed_user_ids():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bind_user_id")
    existing = db.query(Achievement).filter(Achievement.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already exists")
    if body.metric in ("bmi_in_range", "body_fat_max") and body.target_value != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Persona boolean metrics use target_value=1",
        )
    row = Achievement(
        slug=body.slug,
        title=body.title,
        description=body.description,
        scope=body.scope,
        metric=body.metric,
        target_value=float(body.target_value),
        points_reward=int(body.points_reward),
        rule_json=json.dumps(body.rule_json, ensure_ascii=False),
        bind_user_id=body.bind_user_id,
        bind_sex=body.bind_sex,
        sort_order=int(body.sort_order),
        enabled=body.enabled,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _achievement_to_out(row)


@router.patch("/{achievement_id}", response_model=AchievementOut)
def patch_achievement(
    achievement_id: int,
    body: AchievementPatch,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AchievementOut:
    del user
    row = db.get(Achievement, achievement_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    data = body.model_dump(exclude_unset=True)
    if "bind_user_id" in data and data["bind_user_id"] not in _allowed_user_ids():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid bind_user_id")
    if "rule_json" in data and data["rule_json"] is not None:
        data["rule_json"] = json.dumps(data["rule_json"], ensure_ascii=False)
    for key, val in data.items():
        setattr(row, key, val)
    db.commit()
    db.refresh(row)
    return _achievement_to_out(row)


@router.delete("/{achievement_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_achievement(
    achievement_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    del user
    row = db.get(Achievement, achievement_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    db.delete(row)
    db.commit()
