from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import AiReport, User
from backend.app.routers.week_plans import monday_of
from backend.app.services.daily_report import ReportError as DailyReportError
from backend.app.services.daily_report import generate_daily_report
from backend.app.services.weekly_report import ReportError as WeeklyReportError
from backend.app.services.weekly_report import generate_weekly_report

router = APIRouter()


class ReportOut(BaseModel):
    id: int
    user_id: str
    kind: str
    period_key: str
    content_md: str
    created_at: str


class GenerateBody(BaseModel):
    kind: str = Field(..., pattern="^(daily|weekly)$")
    period: str
    force: bool = False


def _report_to_out(r: AiReport) -> ReportOut:
    return ReportOut(
        id=r.id,
        user_id=r.user_id,
        kind=r.kind,
        period_key=r.period_key,
        content_md=r.content_md,
        created_at=r.created_at.isoformat() + "Z",
    )


@router.get("")
def get_report(
    kind: str = Query(..., pattern="^(daily|weekly)$"),
    period: str = Query(..., description="YYYY-MM-DD for daily; week Monday or any day in week for weekly"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    if kind == "daily":
        period_key = date.fromisoformat(period).isoformat()
    else:
        mon = monday_of(date.fromisoformat(period))
        from backend.app.services.day_snapshot import week_period_key

        period_key = week_period_key(mon.isoformat())

    row = (
        db.query(AiReport)
        .filter(
            AiReport.user_id == user.id,
            AiReport.kind == kind,
            AiReport.period_key == period_key,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return _report_to_out(row)


@router.post("/generate")
def generate_report(
    body: GenerateBody,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportOut:
    try:
        if body.kind == "daily":
            row = generate_daily_report(db, user.id, date.fromisoformat(body.period), force=body.force)
        else:
            row = generate_weekly_report(
                db,
                user.id,
                date.fromisoformat(body.period),
                force=body.force,
            )
    except (DailyReportError, WeeklyReportError) as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return _report_to_out(row)
