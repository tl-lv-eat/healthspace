from __future__ import annotations

from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import PointsLedger, User
from backend.app.services.points import get_balance
from backend.app.services.points_rules import evaluate_points_for_day

router = APIRouter()


class PointsEvaluateIn(BaseModel):
    date: str


@router.get("/balance")
def points_balance(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    return {"balance": get_balance(db, user.id)}


@router.get("/ledger")
def points_ledger(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = (
        db.query(PointsLedger)
        .filter(PointsLedger.user_id == user.id)
        .order_by(PointsLedger.created_at.desc(), PointsLedger.id.desc())
        .limit(100)
        .all()
    )
    out = []
    for r in rows:
        created = r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at)
        out.append(
            {
                "id": r.id,
                "delta": r.delta,
                "reason": r.reason,
                "created_at": created,
            }
        )
    return out


@router.post("/evaluate")
def points_evaluate(
    body: PointsEvaluateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    day = date.fromisoformat(body.date)
    return evaluate_points_for_day(db, user.id, day)
