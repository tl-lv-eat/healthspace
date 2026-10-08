from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models import CoupleSettings

COUPLE_SETTINGS_ID = 1


def get_or_create_couple_settings(db: Session) -> CoupleSettings:
    row = db.get(CoupleSettings, COUPLE_SETTINGS_ID)
    if row is None:
        row = CoupleSettings(id=COUPLE_SETTINGS_ID)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row
