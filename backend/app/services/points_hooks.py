from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from backend.app.services.points_rules import evaluate_points_for_day


def after_daily_activity(db: Session, user_id: str, day_str: str) -> None:
    try:
        day = date.fromisoformat(day_str)
    except ValueError:
        return
    evaluate_points_for_day(db, user_id, day)
