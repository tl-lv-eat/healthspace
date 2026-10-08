from __future__ import annotations

import calendar as cal_mod
import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import Meal, User, WaterEntry, Workout
from backend.app.routers.today import _get_partner
from backend.app.services.day_section import build_day_section
from backend.app.routers.week_plans import get_week_plan_for_user, monday_of, plan_as_dict
from backend.app.services.energy import daily_energy_snapshot, user_bmr
from backend.app.services.week_rules import day_status, effective_rules

router = APIRouter()


def _couple_users(db: Session) -> tuple[User, User]:
    users = db.query(User).order_by(User.id.asc()).all()
    by_id = {u.id: u for u in users}
    dragon = by_id.get("dragon")
    leaf = by_id.get("leaf")
    if dragon is None or leaf is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Users not seeded")
    return dragon, leaf


def _day_meals_dicts(user_id: str, day: str, db: Session) -> list[dict]:
    rows = db.query(Meal).filter(Meal.user_id == user_id, Meal.date == day).all()
    return [{"meal_type": m.meal_type, "user_kcal": int(m.user_kcal or 0)} for m in rows]


def _day_intake_kcal(user_id: str, day: str, db: Session) -> int:
    rows = db.query(Meal).filter(Meal.user_id == user_id, Meal.date == day).all()
    return sum(int(m.user_kcal or 0) for m in rows)


def _day_water_total(user_id: str, day: str, db: Session) -> int:
    rows = db.query(WaterEntry).filter(WaterEntry.user_id == user_id, WaterEntry.date == day).all()
    return sum(e.amount_ml for e in rows)


def _day_workouts_dicts(user_id: str, day: str, db: Session) -> list[dict]:
    rows = db.query(Workout).filter(Workout.user_id == user_id, Workout.date == day).all()
    out = []
    for w in rows:
        try:
            payload = json.loads(w.payload) if w.payload else {}
        except json.JSONDecodeError:
            payload = {}
        out.append({"kind": w.kind, "payload": payload})
    return out


def _status_for_user(u: User, day: str, db: Session) -> dict:
    """Energy-linked day status for calendar colors."""
    plan = get_week_plan_for_user(u, day, db)
    rules = effective_rules(plan_as_dict(plan, u), u.default_water_ml)
    intake = _day_intake_kcal(u.id, day, db)
    water = _day_water_total(u.id, day, db)
    workouts = _day_workouts_dicts(u.id, day, db)
    bmr = user_bmr(u, db)
    snap = daily_energy_snapshot(
        intake_kcal=intake,
        workouts=workouts,
        bmr=bmr,
        water_ml=water,
        water_target_ml=rules["water_target_ml"],
        weekly_kcal_deficit=int(rules.get("weekly_kcal_deficit") or 3500),
        period_days=int(rules.get("period_days") or 7),
    )
    # Keep legacy meal/workout completion for points hooks that still call old shape.
    legacy = day_status(
        [{"meal_type": m["meal_type"]} for m in _day_meals_dicts(u.id, day, db)],
        water,
        workouts,
        rules,
    )
    snap["meal"] = legacy["meal"]
    snap["workout"] = legacy["workout"]
    return snap


def _plan_progress(u: User, on_day: str, db: Session) -> dict:
    """Progress for the active plan covering on_day (falls back to Mon–Sun)."""
    plan = get_week_plan_for_user(u, on_day, db)
    rules = effective_rules(plan_as_dict(plan, u), u.default_water_ml)
    if plan is not None:
        start_s = plan.week_start
        end_s = getattr(plan, "end_date", None) or start_s
    else:
        start_s = monday_of(date.fromisoformat(on_day)).isoformat()
        end_s = (date.fromisoformat(start_s) + timedelta(days=6)).isoformat()
    start_d = date.fromisoformat(start_s)
    end_d = date.fromisoformat(end_s)
    deficit_sum = 0
    workout_days = 0
    water_ok_days = 0
    cur = start_d
    while cur <= end_d:
        day = cur.isoformat()
        st = _status_for_user(u, day, db)
        deficit_sum += int(st.get("deficit_contrib") or 0)
        if st.get("had_workout"):
            workout_days += 1
        if st.get("water_ok"):
            water_ok_days += 1
        cur += timedelta(days=1)
    target_def = int(rules.get("weekly_kcal_deficit") or 3500)
    target_wo = int(rules.get("weekly_workout_sessions") or 4)
    period_days = max(1, (end_d - start_d).days + 1)
    return {
        "week_start": start_s,
        "start_date": start_s,
        "end_date": end_s,
        "period_days": period_days,
        "weekly_kcal_deficit_target": target_def,
        "weekly_kcal_deficit_done": deficit_sum,
        "weekly_workout_sessions_target": target_wo,
        "weekly_workout_sessions_done": workout_days,
        "water_ok_days": water_ok_days,
        "target_weight_kg": rules.get("target_weight_kg"),
        "water_target_ml": rules["water_target_ml"],
    }


@router.get("")
def get_calendar_month(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    dragon, leaf = _couple_users(db)
    _, last_day = cal_mod.monthrange(year, month)
    days = []
    for d in range(1, last_day + 1):
        day_str = date(year, month, d).isoformat()
        days.append(
            {
                "date": day_str,
                "dragon": _status_for_user(dragon, day_str, db),
                "leaf": _status_for_user(leaf, day_str, db),
            }
        )
    # Progress for the active plan covering today (or month start if browsing past).
    today = date.today()
    if today.year == year and today.month == month:
        anchor = today.isoformat()
    else:
        anchor = date(year, month, 1).isoformat()
    progress = _plan_progress(user, anchor, db)
    return {
        "year": year,
        "month": month,
        "days": days,
        "week_start": progress["week_start"],
        "my_week_progress": progress,
    }


@router.get("/day")
def get_calendar_day(
    date_str: str = Query(..., alias="date"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    partner = _get_partner(user, db)
    dragon, leaf = _couple_users(db)
    dragon_status = _status_for_user(dragon, date_str, db)
    leaf_status = _status_for_user(leaf, date_str, db)
    return {
        "date": date_str,
        "dragon": {
            "user_id": dragon.id,
            "display_name": dragon.display_name,
            "status": dragon_status,
        },
        "leaf": {
            "user_id": leaf.id,
            "display_name": leaf.display_name,
            "status": leaf_status,
        },
        "sections": {
            "dragon": build_day_section(
                dragon, date_str, db, display_name=dragon.display_name
            ),
            "leaf": build_day_section(leaf, date_str, db, display_name=leaf.display_name),
        },
        "me": build_day_section(user, date_str, db),
        "partner": build_day_section(partner, date_str, db, display_name=partner.display_name),
    }
