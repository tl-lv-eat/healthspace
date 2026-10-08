from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import User, Workout
from backend.app.schemas import WorkoutCreate, WorkoutOut

router = APIRouter()

CARDIO_TYPES = frozenset({"run", "walk", "cycle", "rope", "elliptical", "other"})
WORKOUT_KINDS = frozenset({"cardio", "strength"})


def _workout_to_out(workout: Workout) -> WorkoutOut:
    created = (
        workout.created_at.isoformat()
        if isinstance(workout.created_at, datetime)
        else str(workout.created_at)
    )
    try:
        payload = json.loads(workout.payload) if workout.payload else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    return WorkoutOut(
        id=workout.id,
        user_id=workout.user_id,
        date=workout.date,
        kind=workout.kind,
        payload=payload,
        created_at=created,
    )


def _validate_workout_create(body: WorkoutCreate) -> dict:
    if body.kind not in WORKOUT_KINDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"kind must be one of: {', '.join(sorted(WORKOUT_KINDS))}",
        )
    if body.kind == "cardio":
        if not body.cardio_type or body.cardio_type not in CARDIO_TYPES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"cardio_type must be one of: {', '.join(sorted(CARDIO_TYPES))}",
            )
        if body.duration_min is None or body.duration_min <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="duration_min must be a positive integer",
            )
        payload: dict = {
            "cardio_type": body.cardio_type,
            "duration_min": body.duration_min,
        }
        if body.intensity:
            payload["intensity"] = body.intensity
        return payload

    if not body.body_part or not body.body_part.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="body_part is required for strength workouts",
        )
    if not body.exercise_name or not body.exercise_name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="exercise_name is required for strength workouts",
        )
    if not body.sets:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sets must contain at least one entry for strength workouts",
        )
    sets_payload = []
    for s in body.sets:
        if s.reps <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="each set must have reps > 0",
            )
        item: dict = {"reps": s.reps}
        if s.weight is not None:
            item["weight"] = s.weight
        sets_payload.append(item)
    payload = {
        "body_part": body.body_part.strip(),
        "exercise_name": body.exercise_name.strip(),
        "sets": sets_payload,
    }
    if body.exercise_id is not None:
        payload["exercise_id"] = body.exercise_id
    return payload


def _get_owned_workout(workout_id: int, user: User, db: Session) -> Workout:
    workout = db.get(Workout, workout_id)
    if workout is None or workout.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout not found")
    return workout


@router.post("", response_model=WorkoutOut)
def create_workout(
    body: WorkoutCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WorkoutOut:
    payload = _validate_workout_create(body)
    workout = Workout(
        user_id=user.id,
        date=body.date,
        kind=body.kind,
        payload=json.dumps(payload, ensure_ascii=False),
    )
    db.add(workout)
    db.commit()
    db.refresh(workout)
    from backend.app.services.points_hooks import after_daily_activity

    after_daily_activity(db, user.id, body.date)
    return _workout_to_out(workout)


@router.get("", response_model=list[WorkoutOut])
def list_workouts(
    date: str = Query(..., description="YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WorkoutOut]:
    rows = (
        db.query(Workout)
        .filter(Workout.user_id == user.id, Workout.date == date)
        .order_by(Workout.created_at.asc())
        .all()
    )
    return [_workout_to_out(w) for w in rows]


@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    workout = _get_owned_workout(workout_id, user, db)
    db.delete(workout)
    db.commit()
