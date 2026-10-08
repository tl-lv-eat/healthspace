from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import Meal, User
from backend.app.schemas import MealCreate, MealEstimateOut, MealOut, MealPatch
from backend.app.services.uploads import meal_upload_root, save_meal_image

router = APIRouter()

MEAL_TYPES = frozenset({"breakfast", "lunch", "dinner", "snack"})


def _validate_meal_type(meal_type: str) -> None:
    if meal_type not in MEAL_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"meal_type must be one of: {', '.join(sorted(MEAL_TYPES))}",
        )


def _meal_to_out(meal: Meal) -> MealOut:
    created = meal.created_at.isoformat() if isinstance(meal.created_at, datetime) else str(meal.created_at)
    return MealOut(
        id=meal.id,
        user_id=meal.user_id,
        date=meal.date,
        meal_type=meal.meal_type,
        image_path=meal.image_path,
        food_summary=meal.food_summary,
        ai_kcal=meal.ai_kcal,
        user_kcal=meal.user_kcal,
        advice=meal.advice,
        created_at=created,
    )


def _validate_meal_image_path(image_path: str | None, user_id: str) -> None:
    if image_path is None:
        return
    prefix = f"{user_id}/"
    if ".." in image_path or image_path.startswith("/") or "\\" in image_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image_path")
    if not image_path.startswith(prefix):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="image_path must belong to the current user",
        )
    rest = image_path[len(prefix) :]
    if not rest or "/" in rest:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image_path")


def _get_owned_meal(meal_id: int, user: User, db: Session) -> Meal:
    meal = db.get(Meal, meal_id)
    if meal is None or meal.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal not found")
    return meal


@router.post("/estimate", response_model=MealEstimateOut)
def estimate_meal(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
) -> MealEstimateOut:
    relative = save_meal_image(file, user.id)
    full_path = meal_upload_root() / relative
    from backend.app.services.meal_ai import MealAIError, estimate_calories_from_image

    try:
        result = estimate_calories_from_image(full_path)
    except MealAIError:
        return MealEstimateOut(
            food_summary="",
            kcal=0,
            advice="",
            image_path=relative,
            estimate_failed=True,
        )
    return MealEstimateOut(
        food_summary=str(result["food_summary"]),
        kcal=int(result["kcal"]),
        advice=str(result.get("advice", "")),
        image_path=relative,
    )


@router.post("", response_model=MealOut)
def create_meal(
    body: MealCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MealOut:
    _validate_meal_type(body.meal_type)
    _validate_meal_image_path(body.image_path, user.id)
    meal = Meal(
        user_id=user.id,
        date=body.date,
        meal_type=body.meal_type,
        food_summary=body.food_summary,
        ai_kcal=body.ai_kcal,
        user_kcal=body.user_kcal,
        advice=body.advice,
        image_path=body.image_path,
    )
    db.add(meal)
    db.commit()
    db.refresh(meal)
    from backend.app.services.points_hooks import after_daily_activity

    after_daily_activity(db, user.id, body.date)
    return _meal_to_out(meal)


@router.get("", response_model=list[MealOut])
def list_meals(
    date: str = Query(..., description="YYYY-MM-DD"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MealOut]:
    rows = (
        db.query(Meal)
        .filter(Meal.user_id == user.id, Meal.date == date)
        .order_by(Meal.created_at.asc())
        .all()
    )
    return [_meal_to_out(m) for m in rows]


@router.patch("/{meal_id}", response_model=MealOut)
def patch_meal(
    meal_id: int,
    body: MealPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MealOut:
    meal = _get_owned_meal(meal_id, user, db)
    if body.user_kcal is not None:
        meal.user_kcal = body.user_kcal
    if body.food_summary is not None:
        meal.food_summary = body.food_summary
    db.commit()
    db.refresh(meal)
    from backend.app.services.points_hooks import after_daily_activity

    after_daily_activity(db, user.id, meal.date)
    return _meal_to_out(meal)
