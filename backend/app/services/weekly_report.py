"""Weekly AI report generation."""

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
from backend.app.services.context_summary import build_user_range_summary
from backend.app.services.day_snapshot import get_user_day_snapshot, week_period_key

_SYSTEM = (
    "你是温和专业的健康教练，为「健康space」情侣 App 写周报。"
    "只输出 Markdown，包含：## 本周回顾、## 亮点与不足、## 下周建议。"
    "基于给定数据，不编造。"
)


class ReportError(Exception):
    """LLM or persistence failed."""


def _find_report(db: Session, user_id: str, period_key: str) -> AiReport | None:
    return (
        db.query(AiReport)
        .filter(
            AiReport.user_id == user_id,
            AiReport.kind == "weekly",
            AiReport.period_key == period_key,
        )
        .first()
    )


def generate_weekly_report(
    db: Session,
    user_id: str,
    week_start: date,
    *,
    force: bool = False,
) -> AiReport:
    mon = monday_of(week_start)
    period_key = week_period_key(mon.isoformat())

    existing = _find_report(db, user_id, period_key)
    if existing is not None and not force:
        return existing

    user = db.get(User, user_id)
    if user is None:
        raise ReportError(f"user not found: {user_id}")

    days: list[dict] = []
    for i in range(7):
        d = mon + timedelta(days=i)
        days.append(get_user_day_snapshot(db, user, d.isoformat()))
    blob = build_user_range_summary(days)
    user_text = (
        f"请为 {user.display_name}（{user_id}）生成本周周报，"
        f"周起始 {mon.isoformat()}（{period_key}）。\n\n{blob}"
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
        kind="weekly",
        period_key=period_key,
        content_md=content,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
