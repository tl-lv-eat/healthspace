from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import BodyMetric, User
from backend.app.schemas import BodyMetricCreate, BodyMetricOut
from backend.app.services.bmi import calc_bmi
from backend.app.settings import get_settings

router = APIRouter()


def _metric_to_out(row: BodyMetric) -> BodyMetricOut:
    created = (
        row.created_at.isoformat()
        if isinstance(row.created_at, datetime)
        else str(row.created_at)
    )
    bmi = None
    if row.weight_kg is not None and row.height_cm is not None:
        bmi = calc_bmi(row.weight_kg, row.height_cm)
    return BodyMetricOut(
        id=row.id,
        user_id=row.user_id,
        recorded_on=row.recorded_on,
        weight_kg=row.weight_kg,
        waist_cm=row.waist_cm,
        body_fat_pct=row.body_fat_pct,
        chest_cm=row.chest_cm,
        hip_cm=row.hip_cm,
        height_cm=row.height_cm,
        note=row.note,
        created_at=created,
        bmi=bmi,
    )


def _allowed_user_ids() -> frozenset[str]:
    return frozenset(u.id for u in get_settings().users)


@router.post("")
def create_body_metric(
    body: BodyMetricCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BodyMetricOut:
    row = BodyMetric(
        user_id=user.id,
        recorded_on=body.recorded_on,
        weight_kg=body.weight_kg,
        waist_cm=body.waist_cm,
        body_fat_pct=body.body_fat_pct,
        chest_cm=body.chest_cm,
        hip_cm=body.hip_cm,
        height_cm=body.height_cm,
        note=body.note,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _metric_to_out(row)


@router.get("")
def list_body_metrics(
    user_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[BodyMetricOut]:
    target = user_id or user.id
    if target not in _allowed_user_ids():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    rows = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == target)
        .order_by(BodyMetric.recorded_on.asc(), BodyMetric.id.asc())
        .all()
    )
    return [_metric_to_out(r) for r in rows]


@router.get("/trend")
def body_trend(
    user_ids: str = Query(..., description="comma-separated user ids"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    allowed = _allowed_user_ids()
    ids = [x.strip() for x in user_ids.split(",") if x.strip()]
    for uid in ids:
        if uid not in allowed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {uid} not found")
    series = []
    for uid in ids:
        rows = (
            db.query(BodyMetric)
            .filter(BodyMetric.user_id == uid)
            .order_by(BodyMetric.recorded_on.asc())
            .all()
        )
        points = []
        for r in rows:
            bmi = None
            if r.weight_kg is not None and r.height_cm is not None:
                bmi = calc_bmi(r.weight_kg, r.height_cm)
            points.append(
                {
                    "date": r.recorded_on,
                    "weight_kg": r.weight_kg,
                    "bmi": bmi,
                }
            )
        series.append({"user_id": uid, "points": points})
    return {"series": series}
