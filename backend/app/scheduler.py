"""APScheduler jobs for reports and PushPlus reminders."""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.app.db import SessionLocal
from backend.app.services.daily_report import ReportError, generate_daily_report
from backend.app.services.pushplus import run_reminders_now
from backend.app.services.weekly_report import ReportError as WeeklyReportError
from backend.app.services.weekly_report import generate_weekly_report
from backend.app.services.scheduler import job_points_settlement
from backend.app.settings import get_settings

logger = logging.getLogger(__name__)

JOB_DAILY = "job_daily_reports"
JOB_WEEKLY = "job_weekly_reports"
JOB_REMINDERS = "job_reminders"
JOB_POINTS_SETTLEMENT = "job_points_settlement"

_USER_IDS = ("dragon", "leaf")


def job_daily_reports() -> None:
    today = date.today()
    with SessionLocal() as db:
        for uid in _USER_IDS:
            try:
                generate_daily_report(db, uid, today, force=False)
            except ReportError as exc:
                logger.warning("daily report failed for %s: %s", uid, exc)
            except Exception:
                logger.exception("daily report unexpected error for %s", uid)


def job_weekly_reports() -> None:
    today = date.today()
    this_monday = today - timedelta(days=today.weekday())
    last_week_start = this_monday - timedelta(days=7)
    with SessionLocal() as db:
        for uid in _USER_IDS:
            try:
                generate_weekly_report(db, uid, last_week_start, force=False)
            except WeeklyReportError as exc:
                logger.warning("weekly report failed for %s: %s", uid, exc)
            except Exception:
                logger.exception("weekly report unexpected error for %s", uid)


def job_reminders() -> None:
    with SessionLocal() as db:
        try:
            run_reminders_now(db)
        except Exception:
            logger.exception("reminders job failed")


def start_scheduler() -> BackgroundScheduler | None:
    if os.environ.get("DISABLE_SCHEDULER", "").strip() == "1":
        return None

    sched_cfg = get_settings().schedule
    scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    scheduler.add_job(
        job_daily_reports,
        CronTrigger(
            hour=sched_cfg.daily_report_hour,
            minute=sched_cfg.daily_report_minute,
        ),
        id=JOB_DAILY,
        replace_existing=True,
    )
    scheduler.add_job(
        job_weekly_reports,
        CronTrigger(
            day_of_week=sched_cfg.weekly_report_weekday,
            hour=sched_cfg.weekly_report_hour,
            minute=sched_cfg.weekly_report_minute,
        ),
        id=JOB_WEEKLY,
        replace_existing=True,
    )
    scheduler.add_job(
        job_reminders,
        CronTrigger(minute=0),
        id=JOB_REMINDERS,
        replace_existing=True,
    )
    scheduler.add_job(
        job_points_settlement,
        IntervalTrigger(seconds=60),
        id=JOB_POINTS_SETTLEMENT,
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
