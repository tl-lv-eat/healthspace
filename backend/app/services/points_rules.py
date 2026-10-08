from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.app.models import CoupleSettings, User
from backend.app.routers.calendar import _day_workouts_dicts, _status_for_user
from backend.app.services.couple_settings_service import get_or_create_couple_settings
from backend.app.services.points import get_balance, grant
from backend.app.services.workout_minutes import total_workout_minutes
from backend.app.settings import get_settings


def _grant_daily_item(
    db: Session,
    user_id: str,
    day_str: str,
    reason: str,
    delta: int,
    grants: list[dict],
) -> int:
    key = f"{user_id}:{day_str}:{reason}"
    created, _balance = grant(db, user_id, delta, reason, key, meta={"date": day_str})
    grants.append(
        {
            "reason": reason,
            "granted": created,
            "delta": delta if created else 0,
        }
    )
    return delta if created else 0


def evaluate_daily_points(
    db: Session,
    user_id: str,
    day: date,
    settings: CoupleSettings | None = None,
) -> dict:
    """Apply daily settlement grants (water, deficit, ≥40 min workout) for one user."""
    user = db.get(User, user_id)
    if user is None:
        return {"grants": [], "delta_total": 0, "reason": "user_not_found"}

    if settings is None:
        settings = get_or_create_couple_settings(db)

    day_str = day.isoformat()
    status = _status_for_user(user, day_str, db)
    workouts = _day_workouts_dicts(user_id, day_str, db)

    intake = int(status.get("intake_kcal") or 0)
    water_ml = int(status.get("water_ml") or 0)
    burn = int(status.get("burn_kcal") or 0)
    surplus = int(status.get("surplus_kcal") or 0)
    water_ok = bool(status.get("water_ok"))

    empty = intake == 0 and water_ml == 0 and burn == 0 and len(workouts) == 0
    if empty:
        return {
            "grants": [],
            "delta_total": 0,
            "balance": get_balance(db, user_id),
            "empty": True,
        }

    grants: list[dict] = []
    delta_total = 0

    if water_ok:
        delta_total += _grant_daily_item(
            db, user_id, day_str, "daily_water", settings.points_daily_water, grants
        )

    has_calorie_activity = intake > 0 or burn > 0
    if has_calorie_activity and surplus <= 0:
        delta_total += _grant_daily_item(
            db, user_id, day_str, "daily_deficit", settings.points_daily_deficit, grants
        )

    if total_workout_minutes(workouts) >= 40:
        delta_total += _grant_daily_item(
            db,
            user_id,
            day_str,
            "daily_workout_40",
            settings.points_daily_workout_40,
            grants,
        )

    return {
        "grants": grants,
        "delta_total": delta_total,
        "balance": get_balance(db, user_id),
        "empty": False,
    }


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
