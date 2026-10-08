"""Evaluate achievement progress per user (shared + persona metrics)."""

from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.app.models import BodyMetric, Meal, User, WaterEntry, Workout
from backend.app.routers.calendar import _status_for_user
from backend.app.services.bmi import calc_bmi
from backend.app.services.energy import resolve_body_profile
from backend.app.services.workout_minutes import total_workout_minutes


def _activity_dates(user_id: str, db: Session) -> list[str]:
    dates: set[str] = set()
    for model in (Meal, WaterEntry, Workout):
        rows = db.query(model.date).filter(model.user_id == user_id).distinct().all()
        for (d,) in rows:
            if d:
                dates.add(d)
    body_rows = (
        db.query(BodyMetric.recorded_on).filter(BodyMetric.user_id == user_id).distinct().all()
    )
    for (d,) in body_rows:
        if d:
            dates.add(d)
    return sorted(dates)


def _date_span(user_id: str, db: Session) -> tuple[date | None, date]:
    activity = _activity_dates(user_id, db)
    today = date.today()
    if not activity:
        return None, today
    start = date.fromisoformat(activity[0])
    end = max(today, date.fromisoformat(activity[-1]))
    return start, end


def _day_level(user: User, day: str, db: Session) -> str:
    snap = _status_for_user(user, day, db)
    return str(snap.get("level") or "none")


def eval_green_days_total(user: User, db: Session) -> float:
    start, end = _date_span(user.id, db)
    if start is None:
        return 0.0
    count = 0
    d = start
    while d <= end:
        if _day_level(user, d.isoformat(), db) == "full":
            count += 1
        d += timedelta(days=1)
    return float(count)


def eval_green_streak(user: User, db: Session) -> float:
    start, end = _date_span(user.id, db)
    if start is None:
        return 0.0
    best = 0
    cur = 0
    d = start
    while d <= end:
        if _day_level(user, d.isoformat(), db) == "full":
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
        d += timedelta(days=1)
    return float(best)


def eval_workout_sessions(user: User, db: Session) -> float:
    n = db.query(Workout).filter(Workout.user_id == user.id).count()
    return float(n)


def eval_workout_minutes_total(user: User, db: Session) -> float:
    rows = db.query(Workout).filter(Workout.user_id == user.id).all()
    total = 0
    for w in rows:
        try:
            payload = json.loads(w.payload) if w.payload else {}
        except json.JSONDecodeError:
            payload = {}
        total += total_workout_minutes([{"kind": w.kind, "payload": payload}])
    return float(total)


def eval_water_ok_days(user: User, db: Session) -> float:
    start, end = _date_span(user.id, db)
    if start is None:
        return 0.0
    count = 0
    d = start
    while d <= end:
        snap = _status_for_user(user, d.isoformat(), db)
        if snap.get("water_ok"):
            count += 1
        d += timedelta(days=1)
    return float(count)


def _latest_body_row(user: User, db: Session) -> BodyMetric | None:
    return (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user.id)
        .order_by(BodyMetric.recorded_on.desc(), BodyMetric.id.desc())
        .first()
    )


def eval_bmi_in_range(user: User, db: Session, rule: dict) -> float:
    row = _latest_body_row(user, db)
    if row is None or row.weight_kg is None:
        profile = resolve_body_profile(user, db)
        weight = profile["weight_kg"]
        height = profile["height_cm"]
    else:
        weight = row.weight_kg
        height = row.height_cm
        if height is None or float(height) <= 0:
            profile = resolve_body_profile(user, db)
            height = profile["height_cm"]
    bmi = calc_bmi(float(weight), float(height))
    if bmi is None:
        return 0.0
    bmi_min = float(rule.get("bmi_min", 18.5))
    bmi_max = float(rule.get("bmi_max", 24.0))
    return 1.0 if bmi_min <= bmi <= bmi_max else 0.0


def eval_body_fat_max(user: User, db: Session, rule: dict) -> float:
    row = _latest_body_row(user, db)
    if row is None or row.body_fat_pct is None:
        return 0.0
    profile = resolve_body_profile(user, db)
    sex = profile["sex"]
    if sex == "female":
        limit = float(rule.get("female_max", rule.get("max", 28)))
    else:
        limit = float(rule.get("male_max", rule.get("max", 20)))
    return 1.0 if float(row.body_fat_pct) <= limit else 0.0


def achievement_applies_to_user(achievement, user: User, db: Session) -> bool:
    if not achievement.enabled:
        return False
    if achievement.scope == "shared":
        return True
    if achievement.bind_user_id and achievement.bind_user_id != user.id:
        return False
    if achievement.bind_sex:
        profile = resolve_body_profile(user, db)
        if profile["sex"] != achievement.bind_sex:
            return False
    return True


def eval_progress(user: User, achievement, db: Session) -> float:
    try:
        rule = json.loads(achievement.rule_json or "{}")
    except json.JSONDecodeError:
        rule = {}
    metric = achievement.metric
    if metric == "green_days_total":
        return eval_green_days_total(user, db)
    if metric == "green_streak":
        return eval_green_streak(user, db)
    if metric == "workout_sessions":
        return eval_workout_sessions(user, db)
    if metric == "workout_minutes_total":
        return eval_workout_minutes_total(user, db)
    if metric == "water_ok_days":
        return eval_water_ok_days(user, db)
    if metric == "bmi_in_range":
        return eval_bmi_in_range(user, db, rule)
    if metric == "body_fat_max":
        return eval_body_fat_max(user, db, rule)
    return 0.0


def is_target_met(progress: float, target: float, metric: str) -> bool:
    if metric in ("bmi_in_range", "body_fat_max"):
        return progress >= 1.0
    return progress >= float(target)


def user_achievement_status(
    *,
    progress: float,
    target: float,
    metric: str,
    claimed: bool,
) -> str:
    if claimed:
        return "claimed"
    if is_target_met(progress, target, metric):
        return "claimable"
    return "incomplete"
