from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    user_id: str
    password: str


class SelectRequest(BaseModel):
    user_id: str


class ProfileUpdateRequest(BaseModel):
    display_name: str
    sex: str | None = None  # male|female
    age: int | None = None


class UserOut(BaseModel):
    id: str
    display_name: str
    default_water_ml: int
    role: str
    sex: str | None = None
    age: int | None = None

    model_config = {"from_attributes": True}


class PersonaOut(BaseModel):
    id: str
    display_name: str
    emoji: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MealEstimateOut(BaseModel):
    food_summary: str
    kcal: int
    advice: str
    reason: str = ""
    image_path: str
    estimate_failed: bool = False


class MealRefineIn(BaseModel):
    image_path: str | None = None
    food_summary: str
    kcal: int
    reason: str = ""
    advice: str = ""
    message: str


class MealCreate(BaseModel):
    date: str
    meal_type: str
    food_summary: str
    ai_kcal: int | None = None
    user_kcal: int
    advice: str = ""
    image_path: str | None = None


class MealPatch(BaseModel):
    user_kcal: int | None = None
    food_summary: str | None = None


class MealOut(BaseModel):
    id: int
    user_id: str
    date: str
    meal_type: str
    image_path: str | None
    food_summary: str
    ai_kcal: int | None
    user_kcal: int
    advice: str
    created_at: str

    model_config = {"from_attributes": True}


class WaterCreate(BaseModel):
    date: str
    amount_ml: int


class WaterPatch(BaseModel):
    amount_ml: int


class WaterEntryOut(BaseModel):
    id: int
    user_id: str
    date: str
    amount_ml: int
    created_at: str

    model_config = {"from_attributes": True}


class WaterDayOut(BaseModel):
    target_ml: int
    total_ml: int
    entries: list[WaterEntryOut]


class WorkoutSetIn(BaseModel):
    reps: int
    weight: float | None = None


class WorkoutCreate(BaseModel):
    date: str
    kind: str
    cardio_type: str | None = None
    duration_min: int | None = None
    intensity: str | None = None
    body_part: str | None = None
    exercise_id: int | None = None
    exercise_name: str | None = None
    sets: list[WorkoutSetIn] | None = None


class WorkoutOut(BaseModel):
    id: int
    user_id: str
    date: str
    kind: str
    payload: dict
    created_at: str


class WorkoutPatch(BaseModel):
    """Partial update — fields depend on kind (cardio vs strength)."""

    cardio_type: str | None = None
    duration_min: int | None = None
    intensity: str | None = None
    body_part: str | None = None
    exercise_name: str | None = None
    exercise_id: int | None = None
    sets: list[WorkoutSetIn] | None = None


class ExerciseCreate(BaseModel):
    name_zh: str
    name_en: str = ""
    body_part: str
    instructions_zh: str = ""
    gif_url: str = ""


class BodyMetricCreate(BaseModel):
    recorded_on: str
    weight_kg: float | None = None
    waist_cm: float | None = None
    body_fat_pct: float | None = None
    chest_cm: float | None = None
    hip_cm: float | None = None
    height_cm: float | None = None
    note: str = ""


class BodyMetricOut(BaseModel):
    id: int
    user_id: str
    recorded_on: str
    weight_kg: float | None
    waist_cm: float | None
    body_fat_pct: float | None
    chest_cm: float | None
    hip_cm: float | None
    height_cm: float | None
    note: str
    created_at: str
    bmi: float | None = None


class WeekPlanUpsert(BaseModel):
    id: int | None = None
    week_start: str | None = None  # legacy alias for start_date
    start_date: str | None = None
    end_date: str | None = None
    water_target_ml: int
    weekly_kcal_deficit: int = 3500
    weekly_workout_sessions: int = 4
    target_weight_kg: float | None = None
    meal_mode: str = "three_main"
    workout_mode: str = "any"
    workout_cardio_min: int | None = None
    workout_strength_sets: int | None = None


class WeekPlanOut(BaseModel):
    id: int | None
    user_id: str
    week_start: str  # = start_date (compat)
    start_date: str
    end_date: str
    period_days: int = 7
    water_target_ml: int
    weekly_kcal_deficit: int = 3500
    weekly_workout_sessions: int = 4
    target_weight_kg: float | None = None
    meal_mode: str
    workout_mode: str
    workout_cardio_min: int | None = None
    workout_strength_sets: int | None = None


class ExerciseOut(BaseModel):
    id: int
    slug: str
    name_zh: str
    name_en: str
    body_part: str
    gif_url: str
    instructions_zh: str
    is_custom: bool
    owner_user_id: str | None

    model_config = {"from_attributes": True}
