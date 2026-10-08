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
