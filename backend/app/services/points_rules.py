from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.app.models import User
from backend.app.routers.calendar import _status_for_user
from backend.app.services.points import grant
from backend.app.settings import get_settings


def evaluate_daily_points(db: Session, user_id: str, day: date) -> dict:
    user = db.get(User, user_id)
    if user is None:
        return {"granted": False, "reason": "user_not_found"}
    day_str = day.isoformat()
    status = _status_for_user(user, day_str, db)
    if status.get("level") != "full":
        return {"granted": False, "level": status.get("level")}
    pts = get_settings().points.daily_all_three
    key = f"{user_id}:{day_str}:daily_all_three"
    created, balance = grant(db, user_id, pts, "daily_all_three", key, meta={"date": day_str})
    return {"granted": created, "balance": balance, "delta": pts if created else 0}


def evaluate_weekly_points(db: Session, user_id: str, week_start: date) -> dict:
    if week_start.weekday() != 0:
        week_start = week_start - timedelta(days=week_start.weekday())
    user = db.get(User, user_id)
    if user is None:
        return {"granted": False, "reason": "user_not_found"}
    for i in range(7):
        d = week_start + timedelta(days=i)
        status = _status_for_user(user, d.isoformat(), db)
        if status.get("level") != "full":
            return {"granted": False, "reason": "week_incomplete", "failed_date": d.isoformat()}
    pts = get_settings().points.weekly_plan_complete
    key = f"{user_id}:{week_start.isoformat()}:weekly_plan_complete"
    created, balance = grant(db, user_id, pts, "weekly_plan_complete", key, meta={"week_start": week_start.isoformat()})
    return {"granted": created, "balance": balance, "delta": pts if created else 0}


def evaluate_points_for_day(db: Session, user_id: str, day: date) -> dict:
    daily = evaluate_daily_points(db, user_id, day)
    monday = day - timedelta(days=day.weekday())
    weekly = evaluate_weekly_points(db, user_id, monday)
    return {"daily": daily, "weekly": weekly}
