from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import User, WeekPlan
from backend.app.schemas import WeekPlanOut, WeekPlanUpsert

router = APIRouter()


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _plan_to_out(plan: WeekPlan | None, user: User, week_start: str) -> WeekPlanOut:
    if plan is None:
        return WeekPlanOut(
            id=None,
            user_id=user.id,
            week_start=week_start,
            water_target_ml=user.default_water_ml,
            meal_mode="three_main",
            workout_mode="any",
            workout_cardio_min=None,
            workout_strength_sets=None,
        )
    return WeekPlanOut(
        id=plan.id,
        user_id=plan.user_id,
        week_start=plan.week_start,
        water_target_ml=plan.water_target_ml,
        meal_mode=plan.meal_mode,
        workout_mode=plan.workout_mode,
        workout_cardio_min=plan.workout_cardio_min,
        workout_strength_sets=plan.workout_strength_sets,
    )


def _plan_dict(plan: WeekPlan | None, user: User) -> dict:
    if plan is None:
        return {}
    return {
        "water_target_ml": plan.water_target_ml,
        "meal_mode": plan.meal_mode,
        "workout_mode": plan.workout_mode,
        "workout_cardio_min": plan.workout_cardio_min,
        "workout_strength_sets": plan.workout_strength_sets,
    }


def get_week_plan_for_user(user: User, day: str, db: Session) -> WeekPlan | None:
    week_start = monday_of(date.fromisoformat(day)).isoformat()
    return (
        db.query(WeekPlan)
        .filter(WeekPlan.user_id == user.id, WeekPlan.week_start == week_start)
        .first()
    )


def plan_as_dict(plan: WeekPlan | None, user: User) -> dict:
    return _plan_dict(plan, user)


@router.get("")
def get_week_plan(
    week_start: str = Query(..., description="YYYY-MM-DD, normalized to Monday"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeekPlanOut:
    mon = monday_of(date.fromisoformat(week_start)).isoformat()
    plan = (
        db.query(WeekPlan)
        .filter(WeekPlan.user_id == user.id, WeekPlan.week_start == mon)
        .first()
    )
    return _plan_to_out(plan, user, mon)


@router.put("")
def upsert_week_plan(
    body: WeekPlanUpsert,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeekPlanOut:
    mon = monday_of(date.fromisoformat(body.week_start)).isoformat()
    plan = (
        db.query(WeekPlan)
        .filter(WeekPlan.user_id == user.id, WeekPlan.week_start == mon)
        .first()
    )
    if plan is None:
        plan = WeekPlan(user_id=user.id, week_start=mon)
        db.add(plan)
    plan.water_target_ml = body.water_target_ml
    plan.meal_mode = body.meal_mode
    plan.workout_mode = body.workout_mode
    plan.workout_cardio_min = body.workout_cardio_min
    plan.workout_strength_sets = body.workout_strength_sets
    db.commit()
    db.refresh(plan)
    return _plan_to_out(plan, user, mon)
