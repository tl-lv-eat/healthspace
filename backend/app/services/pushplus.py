"""PushPlus WeChat push and incomplete-day reminders."""

from __future__ import annotations

import json
from datetime import date, datetime

import httpx
from sqlalchemy.orm import Session

from backend.app.models import PushBinding, User
from backend.app.services.day_snapshot import get_user_day_snapshot
from backend.app.settings import get_settings

PUSHPLUS_URL = "http://www.pushplus.plus/send"


class PushPlusError(Exception):
    """PushPlus API error."""


def send_pushplus(token: str, title: str, content: str) -> None:
    payload = {"token": token, "title": title, "content": content}
    resp = httpx.post(PUSHPLUS_URL, json=payload, timeout=30.0)
    if resp.status_code != 200:
        raise PushPlusError(f"HTTP {resp.status_code}: {resp.text[:200]}")
    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise PushPlusError("invalid JSON response") from exc
    if data.get("code") != 200:
        raise PushPlusError(str(data.get("msg") or data))


def _default_remind_hours() -> list[int]:
    sched = get_settings().schedule
    return list(sched.reminder_hours)


def _parse_remind_hours(raw: str) -> list[int]:
    try:
        parsed = json.loads(raw or "[]")
    except json.JSONDecodeError:
        return _default_remind_hours()
    if not isinstance(parsed, list):
        return _default_remind_hours()
    out: list[int] = []
    for x in parsed:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out or _default_remind_hours()


def _incomplete_lines(done: dict[str, bool]) -> list[str]:
    lines: list[str] = []
    if not done.get("meal"):
        lines.append("饮食打卡未完成")
    if not done.get("water"):
        lines.append("饮水目标未达成")
    if not done.get("workout"):
        lines.append("运动打卡未完成")
    return lines


def run_reminders_now(db: Session, *, hour: int | None = None) -> None:
    """Send PushPlus reminders for users with incomplete today items."""
    now_hour = hour if hour is not None else datetime.now().hour
    today = date.today().isoformat()

    bindings = db.query(PushBinding).filter(PushBinding.enabled.is_(True)).all()
    for binding in bindings:
        hours = _parse_remind_hours(binding.remind_hours_json)
        if now_hour not in hours:
            continue
        if not (binding.token or "").strip():
            binding.last_error = "missing token"
            db.commit()
            continue

        user = db.get(User, binding.user_id)
        if user is None:
            continue

        snap = get_user_day_snapshot(db, user, today)
        done = snap.get("done") or {}
        if done.get("meal") and done.get("water") and done.get("workout"):
            continue

        lines = _incomplete_lines(done)
        title = "健康space · 今日提醒"
        content = f"{today}\n" + "\n".join(f"· {line}" for line in lines)

        try:
            send_pushplus(binding.token.strip(), title, content)
        except Exception as exc:
            binding.last_error = str(exc)[:500]
            db.commit()
            continue

        binding.last_error = None
        binding.last_success_at = datetime.utcnow()
        db.commit()


def get_or_create_binding(db: Session, user_id: str) -> PushBinding:
    row = db.get(PushBinding, user_id)
    if row is not None:
        return row
    default_hours = json.dumps(_default_remind_hours())
    row = PushBinding(user_id=user_id, token="", enabled=False, remind_hours_json=default_hours)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
