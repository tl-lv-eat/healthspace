from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models import PointsLedger


def get_balance(db: Session, user_id: str) -> int:
    total = db.query(func.coalesce(func.sum(PointsLedger.delta), 0)).filter(PointsLedger.user_id == user_id).scalar()
    return int(total or 0)


def grant(
    db: Session,
    user_id: str,
    delta: int,
    reason: str,
    idempotency_key: str,
    meta: dict | None = None,
) -> tuple[bool, int]:
    existing = db.query(PointsLedger).filter_by(idempotency_key=idempotency_key).first()
    if existing:
        return False, get_balance(db, user_id)
    row = PointsLedger(
        user_id=user_id,
        delta=int(delta),
        reason=reason,
        idempotency_key=idempotency_key,
        meta_json=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return False, get_balance(db, user_id)
    return True, get_balance(db, user_id)
