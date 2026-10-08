from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.auth import get_current_user
from backend.app.db import get_db
from backend.app.models import Redemption, Reward, User
from backend.app.services.points import get_balance, grant
from backend.app.settings import get_settings

router = APIRouter()


class RewardCreate(BaseModel):
    title: str
    description: str = ""
    is_private: bool = False
    scale_level: int = Field(default=1, ge=1, le=5)
    cost_note: str = ""
    points_price: int = Field(..., gt=0)


class RewardPatch(BaseModel):
    title: str | None = None
    description: str | None = None
    is_private: bool | None = None
    scale_level: int | None = Field(default=None, ge=1, le=5)
    cost_note: str | None = None
    points_price: int | None = Field(default=None, gt=0)
    active: bool | None = None


class RedemptionPatch(BaseModel):
    status: str


class RewardOut(BaseModel):
    id: int
    creator_user_id: str
    title: str
    description: str | None
    is_private: bool
    scale_level: int
    cost_note: str
    points_price: int
    active: bool
    created_at: str


class RedemptionOut(BaseModel):
    id: int
    reward_id: int
    redeemer_user_id: str
    points_spent: int
    status: str
    created_at: str
    fulfilled_at: str | None
    reward_title: str | None = None


def _reward_to_out(row: Reward, *, reveal: bool = False) -> RewardOut:
    created = row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at)
    desc: str | None = row.description
    if row.is_private and not reveal:
        desc = None
    return RewardOut(
        id=row.id,
        creator_user_id=row.creator_user_id,
        title=row.title,
        description=desc,
        is_private=row.is_private,
        scale_level=row.scale_level,
        cost_note=row.cost_note,
        points_price=row.points_price,
        active=row.active,
        created_at=created,
    )


def _allowed_user_ids() -> frozenset[str]:
    return frozenset(u.id for u in get_settings().users)


@router.get("")
def list_rewards(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RewardOut]:
    _ = user
    rows = (
        db.query(Reward)
        .filter(Reward.creator_user_id.in_(_allowed_user_ids()), Reward.active.is_(True))
        .order_by(Reward.created_at.desc())
        .all()
    )
    return [_reward_to_out(r) for r in rows]


@router.post("")
def create_reward(
    body: RewardCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RewardOut:
    row = Reward(
        creator_user_id=user.id,
        title=body.title.strip(),
        description=body.description,
        is_private=body.is_private,
        scale_level=body.scale_level,
        cost_note=body.cost_note,
        points_price=body.points_price,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _reward_to_out(row, reveal=True)


@router.patch("/{reward_id}")
def patch_reward(
    reward_id: int,
    body: RewardPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RewardOut:
    row = db.get(Reward, reward_id)
    if row is None or row.creator_user_id not in _allowed_user_ids():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reward not found")
    if row.creator_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your reward")
    if body.title is not None:
        row.title = body.title.strip()
    if body.description is not None:
        row.description = body.description
    if body.is_private is not None:
        row.is_private = body.is_private
    if body.scale_level is not None:
        row.scale_level = body.scale_level
    if body.cost_note is not None:
        row.cost_note = body.cost_note
    if body.points_price is not None:
        row.points_price = body.points_price
    if body.active is not None:
        row.active = body.active
    db.commit()
    db.refresh(row)
    return _reward_to_out(row, reveal=True)


@router.post("/{reward_id}/reveal")
def reveal_reward(
    reward_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _ = user
    row = db.get(Reward, reward_id)
    if row is None or row.creator_user_id not in _allowed_user_ids():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reward not found")
    return {"description": row.description}


@router.post("/{reward_id}/redeem")
def redeem_reward(
    reward_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedemptionOut:
    row = db.get(Reward, reward_id)
    if row is None or not row.active or row.creator_user_id not in _allowed_user_ids():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reward not found")
    price = row.points_price
    if get_balance(db, user.id) < price:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient points")
    redeem_key = f"redeem:{user.id}:{uuid.uuid4()}"
    ok, _ = grant(db, user.id, -price, "redeem", redeem_key, meta={"reward_id": reward_id})
    if not ok:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Redeem failed")
    redemption = Redemption(
        reward_id=reward_id,
        redeemer_user_id=user.id,
        points_spent=price,
        status="pending",
    )
    db.add(redemption)
    db.commit()
    db.refresh(redemption)
    return _redemption_to_out(redemption, row.title)


def _redemption_to_out(r: Redemption, reward_title: str | None = None) -> RedemptionOut:
    created = r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at)
    fulfilled = None
    if r.fulfilled_at is not None:
        fulfilled = r.fulfilled_at.isoformat() if isinstance(r.fulfilled_at, datetime) else str(r.fulfilled_at)
    return RedemptionOut(
        id=r.id,
        reward_id=r.reward_id,
        redeemer_user_id=r.redeemer_user_id,
        points_spent=r.points_spent,
        status=r.status,
        created_at=created,
        fulfilled_at=fulfilled,
        reward_title=reward_title,
    )


@router.get("/redemptions/mine")
def my_redemptions(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RedemptionOut]:
    rows = (
        db.query(Redemption)
        .filter(Redemption.redeemer_user_id == user.id)
        .order_by(Redemption.created_at.desc())
        .all()
    )
    out = []
    for r in rows:
        reward = db.get(Reward, r.reward_id)
        title = reward.title if reward else None
        out.append(_redemption_to_out(r, title))
    return out


@router.patch("/redemptions/{redemption_id}")
def patch_redemption(
    redemption_id: int,
    body: RedemptionPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RedemptionOut:
    _ = user
    r = db.get(Redemption, redemption_id)
    if r is None or r.redeemer_user_id not in _allowed_user_ids():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Redemption not found")
    if body.status not in ("fulfilled", "cancelled"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid status")
    if r.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Redemption not pending")
    if body.status == "fulfilled":
        r.status = "fulfilled"
        r.fulfilled_at = datetime.utcnow()
    else:
        r.status = "cancelled"
        grant(
            db,
            r.redeemer_user_id,
            r.points_spent,
            "redeem_refund",
            f"redeem_refund:{r.id}",
            meta={"redemption_id": r.id},
        )
    db.commit()
    db.refresh(r)
    reward = db.get(Reward, r.reward_id)
    return _redemption_to_out(r, reward.title if reward else None)
