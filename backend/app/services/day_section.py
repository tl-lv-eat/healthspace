"""Shared full-day payload for Today and calendar day detail."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.orm import Session

from backend.app.completion import meal_done, water_done
from backend.app.models import Meal, User, WaterEntry, WeekPlan, Workout
from backend.app.routers.meals import _meal_to_out
from backend.app.routers.week_plans import get_week_plan_for_user, plan_as_dict
from backend.app.routers.workouts import _workout_to_out
from backend.app.services.energy import daily_energy_snapshot, user_bmr
from backend.app.services.week_rules import _workout_done_extended, effective_rules


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


def _day_water_entries(user_id: str, date: str, db: Session) -> list[WaterEntry]:
    return (
        db.query(WaterEntry)
        .filter(WaterEntry.user_id == user_id, WaterEntry.date == date)
        .order_by(WaterEntry.created_at.asc())
        .all()
    )


def _water_entry_dict(entry: WaterEntry) -> dict:
    created = (
        entry.created_at.isoformat()
        if isinstance(entry.created_at, datetime)
        else str(entry.created_at)
    )
    return {"id": entry.id, "amount_ml": entry.amount_ml, "created_at": created}


def _workout_payload_dicts(workouts: list[Workout]) -> list[dict]:
    out: list[dict] = []
    for w in workouts:
        try:
            payload = json.loads(w.payload) if w.payload else {}
        except json.JSONDecodeError:
            payload = {}
        out.append({"kind": w.kind, "payload": payload})
    return out


def _plan_block(plan: WeekPlan | None, plan_dict: dict) -> dict | None:
    if plan is None:
        return None
    return {
        "id": plan.id,
        "title": plan_dict.get("title"),
        "start_date": plan_dict.get("start_date"),
        "end_date": plan_dict.get("end_date"),
    }


def build_day_section(
    user: User,
    date: str,
    db: Session,
    *,
    display_name: str | None = None,
) -> dict:
    meals = _day_meals(user.id, date, db)
    workouts = _day_workouts(user.id, date, db)
    water_rows = _day_water_entries(user.id, date, db)
    total_ml = sum(e.amount_ml for e in water_rows)

    plan = get_week_plan_for_user(user, date, db)
    plan_dict = plan_as_dict(plan, user)
    rules = effective_rules(plan_dict, user.default_water_ml)
    target_ml = rules["water_target_ml"]

    meal_dicts = [{"meal_type": m.meal_type} for m in meals]
    workout_dicts = _workout_payload_dicts(workouts)
    done = {
        "meal": meal_done(meal_dicts, rules["meal_rule"]),
        "water": water_done(total_ml, target_ml),
        "workout": _workout_done_extended(workout_dicts, rules["workout_rule"]),
    }

    intake_kcal = sum(int(m.user_kcal or 0) for m in meals)
    bmr = user_bmr(user, db)
    snap = daily_energy_snapshot(
        intake_kcal=intake_kcal,
        workouts=workout_dicts,
        bmr=bmr,
        water_ml=total_ml,
        water_target_ml=target_ml,
        weekly_kcal_deficit=rules["weekly_kcal_deficit"],
        period_days=rules.get("period_days") or 7,
    )

    section: dict = {
        "user_id": user.id,
        "meals": [_meal_to_out(m).model_dump() for m in meals],
        "water": {
            "total_ml": total_ml,
            "target_ml": target_ml,
            "done": done["water"],
            "entries": [_water_entry_dict(e) for e in water_rows],
        },
        "workouts": [_workout_to_out(w).model_dump() for w in workouts],
        "done": done,
        "energy": {
            "intake_kcal": snap["intake_kcal"],
            "burn_kcal": snap["burn_kcal"],
            "bmr": snap["bmr"],
            "surplus_kcal": snap["surplus_kcal"],
            "daily_deficit_target": snap["daily_deficit_target"],
            "daily_kcal_cap": rules.get("daily_kcal_cap"),
            "water_target_ml": rules["water_target_ml"],
            "period_days": rules.get("period_days") or 7,
        },
        "plan": _plan_block(plan, plan_dict),
    }
    if display_name is not None:
        section["display_name"] = display_name
    return section
