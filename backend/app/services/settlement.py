"""Run daily (and later plan) points settlement for both users."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy.orm import Session

from backend.app.models import SettlementRun, User
from backend.app.services.couple_settings_service import get_or_create_couple_settings
from backend.app.services.points_rules import (
    evaluate_daily_points,
    evaluate_plan_settlement,
    plans_due_for_settlement,
)


def _couple_user_ids(db: Session) -> list[str]:
    users = db.query(User).filter(User.id.in_(("dragon", "leaf"))).order_by(User.id.asc()).all()
    return [u.id for u in users]


def _record_settlement_run(db: Session, run_date: str, kind: str, meta: dict) -> None:
    existing = (
        db.query(SettlementRun)
        .filter(SettlementRun.run_date == run_date, SettlementRun.kind == kind)
        .first()
    )
    if existing is not None:
        return
    db.add(
        SettlementRun(
            run_date=run_date,
            kind=kind,
            meta_json=json.dumps(meta, ensure_ascii=False),
        )
    )


def settle_daily_for_date(db: Session, day: date) -> dict:
    """Grant daily points for ``day`` and plan tier points for plans that ended yesterday."""
    settings = get_or_create_couple_settings(db)
    day_str = day.isoformat()
    per_user: dict[str, dict] = {}
    for user_id in _couple_user_ids(db):
        per_user[user_id] = evaluate_daily_points(db, user_id, day, settings)
    plan_results = [
        evaluate_plan_settlement(db, plan, settings) for plan in plans_due_for_settlement(db, day)
    ]
    result = {"date": day_str, "users": per_user, "plans": plan_results}
    _record_settlement_run(
        db,
        day_str,
        "daily",
        {
            "user_ids": list(per_user.keys()),
            "plan_ids": [p.get("plan_id") for p in plan_results if p.get("plan_id") is not None],
        },
    )
    for plan in plan_results:
        plan_id = plan.get("plan_id")
        if plan_id is None:
            continue
        _record_settlement_run(
            db,
            day_str,
            f"plan:{plan_id}",
            {"tier": plan.get("tier"), "user_id": plan.get("user_id"), "granted": plan.get("granted")},
        )
    return result
