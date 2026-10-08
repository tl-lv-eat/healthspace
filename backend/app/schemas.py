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
