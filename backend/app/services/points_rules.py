from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.app.models import CoupleSettings, User, WeekPlan
from backend.app.routers.calendar import _day_workouts_dicts, _status_for_user
from backend.app.services.couple_settings_service import get_or_create_couple_settings
from backend.app.services.week_rules import effective_rules
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

    if int(status.get("deficit_contrib") or 0) > 0:
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


def _plan_end_date(plan: WeekPlan) -> date:
    end_s = getattr(plan, "end_date", None) or plan.week_start
    return date.fromisoformat(end_s)


def compute_plan_progress(db: Session, user: User, plan: WeekPlan) -> dict:
    """Cumulative plan metrics over [start, end] (same rules as calendar progress)."""
    from backend.app.routers.week_plans import plan_as_dict

    rules = effective_rules(plan_as_dict(plan, user), user.default_water_ml)
    start_s = plan.week_start
    end_s = getattr(plan, "end_date", None) or start_s
    start_d = date.fromisoformat(start_s)
    end_d = date.fromisoformat(end_s)
    deficit_sum = 0
    workout_days = 0
    water_ok_days = 0
    cur = start_d
    while cur <= end_d:
        day = cur.isoformat()
        st = _status_for_user(user, day, db)
        deficit_sum += int(st.get("deficit_contrib") or 0)
        if st.get("had_workout"):
            workout_days += 1
        if st.get("water_ok"):
            water_ok_days += 1
        cur += timedelta(days=1)
    period_days = max(1, (end_d - start_d).days + 1)
    target_def = int(rules.get("weekly_kcal_deficit") or 3500)
    target_wo = int(rules.get("weekly_workout_sessions") or 4)
    return {
        "start_date": start_s,
        "end_date": end_s,
        "period_days": period_days,
        "weekly_kcal_deficit_target": target_def,
        "weekly_kcal_deficit_done": deficit_sum,
        "weekly_workout_sessions_target": target_wo,
        "weekly_workout_sessions_done": workout_days,
        "water_ok_days": water_ok_days,
    }


def classify_plan_tier(progress: dict) -> str:
    period_days = int(progress.get("period_days") or 1)
    def_ok = int(progress.get("weekly_kcal_deficit_done") or 0) >= int(
        progress.get("weekly_kcal_deficit_target") or 0
    )
    wo_ok = int(progress.get("weekly_workout_sessions_done") or 0) >= int(
        progress.get("weekly_workout_sessions_target") or 0
    )
    all_water = int(progress.get("water_ok_days") or 0) >= period_days
    if def_ok and wo_ok and all_water:
        return "B"
    if def_ok and wo_ok:
        return "A"
    return "fail"


def evaluate_plan_settlement(
    db: Session,
    plan: WeekPlan,
    settings: CoupleSettings | None = None,
) -> dict:
    """Grant tier B/A/fail points once per plan (idempotent)."""
    user = db.get(User, plan.user_id)
    if user is None:
        return {"skipped": True, "reason": "user_not_found"}

    if settings is None:
        settings = get_or_create_couple_settings(db)

    progress = compute_plan_progress(db, user, plan)
    tier = classify_plan_tier(progress)
    tier_delta = {
        "B": settings.points_plan_tier_b,
        "A": settings.points_plan_tier_a,
        "fail": settings.points_plan_tier_fail,
    }
    tier_reason = {
        "B": "plan_tier_b",
        "A": "plan_tier_a",
        "fail": "plan_tier_fail",
    }
    delta = int(tier_delta[tier])
    reason = tier_reason[tier]
    key = f"{user.id}:plan:{plan.id}:settle"
    created, balance = grant(
        db,
        user.id,
        delta,
        reason,
        key,
        meta={
            "plan_id": plan.id,
            "tier": tier,
            "start_date": progress["start_date"],
            "end_date": progress["end_date"],
        },
    )
    return {
        "plan_id": plan.id,
        "user_id": user.id,
        "tier": tier,
        "granted": created,
        "delta": delta if created else 0,
        "balance": balance,
        "progress": progress,
    }


def plans_due_for_settlement(db: Session, settle_day: date) -> list[WeekPlan]:
    """Plans whose inclusive end_date is the calendar day before ``settle_day``."""
    due: list[WeekPlan] = []
    for plan in db.query(WeekPlan).all():
        if _plan_end_date(plan) + timedelta(days=1) == settle_day:
            due.append(plan)
    return due
