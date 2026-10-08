from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import User, WaterEntry
from backend.app.schemas import WaterCreate, WaterDayOut, WaterEntryOut, WaterPatch

router = APIRouter()


def _entry_to_out(entry: WaterEntry) -> WaterEntryOut:
    created = entry.created_at.isoformat() if isinstance(entry.created_at, datetime) else str(entry.created_at)
    return WaterEntryOut(
        id=entry.id,
        user_id=entry.user_id,
        date=entry.date,
        amount_ml=entry.amount_ml,
        created_at=created,
    )


def _get_owned_entry(entry_id: int, user: User, db: Session) -> WaterEntry:
    entry = db.get(WaterEntry, entry_id)
    if entry is None or entry.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Water entry not found")
    return entry


@router.get("", response_model=WaterDayOut)
def get_water_day(
    date: str = Query(..., description="YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WaterDayOut:
    rows = (
        db.query(WaterEntry)
        .filter(WaterEntry.user_id == user.id, WaterEntry.date == date)
        .order_by(WaterEntry.created_at.asc())
        .all()
    )
    entries = [_entry_to_out(e) for e in rows]
    total_ml = sum(e.amount_ml for e in rows)
    return WaterDayOut(target_ml=user.default_water_ml, total_ml=total_ml, entries=entries)


@router.post("", response_model=WaterEntryOut)
def create_water_entry(
    body: WaterCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WaterEntryOut:
    entry = WaterEntry(user_id=user.id, date=body.date, amount_ml=body.amount_ml)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _entry_to_out(entry)


@router.patch("/{entry_id}", response_model=WaterEntryOut)
def patch_water_entry(
    entry_id: int,
    body: WaterPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WaterEntryOut:
    entry = _get_owned_entry(entry_id, user, db)
    entry.amount_ml = body.amount_ml
    db.commit()
    db.refresh(entry)
    return _entry_to_out(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_water_entry(
    entry_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    entry = _get_owned_entry(entry_id, user, db)
    db.delete(entry)
    db.commit()
