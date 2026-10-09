"""Diet coach chat with recent context."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import call_llm  # noqa: E402

from backend.app.models import ChatMessage, User
from backend.app.services.context_summary import build_user_range_summary
from backend.app.services.day_snapshot import get_user_day_snapshot

CHAT_DISCLAIMER = "非医疗建议，不能替代医师诊断。"

_COACH_SYSTEM = (
    "你是「健康space」情侣 App 的健康教练，回答简短实用、鼓励记录。"
    f"重要：{CHAT_DISCLAIMER} "
    "若上下文无相关数据，请如实说明并建议继续打卡。"
)


class ChatError(Exception):
    """LLM or chat persistence failed."""


def _last_n_messages(db: Session, user_id: str, limit: int = 10) -> list[ChatMessage]:
    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )
    return list(reversed(rows))


def _recent_days_snapshot(db: Session, user: User, n_days: int = 7) -> str:
    today = date.today()
    days: list[dict] = []
    for i in range(n_days - 1, -1, -1):
        d = today - timedelta(days=i)
        days.append(get_user_day_snapshot(db, user, d.isoformat()))
    return build_user_range_summary(days)


def chat_reply(db: Session, user: User, message: str) -> str:
    text = (message or "").strip()
    if not text:
        raise ChatError("empty message")

    context = _recent_days_snapshot(db, user)
    system_content = f"{_COACH_SYSTEM}\n\n=== 近7日记录 ===\n{context}"
    messages: list[dict] = [{"role": "system", "content": system_content}]
    for row in _last_n_messages(db, user.id, 10):
        messages.append({"role": row.role, "content": row.content})
    messages.append({"role": "user", "content": text})

    try:
        result = call_llm.responses_chat_messages(messages, enable_thinking=False)
        reply = (result.text or "").strip()
    except Exception as exc:
        raise ChatError(str(exc)) from exc

    if not reply:
        raise ChatError("empty LLM response")

    db.add(ChatMessage(user_id=user.id, role="user", content=text))
    db.add(ChatMessage(user_id=user.id, role="assistant", content=reply))
    db.commit()
    return reply
