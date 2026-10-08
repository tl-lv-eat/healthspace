from __future__ import annotations

import json
from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.app.models import BodyMetric, Goal, User
from backend.app.routers.calendar import _status_for_user
from backend.app.services.points import grant
from backend.app.settings import get_settings


def weight_goal_reached(baseline: float, target: float, latest: float) -> bool:
    if target <= baseline:
        return latest <= target
    return latest >= target


def _parse_meta(goal: Goal) -> dict:
    try:
        return json.loads(goal.meta_json or "{}")
    except json.JSONDecodeError:
        return {}


def _latest_weight(db: Session, user_id: str) -> float | None:
    row = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user_id, BodyMetric.weight_kg.isnot(None))
        .order_by(BodyMetric.recorded_on.desc(), BodyMetric.id.desc())
        .first()
    )
    return float(row.weight_kg) if row and row.weight_kg is not None else None


def _count_workout_days(db: Session, user: User, start: date, end: date) -> int:
    count = 0
    d = start
    while d <= end:
        st = _status_for_user(user, d.isoformat(), db)
        if st.get("workout"):
            count += 1
        d += timedelta(days=1)
    return count


def refresh_goal_progress(db: Session, goal: Goal) -> Goal:
    if goal.status != "active":
        return goal
    user = db.get(User, goal.user_id)
    if user is None:
        return goal
    meta = _parse_meta(goal)
    if goal.metric == "weight_kg":
        latest = _latest_weight(db, goal.user_id)
        if latest is not None:
            goal.current_value = latest
        baseline = meta.get("baseline_weight")
        if baseline is None:
            baseline = goal.target_value
        if latest is not None and weight_goal_reached(float(baseline), goal.target_value, latest):
            goal.status = "done"
            pts = get_settings().points.goal_complete
            grant(
                db,
                goal.user_id,
                pts,
                "goal_complete",
                f"goal_done:{goal.id}",
                meta={"goal_id": goal.id},
            )
    elif goal.metric == "workout_days":
        start = date.fromisoformat(goal.start_date)
        end = date.fromisoformat(goal.end_date) if goal.end_date else date.today()
        goal.current_value = float(_count_workout_days(db, user, start, end))
        if goal.current_value >= goal.target_value:
            goal.status = "done"
    db.commit()
    db.refresh(goal)
    return goal
