from __future__ import annotations
from calendar import monthrange
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import User, WeekPlan
from backend.app.schemas import WeekPlanOut, WeekPlanUpsert

router = APIRouter()


def _couple_user_ids() -> set[str]:
    return {"dragon", "leaf"}


def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _period_days(start: str, end: str) -> int:
    a = date.fromisoformat(start)
    b = date.fromisoformat(end)
    return max(1, (b - a).days + 1)


def _plan_to_out(
    plan: WeekPlan | None, user: User, *, start: str, end: str
) -> WeekPlanOut:
    if plan is None:
        return WeekPlanOut(
            id=None,
            user_id=user.id,
            start_date=start,
            end_date=end,
            week_start=start,
            title=None,
            note="",
            daily_kcal_cap=None,
            water_target_ml=user.default_water_ml,
            weekly_kcal_deficit=3500,
            weekly_workout_sessions=4,
            target_weight_kg=None,
            meal_mode="three_main",
            workout_mode="any",
            workout_cardio_min=None,
            workout_strength_sets=None,
            period_days=_period_days(start, end),
        )
    start_s = plan.week_start
    end_s = getattr(plan, "end_date", None) or start_s
    return WeekPlanOut(
        id=plan.id,
        user_id=plan.user_id,
        start_date=start_s,
        end_date=end_s,
        week_start=start_s,
        title=getattr(plan, "title", None),
        note=getattr(plan, "note", None) or "",
        daily_kcal_cap=getattr(plan, "daily_kcal_cap", None),
        water_target_ml=plan.water_target_ml,
        weekly_kcal_deficit=int(getattr(plan, "weekly_kcal_deficit", 3500) or 3500),
        weekly_workout_sessions=int(getattr(plan, "weekly_workout_sessions", 4) or 4),
        target_weight_kg=getattr(plan, "target_weight_kg", None),
        meal_mode=plan.meal_mode,
        workout_mode=plan.workout_mode,
        workout_cardio_min=plan.workout_cardio_min,
        workout_strength_sets=plan.workout_strength_sets,
        period_days=_period_days(start_s, end_s),
    )


def _plan_dict(plan: WeekPlan | None, user: User) -> dict:
    if plan is None:
        return {
            "water_target_ml": user.default_water_ml,
            "daily_kcal_cap": None,
            "weekly_kcal_deficit": 3500,
            "weekly_workout_sessions": 4,
            "target_weight_kg": None,
            "meal_mode": "three_main",
            "workout_mode": "any",
            "period_days": 7,
            "start_date": None,
            "end_date": None,
            "title": None,
            "note": "",
        }
    start_s = plan.week_start
    end_s = getattr(plan, "end_date", None) or start_s
    return {
        "water_target_ml": plan.water_target_ml,
        "daily_kcal_cap": getattr(plan, "daily_kcal_cap", None),
        "weekly_kcal_deficit": int(getattr(plan, "weekly_kcal_deficit", 3500) or 3500),
        "weekly_workout_sessions": int(
            getattr(plan, "weekly_workout_sessions", 4) or 4
        ),
        "target_weight_kg": getattr(plan, "target_weight_kg", None),
        "meal_mode": plan.meal_mode,
        "workout_mode": plan.workout_mode,
        "workout_cardio_min": plan.workout_cardio_min,
        "workout_strength_sets": plan.workout_strength_sets,
        "period_days": _period_days(start_s, end_s),
        "start_date": start_s,
        "end_date": end_s,
        "title": getattr(plan, "title", None),
        "note": getattr(plan, "note", None) or "",
    }


def get_week_plan_for_user(user: User, day: str, db: Session) -> WeekPlan | None:
    """Active plan covering this calendar day (latest start wins if overlap)."""
    rows = (
        db.query(WeekPlan)
        .filter(WeekPlan.user_id == user.id, WeekPlan.week_start <= day)
        .order_by(WeekPlan.week_start.desc(), WeekPlan.id.desc())
        .all()
    )
    for plan in rows:
        end_s = getattr(plan, "end_date", None) or plan.week_start
        if plan.week_start <= day <= end_s:
            return plan
    return None


def plan_as_dict(plan: WeekPlan | None, user: User) -> dict:
    return _plan_dict(plan, user)


def _normalize_range(start: str, end: str | None) -> tuple[str, str]:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end) if end else s + timedelta(days=6)
    if e < s:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must be on or after start_date",
        )
    # Cap at 60 days to keep calendar linkage sane
    if (e - s).days + 1 > 60:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="plan range cannot exceed 60 days",
        )
    return s.isoformat(), e.isoformat()


def _apply_upsert_fields(
    plan: WeekPlan, body: WeekPlanUpsert, *, start_s: str, end_s: str
) -> None:
    plan.week_start = start_s
    plan.end_date = end_s
    plan.water_target_ml = body.water_target_ml
    plan.weekly_kcal_deficit = max(0, int(body.weekly_kcal_deficit))
    plan.weekly_workout_sessions = max(0, min(60, int(body.weekly_workout_sessions)))
    plan.target_weight_kg = body.target_weight_kg
    plan.meal_mode = body.meal_mode
    plan.workout_mode = body.workout_mode
    plan.workout_cardio_min = body.workout_cardio_min
    plan.workout_strength_sets = body.workout_strength_sets
    plan.title = body.title
    plan.note = body.note or ""
    plan.daily_kcal_cap = body.daily_kcal_cap


def _owner_id_from_body(body: WeekPlanUpsert, user: User) -> str:
    owner_id = body.target_user_id or user.id
    if owner_id not in _couple_user_ids():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="target_user_id must be a couple member",
        )
    return owner_id


