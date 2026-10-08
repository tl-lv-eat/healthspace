"""Load one user's meals/water/workouts/done for a calendar day."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.app.models import Meal, User, WaterEntry, Workout
from backend.app.routers.week_plans import get_week_plan_for_user, plan_as_dict
from backend.app.services.week_rules import day_status, effective_rules


def _day_meals(user_id: str, day: str, db: Session) -> list[dict]:
    rows = (
        db.query(Meal)
        .filter(Meal.user_id == user_id, Meal.date == day)
        .order_by(Meal.created_at.asc())
        .all()
    )
    return [
        {
            "meal_type": m.meal_type,
            "user_kcal": m.user_kcal,
            "food_summary": m.food_summary,
        }
        for m in rows
    ]


def _day_workouts(user_id: str, day: str, db: Session) -> list[dict]:
    rows = (
        db.query(Workout)
        .filter(Workout.user_id == user_id, Workout.date == day)
        .order_by(Workout.created_at.asc())
        .all()
    )
    out = []
    for w in rows:
        try:
            payload = json.loads(w.payload) if w.payload else {}
        except json.JSONDecodeError:
            payload = {}
        out.append({"kind": w.kind, "payload": payload})
    return out


def _water_total(user_id: str, day: str, db: Session) -> int:
    rows = db.query(WaterEntry).filter(WaterEntry.user_id == user_id, WaterEntry.date == day).all()
    return sum(e.amount_ml for e in rows)


def get_user_day_snapshot(db: Session, user: User, day: str) -> dict:
    plan = get_week_plan_for_user(user, day, db)
    rules = effective_rules(plan_as_dict(plan, user), user.default_water_ml)
    meals = _day_meals(user.id, day, db)
    workouts = _day_workouts(user.id, day, db)
    total_ml = _water_total(user.id, day, db)
    meal_dicts = [{"meal_type": m["meal_type"]} for m in meals]
    done = day_status(meal_dicts, total_ml, workouts, rules)
    return {
        "date": day,
        "meals": meals,
        "water": {"total_ml": total_ml, "target_ml": rules["water_target_ml"]},
        "workouts": workouts,
        "done": {"meal": done["meal"], "water": done["water"], "workout": done["workout"]},
    }


def week_period_key(week_start_monday: str) -> str:
    from datetime import date

    d = date.fromisoformat(week_start_monday)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"
