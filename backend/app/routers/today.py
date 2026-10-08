from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.completion import meal_done, water_done, workout_done
from backend.app.db import get_db
from backend.app.models import Meal, User, WaterEntry, Workout
from backend.app.routers.week_plans import get_week_plan_for_user, plan_as_dict
from backend.app.services.week_rules import _workout_done_extended, effective_rules
from backend.app.routers.meals import _meal_to_out
from backend.app.routers.workouts import _workout_to_out

router = APIRouter()


def _get_partner(user: User, db: Session) -> User:
    partner = db.query(User).filter(User.id != user.id).first()
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return partner


def _day_meals(user_id: str, date: str, db: Session) -> list[Meal]:
    return (
        db.query(Meal)
        .filter(Meal.user_id == user_id, Meal.date == date)
        .order_by(Meal.created_at.asc())
        .all()
    )


def _day_workouts(user_id: str, date: str, db: Session) -> list[Workout]:
    return (
        db.query(Workout)
        .filter(Workout.user_id == user_id, Workout.date == date)
        .order_by(Workout.created_at.asc())
        .all()
    )


def _water_target(user: User, date: str, db: Session) -> int:
    plan = get_week_plan_for_user(user, date, db)
    rules = effective_rules(plan_as_dict(plan, user), user.default_water_ml)
    return rules["water_target_ml"]


def _water_totals(user: User, date: str, db: Session) -> tuple[int, int]:
    rows = db.query(WaterEntry).filter(WaterEntry.user_id == user.id, WaterEntry.date == date).all()
    total_ml = sum(e.amount_ml for e in rows)
    return total_ml, _water_target(user, date, db)


def _done_flags(
    user: User,
    date: str,
    meals: list[Meal],
    total_ml: int,
    workouts: list[Workout],
    db: Session,
) -> dict[str, bool]:
    plan = get_week_plan_for_user(user, date, db)
    rules = effective_rules(plan_as_dict(plan, user), user.default_water_ml)
    meal_dicts = [{"meal_type": m.meal_type} for m in meals]
    workout_dicts = []
    for w in workouts:
        try:
            payload = json.loads(w.payload) if w.payload else {}
        except json.JSONDecodeError:
            payload = {}
        workout_dicts.append({"kind": w.kind, "payload": payload})
    return {
        "meal": meal_done(meal_dicts, rules["meal_rule"]),
        "water": water_done(total_ml, rules["water_target_ml"]),
        "workout": _workout_done_extended(workout_dicts, rules["workout_rule"]),
    }


def _build_me_section(user: User, date: str, db: Session) -> dict:
    meals = _day_meals(user.id, date, db)
    workouts = _day_workouts(user.id, date, db)
    total_ml, target_ml = _water_totals(user, date, db)
    done = _done_flags(user, date, meals, total_ml, workouts, db)
    return {
        "user_id": user.id,
        "meals": [_meal_to_out(m).model_dump() for m in meals],
        "water": {"total_ml": total_ml, "target_ml": target_ml, "done": done["water"]},
        "workouts": [_workout_to_out(w).model_dump() for w in workouts],
        "done": done,
    }


def _build_partner_section(partner: User, date: str, db: Session) -> dict:
    meals = _day_meals(partner.id, date, db)
    workouts = _day_workouts(partner.id, date, db)
    total_ml, target_ml = _water_totals(partner, date, db)
    done = _done_flags(partner, date, meals, total_ml, workouts, db)
    return {
        "user_id": partner.id,
        "display_name": partner.display_name,
        "done": done,
        "water_total_ml": total_ml,
        "water_target_ml": target_ml,
    }


@router.get("")
def get_today(
    date: str = Query(..., description="YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    partner = _get_partner(user, db)
    return {
        "date": date,
        "me": _build_me_section(user, date, db),
        "partner": _build_partner_section(partner, date, db),
    }
