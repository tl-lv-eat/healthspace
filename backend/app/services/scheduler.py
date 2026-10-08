"""Minute tick for couple points daily settlement at ``CoupleSettings.settle_hour``."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.app.db import SessionLocal
from backend.app.models import SettlementRun
from backend.app.services.couple_settings_service import get_or_create_couple_settings
from backend.app.services.settlement import settle_daily_for_date

logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Asia/Shanghai")
DAILY_KIND = "daily"


def should_run_daily(now: datetime, settle_hour: int, last_run: date | None) -> bool:
    """True when local hour matches ``settle_hour`` and yesterday is not yet settled."""
    if now.hour != settle_hour:
        return False
    settle_day = now.date() - timedelta(days=1)
    return last_run != settle_day


def daily_run_recorded(db: Session, settle_day: date) -> bool:
    return (
        db.query(SettlementRun)
        .filter(
            SettlementRun.run_date == settle_day.isoformat(),
            SettlementRun.kind == DAILY_KIND,
        )
        .first()
        is not None
    )


def last_daily_settle_day(db: Session) -> date | None:
    row = (
        db.query(SettlementRun)
        .filter(SettlementRun.kind == DAILY_KIND)
        .order_by(SettlementRun.run_date.desc())
        .first()
    )
    if row is None:
        return None
    return date.fromisoformat(row.run_date)


def job_points_settlement() -> None:
    now = datetime.now(LOCAL_TZ)
    with SessionLocal() as db:
        settings = get_or_create_couple_settings(db)
        settle_day = now.date() - timedelta(days=1)
        last_run = settle_day if daily_run_recorded(db, settle_day) else None
        if not should_run_daily(now, settings.settle_hour, last_run):
            return
        try:
            settle_daily_for_date(db, settle_day)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("points settlement failed for %s", settle_day.isoformat())
