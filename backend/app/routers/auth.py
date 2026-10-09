from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.auth import create_access_token, get_current_user, verify_password
from backend.app.db import get_db
from backend.app.models import User
from backend.app.schemas import (
    LoginRequest,
    PersonaOut,
    ProfileUpdateRequest,
    SelectRequest,
    TokenResponse,
    UserOut,
)

router = APIRouter()

_PERSONA_EMOJI = {"dragon": "🐉", "leaf": "🍃"}


def _token_for_user(user: User) -> TokenResponse:
    token = create_access_token(user.id)
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.get(User, body.user_id)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return _token_for_user(user)


@router.post("/select", response_model=TokenResponse)
def select(body: SelectRequest, db: Session = Depends(get_db)) -> TokenResponse:
    """Private couple app: pick persona without password."""
    user = db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown user")
    return _token_for_user(user)


@router.get("/personas", response_model=list[PersonaOut])
def personas(db: Session = Depends(get_db)) -> list[PersonaOut]:
    rows = db.query(User).filter(User.id.in_(["dragon", "leaf"])).all()
    by_id = {u.id: u for u in rows}
    out: list[PersonaOut] = []
    for uid, emoji in _PERSONA_EMOJI.items():
        u = by_id.get(uid)
        if u is None:
            continue
        out.append(PersonaOut(id=u.id, display_name=u.display_name, emoji=emoji))
    return out


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)


@router.patch("/me", response_model=UserOut)
def update_me(
    body: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserOut:
    name = body.display_name.strip()
    if not name or len(name) > 32:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid display_name")
    current_user.display_name = name
    if body.sex in ("male", "female"):
        current_user.sex = body.sex
    if body.age is not None and isinstance(body.age, int) and 10 <= body.age <= 100:
        current_user.age = body.age
    if body.bmr_kcal is not None:
        if not isinstance(body.bmr_kcal, int) or not (800 <= body.bmr_kcal <= 4000):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="bmr_kcal must be an integer between 800 and 4000",
            )
        current_user.bmr_kcal = body.bmr_kcal
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return UserOut.model_validate(current_user)
