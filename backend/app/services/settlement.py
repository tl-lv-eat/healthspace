"""Run daily (and later plan) points settlement for both users."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from backend.app.models import User
from backend.app.services.couple_settings_service import get_or_create_couple_settings
from backend.app.services.points_rules import evaluate_daily_points


def _couple_user_ids(db: Session) -> list[str]:
    users = db.query(User).filter(User.id.in_(("dragon", "leaf"))).order_by(User.id.asc()).all()
    return [u.id for u in users]


def settle_daily_for_date(db: Session, day: date) -> dict:
    """Grant daily water / deficit / workout points for each user on ``day``."""
    settings = get_or_create_couple_settings(db)
    day_str = day.isoformat()
    per_user: dict[str, dict] = {}
    for user_id in _couple_user_ids(db):
        per_user[user_id] = evaluate_daily_points(db, user_id, day, settings)
    return {"date": day_str, "users": per_user}