def _load_subject_user(db: Session, current: User, subject_id: str) -> User:
    if subject_id not in _couple_user_ids():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_id must be a couple member",
        )
    if subject_id == current.id:
        return current
    u = db.get(User, subject_id)
    if u is None:
        raise HTTPException(status_code=404, detail="User not found")
    return u


def _plan_intersects_month(plan: WeekPlan, month_start: str, month_end: str) -> bool:
    end_s = getattr(plan, "end_date", None) or plan.week_start
    return plan.week_start <= month_end and end_s >= month_start


def _month_bounds(month: str) -> tuple[str, str]:
    try:
        y_s, m_s = month.split("-", 1)
        y, m = int(y_s), int(m_s)
        if m < 1 or m > 12:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="month must be YYYY-MM") from exc
    last = monthrange(y, m)[1]
    return date(y, m, 1).isoformat(), date(y, m, last).isoformat()


@router.get("")
def get_or_list_week_plans(
    week_start: str | None = Query(
        default=None, description="legacy: Monday or any day in range"
    ),
    on: str | None = Query(default=None, description="plan covering this date"),
    list_all: bool = Query(default=False, alias="list"),
    month: str | None = Query(
        default=None, description="YYYY-MM filter for couple list"
    ),
    subject_user_id: str | None = Query(default=None, alias="user_id"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if list_all:
        if month:
            month_start, month_end = _month_bounds(month)
            couple = _couple_user_ids()
            rows = (
                db.query(WeekPlan)
                .filter(WeekPlan.user_id.in_(couple))
                .order_by(WeekPlan.week_start.desc(), WeekPlan.id.desc())
                .all()
            )
            rows = [
                p for p in rows if _plan_intersects_month(p, month_start, month_end)
            ]
            out: list[WeekPlanOut] = []
            for p in rows:
                subj = _load_subject_user(db, user, p.user_id)
                end_s = getattr(p, "end_date", None) or p.week_start
                out.append(_plan_to_out(p, subj, start=p.week_start, end=end_s))
            return out
        rows = (
            db.query(WeekPlan)
            .filter(WeekPlan.user_id == user.id)
            .order_by(WeekPlan.week_start.desc(), WeekPlan.id.desc())
            .limit(40)
            .all()
        )
        return [
            _plan_to_out(
                p,
                user,
                start=p.week_start,
                end=getattr(p, "end_date", None) or p.week_start,
            )
            for p in rows
        ]
    day = on or week_start
    if not day:
        raise HTTPException(
            status_code=422, detail="Provide on=, week_start=, or list=true"
        )
    subject = _load_subject_user(db, user, subject_user_id or user.id)
    plan = get_week_plan_for_user(subject, day, db)
    if plan is None:
        mon = monday_of(date.fromisoformat(day)).isoformat()
        sun = (date.fromisoformat(mon) + timedelta(days=6)).isoformat()
        return _plan_to_out(None, subject, start=mon, end=sun)
    end_s = getattr(plan, "end_date", None) or plan.week_start
    return _plan_to_out(plan, subject, start=plan.week_start, end=end_s)


@router.post("")
def create_week_plan(
    body: WeekPlanUpsert,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeekPlanOut:
    start = body.start_date or body.week_start
    if not start:
        raise HTTPException(status_code=422, detail="start_date required")
    start_s, end_s = _normalize_range(start, body.end_date)
    owner_id = _owner_id_from_body(body, user)
    owner = _load_subject_user(db, user, owner_id)
    plan = WeekPlan(user_id=owner_id, week_start=start_s)
    db.add(plan)
    _apply_upsert_fields(plan, body, start_s=start_s, end_s=end_s)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        existing = (
            db.query(WeekPlan)
            .filter(WeekPlan.user_id == owner_id, WeekPlan.week_start == start_s)
            .first()
        )
        if existing is None:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        plan = existing
        _apply_upsert_fields(plan, body, start_s=start_s, end_s=end_s)
        db.commit()
    db.refresh(plan)
    return _plan_to_out(
        plan, owner, start=plan.week_start, end=plan.end_date or plan.week_start
    )


@router.put("")
def upsert_week_plan(
    body: WeekPlanUpsert,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeekPlanOut:
    """Create or update by id / start_date."""
    start = body.start_date or body.week_start
    if not start:
        raise HTTPException(status_code=422, detail="start_date required")
    start_s, end_s = _normalize_range(start, body.end_date)
    owner_id = _owner_id_from_body(body, user)
    owner = _load_subject_user(db, user, owner_id)
    couple = _couple_user_ids()
    plan: WeekPlan | None = None
    if body.id is not None:
        plan = db.get(WeekPlan, body.id)
        if plan is None or plan.user_id not in couple:
            raise HTTPException(status_code=404, detail="Plan not found")
        if plan.user_id != owner_id:
            raise HTTPException(status_code=404, detail="Plan not found")
    else:
        plan = (
            db.query(WeekPlan)
            .filter(WeekPlan.user_id == owner_id, WeekPlan.week_start == start_s)
            .first()
        )
        if plan is None:
            plan = WeekPlan(user_id=owner_id, week_start=start_s)
            db.add(plan)
    _apply_upsert_fields(plan, body, start_s=start_s, end_s=end_s)
    db.commit()
    db.refresh(plan)
    return _plan_to_out(
        plan, owner, start=plan.week_start, end=plan.end_date or plan.week_start
    )


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_week_plan(
    plan_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    plan = db.get(WeekPlan, plan_id)
    couple = _couple_user_ids()
    if plan is None or plan.user_id not in couple:
        raise HTTPException(status_code=404, detail="Plan not found")
    db.delete(plan)
    db.commit()
