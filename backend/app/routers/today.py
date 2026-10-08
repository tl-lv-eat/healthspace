from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import User
from backend.app.services.day_section import build_day_section

router = APIRouter()


def _get_partner(user: User, db: Session) -> User:
    partner = db.query(User).filter(User.id != user.id).first()
    if partner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Partner not found")
    return partner


@router.get("")
def get_today(
    date: str = Query(..., description="YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    partner = _get_partner(user, db)
    return {
        "date": date,
        "me": build_day_section(user, date, db),
        "partner": build_day_section(partner, date, db, display_name=partner.display_name),
    }
