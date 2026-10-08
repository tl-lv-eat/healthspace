from __future__ import annotations

import calendar as cal_mod
import json
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import Meal, User, WaterEntry, Workout
from backend.app.routers.today import (
    _build_me_section,
    _build_partner_section,
    _get_partner,
)
from backend.app.routers.week_plans import get_week_plan_for_user, plan_as_dict
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
    return [{"meal_type": m.meal_type} for m in rows]


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
    plan = get_week_plan_for_user(u, day, db)
    rules = effective_rules(plan_as_dict(plan, u), u.default_water_ml)
    meals = _day_meals_dicts(u.id, day, db)
    water = _day_water_total(u.id, day, db)
    workouts = _day_workouts_dicts(u.id, day, db)
    return day_status(meals, water, workouts, rules)


@router.get("")
def get_calendar_month(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ = user
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
    return {"year": year, "month": month, "days": days}


@router.get("/day")
def get_calendar_day(
    date_str: str = Query(..., alias="date"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    partner = _get_partner(user, db)
    dragon, leaf = _couple_users(db)
    return {
        "date": date_str,
        "dragon": {
            "user_id": dragon.id,
            "display_name": dragon.display_name,
            "status": _status_for_user(dragon, date_str, db),
        },
        "leaf": {
            "user_id": leaf.id,
            "display_name": leaf.display_name,
            "status": _status_for_user(leaf, date_str, db),
        },
        "me": _build_me_section(user, date_str, db),
        "partner": _build_partner_section(partner, date_str, db),
    }
