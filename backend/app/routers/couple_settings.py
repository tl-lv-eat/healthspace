from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import CoupleSettings, User
from backend.app.services.couple_settings_service import get_or_create_couple_settings
from backend.app.services.settlement import settle_daily_for_date

router = APIRouter()


class CoupleSettingsOut(BaseModel):
    settle_hour: int
    points_daily_water: int
    points_daily_deficit: int
    points_daily_workout_40: int
    points_plan_tier_b: int
    points_plan_tier_a: int
    points_plan_tier_fail: int


class CoupleSettingsPatch(BaseModel):
    settle_hour: int | None = Field(default=None, ge=0, le=23)
    points_daily_water: int | None = None
    points_daily_deficit: int | None = None
    points_daily_workout_40: int | None = None
    points_plan_tier_b: int | None = None
    points_plan_tier_a: int | None = None
    points_plan_tier_fail: int | None = None


def _row_to_out(row: CoupleSettings) -> CoupleSettingsOut:
    return CoupleSettingsOut(
        settle_hour=row.settle_hour,
        points_daily_water=row.points_daily_water,
        points_daily_deficit=row.points_daily_deficit,
        points_daily_workout_40=row.points_daily_workout_40,
        points_plan_tier_b=row.points_plan_tier_b,
        points_plan_tier_a=row.points_plan_tier_a,
        points_plan_tier_fail=row.points_plan_tier_fail,
    )


@router.get("")
def get_couple_settings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoupleSettingsOut:
    _ = user
    return _row_to_out(get_or_create_couple_settings(db))


@router.patch("")
def patch_couple_settings(
    body: CoupleSettingsPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CoupleSettingsOut:
    _ = user
    row = get_or_create_couple_settings(db)
    data = body.model_dump(exclude_unset=True)
    if "settle_hour" in data and not (0 <= data["settle_hour"] <= 23):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="settle_hour must be 0-23")
    for key, value in data.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


@router.post("/settle")
def settle_daily(
    day: str = Query(..., alias="date", description="Calendar day to settle (YYYY-MM-DD)"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ = user
    try:
        settle_day = date.fromisoformat(day)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid date") from exc
    result = settle_daily_for_date(db, settle_day)
    db.commit()
    return result
