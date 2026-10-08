from __future__ import annotations

from pydantic import BaseModel


class LoginRequest(BaseModel):
    user_id: str
    password: str


class UserOut(BaseModel):
    id: str
    display_name: str
    default_water_ml: int
    role: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class MealEstimateOut(BaseModel):
    food_summary: str
    kcal: int
    advice: str
    image_path: str
    estimate_failed: bool = False


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
    week_start: str
    water_target_ml: int
    meal_mode: str = "three_main"
    workout_mode: str = "any"
    workout_cardio_min: int | None = None
    workout_strength_sets: int | None = None


class WeekPlanOut(BaseModel):
    id: int | None
    user_id: str
    week_start: str
    water_target_ml: int
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
