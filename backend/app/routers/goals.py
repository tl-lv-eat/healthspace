from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import BodyMetric, Goal, User
from backend.app.services.goals_progress import refresh_goal_progress
from backend.app.settings import get_settings

router = APIRouter()

GOAL_KINDS = frozenset({"short", "long"})
GOAL_METRICS = frozenset({"weight_kg", "workout_days", "custom"})
GOAL_STATUSES = frozenset({"active", "done", "cancelled"})


class GoalCreate(BaseModel):
    kind: str
    title: str
    description: str = ""
    metric: str
    target_value: float
    unit: str = ""
    start_date: str
    end_date: str | None = None


class GoalPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    target_value: float | None = None
    end_date: str | None = None
    status: str | None = None
    current_value: float | None = None


class GoalOut(BaseModel):
    id: int
    user_id: str
    kind: str
    title: str
    description: str
    metric: str
    target_value: float
    current_value: float
    unit: str
    start_date: str
    end_date: str | None
    status: str
    created_at: str


def _goal_to_out(goal: Goal) -> GoalOut:
    created = goal.created_at.isoformat() if isinstance(goal.created_at, datetime) else str(goal.created_at)
    return GoalOut(
        id=goal.id,
        user_id=goal.user_id,
        kind=goal.kind,
        title=goal.title,
        description=goal.description,
        metric=goal.metric,
        target_value=goal.target_value,
        current_value=goal.current_value,
        unit=goal.unit,
        start_date=goal.start_date,
        end_date=goal.end_date,
        status=goal.status,
        created_at=created,
    )


def _allowed_user_ids() -> frozenset[str]:
    return frozenset(u.id for u in get_settings().users)


def _baseline_weight(db: Session, user_id: str, target: float) -> float:
    row = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id, BodyMetric.weight_kg.isnot(None))
        .order_by(BodyMetric.recorded_on.desc(), BodyMetric.id.desc())
        .first()
    )
    if row and row.weight_kg is not None:
        return float(row.weight_kg)
    return float(target)


@router.post("")
def create_goal(
    body: GoalCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalOut:
    if body.kind not in GOAL_KINDS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid kind")
    if body.metric not in GOAL_METRICS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid metric")
    meta: dict = {}
    if body.metric == "weight_kg":
        meta["baseline_weight"] = _baseline_weight(db, user.id, body.target_value)
    goal = Goal(
        user_id=user.id,
        kind=body.kind,
        title=body.title.strip(),
        description=body.description,
        metric=body.metric,
        target_value=body.target_value,
        current_value=0,
        unit=body.unit,
        start_date=body.start_date,
        end_date=body.end_date,
        meta_json=json.dumps(meta, ensure_ascii=False),
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    refresh_goal_progress(db, goal)
    db.refresh(goal)
    return _goal_to_out(goal)


@router.get("")
def list_goals(
    scope: str = Query(default="mine"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GoalOut]:
    allowed = _allowed_user_ids()
    q = db.query(Goal).filter(Goal.user_id.in_(allowed))
    if scope == "mine":
        q = q.filter(Goal.user_id == user.id)
    elif scope != "all":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="scope must be mine or all")
    rows = q.order_by(Goal.created_at.desc()).all()
    return [_goal_to_out(g) for g in rows]


def _get_goal(goal_id: int, db: Session) -> Goal:
    goal = db.get(Goal, goal_id)
    if goal is None or goal.user_id not in _allowed_user_ids():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found")
    return goal


@router.patch("/{goal_id}")
def patch_goal(
    goal_id: int,
    body: GoalPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalOut:
    goal = _get_goal(goal_id, db)
    if goal.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your goal")
    if body.title is not None:
        goal.title = body.title.strip()
    if body.description is not None:
        goal.description = body.description
    if body.target_value is not None:
        goal.target_value = body.target_value
    if body.end_date is not None:
        goal.end_date = body.end_date
    if body.status is not None:
        if body.status not in GOAL_STATUSES:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status")
        goal.status = body.status
    if body.current_value is not None:
        if goal.metric != "custom":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only custom goals allow manual progress")
        goal.current_value = body.current_value
    db.commit()
    db.refresh(goal)
    return _goal_to_out(goal)


@router.post("/{goal_id}/refresh")
def refresh_goal(
    goal_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalOut:
    goal = _get_goal(goal_id, db)
    if goal.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your goal")
    refresh_goal_progress(db, goal)
    db.refresh(goal)
    return _goal_to_out(goal)
