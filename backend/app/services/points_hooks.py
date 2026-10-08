from __future__ import annotations

from sqlalchemy.orm import Session


def after_daily_activity(db: Session, user_id: str, day_str: str) -> None:
    """No-op: daily points are granted by scheduled settlement, not live activity hooks."""
    _ = (db, user_id, day_str)
