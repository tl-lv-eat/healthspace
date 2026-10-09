"""Daily AI report generation."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import call_llm  # noqa: E402

from backend.app.models import AiReport, User
from backend.app.routers.week_plans import monday_of
from backend.app.services.context_summary import build_user_day_blob, build_user_range_summary
from backend.app.services.day_snapshot import get_user_day_snapshot

_SYSTEM = (
    "你是温和专业的健康教练，为「健康space」情侣 App 写日终分析。"
    "只输出 Markdown，包含三个二级标题：## 今日小结、## 本周趋势、## 明日建议。"
    "语气鼓励、具体可执行，不编造没有的数据。"
)


class ReportError(Exception):
    """LLM or persistence failed; existing report must not be overwritten."""


def _find_report(db: Session, user_id: str, period_key: str) -> AiReport | None:
    return (
        db.query(AiReport)
        .filter(
            AiReport.user_id == user_id,
            AiReport.kind == "daily",
            AiReport.period_key == period_key,
        )
        .first()
    )


def _collect_week_days(db: Session, user: User, day: date) -> list[dict]:
    mon = monday_of(day)
    days: list[dict] = []
    d = mon
    while d <= day:
        days.append(get_user_day_snapshot(db, user, d.isoformat()))
        d += timedelta(days=1)
    return days


def generate_daily_report(
    db: Session,
    user_id: str,
    day: date,
    *,
    force: bool = False,
) -> AiReport:
    period_key = day.isoformat()
    existing = _find_report(db, user_id, period_key)
    if existing is not None and not force:
        return existing

    user = db.get(User, user_id)
    if user is None:
        raise ReportError(f"user not found: {user_id}")

    week_days = _collect_week_days(db, user, day)
    today_snap = week_days[-1] if week_days else get_user_day_snapshot(db, user, period_key)
    today_blob = build_user_day_blob(
        today_snap["date"],
        today_snap["meals"],
        today_snap["water"],
        today_snap["workouts"],
        today_snap["done"],
    )
    week_blob = build_user_range_summary(week_days)
    user_text = (
        f"请为 {user.display_name}（{user_id}）生成 {period_key} 的日终报告。\n\n"
        f"=== 当日详情 ===\n{today_blob}\n\n=== 本周至今 ===\n{week_blob}"
    )
    messages = [
        {"role": "system", "content": _SYSTEM},
        {"role": "user", "content": user_text},
    ]

    try:
        result = call_llm.responses_chat_messages(messages, enable_thinking=False)
        content = (result.text or "").strip()
    except Exception as exc:
        raise ReportError(str(exc)) from exc

    if not content:
        raise ReportError("empty LLM response")

    if existing is not None:
        existing.content_md = content
        db.commit()
        db.refresh(existing)
        return existing

    row = AiReport(
        user_id=user_id,
        kind="daily",
        period_key=period_key,
        content_md=content,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
