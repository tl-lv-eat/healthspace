from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import User
from backend.app.routers.calendar import _day_meals_dicts, _day_water_total, _day_workouts_dicts
from backend.app.routers.week_plans import get_week_plan_for_user, plan_as_dict
from backend.app.services.week_rules import day_status, effective_rules
from backend.app.settings import get_settings

router = APIRouter()


def _users_for_journal(db: Session, filter_id: str | None) -> list[User]:
    allowed = {u.id: u for u in db.query(User).all()}
    if filter_id:
        if filter_id not in allowed:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return [allowed[filter_id]]
    ids = [u.id for u in get_settings().users]
    return [allowed[i] for i in ids if i in allowed]


@router.get("")
def get_journal(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    user_id: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ = user
    start = date.fromisoformat(from_date)
    end = date.fromisoformat(to_date)
    if end < start:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid range")
    users = _users_for_journal(db, user_id)
    items = []
    cur = end
    while cur >= start:
        day_str = cur.isoformat()
        day_users = []
        for u in users:
            plan = get_week_plan_for_user(u, day_str, db)
            rules = effective_rules(plan_as_dict(plan, u), u.default_water_ml)
            meals = _day_meals_dicts(u.id, day_str, db)
            water_total = _day_water_total(u.id, day_str, db)
            workouts = _day_workouts_dicts(u.id, day_str, db)
            st = day_status(meals, water_total, workouts, rules)
            day_users.append(
                {
                    "user_id": u.id,
                    "display_name": u.display_name,
                    "meal_done": st["meal"],
                    "water_total_ml": water_total,
                    "water_target_ml": rules["water_target_ml"],
                    "water_done": st["water"],
                    "workout_done": st["workout"],
                }
            )
        if day_users:
            items.append({"date": day_str, "users": day_users})
        cur -= timedelta(days=1)
    return {"items": items}
