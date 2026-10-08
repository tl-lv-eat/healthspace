from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    default_water_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)

    meals: Mapped[list[Meal]] = relationship(back_populates="user")
    water_entries: Mapped[list[WaterEntry]] = relationship(back_populates="user")
    workouts: Mapped[list[Workout]] = relationship(back_populates="user")
    body_metrics: Mapped[list["BodyMetric"]] = relationship(back_populates="user")
    week_plans: Mapped[list["WeekPlan"]] = relationship(back_populates="user")


class Meal(Base):
    __tablename__ = "meals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(16), nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    food_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    ai_kcal: Mapped[int | None] = mapped_column(Integer, nullable=True)
    user_kcal: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    advice: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="meals")


class WaterEntry(Base):
    __tablename__ = "water_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    amount_ml: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="water_entries")


class Workout(Base):
    __tablename__ = "workouts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="workouts")


class BodyMetric(Base):
    __tablename__ = "body_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    recorded_on: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    chest_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hip_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="body_metrics")


class WeekPlan(Base):
    __tablename__ = "week_plans"
    __table_args__ = (UniqueConstraint("user_id", "week_start", name="uq_week_plan_user_week"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    # week_start kept as DB column name = plan start_date (YYYY-MM-DD)
    week_start: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    # Inclusive end date; defaults to start+6 when missing (legacy rows).
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    water_target_ml: Mapped[int] = mapped_column(Integer, nullable=False, default=2000)
    # Period calorie deficit target (kcal). Split evenly across period days.
    weekly_kcal_deficit: Mapped[int] = mapped_column(Integer, nullable=False, default=3500)
    # Target number of workout days in this period (not every day).
    weekly_workout_sessions: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Legacy completion modes (still used by today checkboxes / points).
    meal_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="three_main")
    workout_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="any")
    workout_cardio_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workout_strength_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    note: Mapped[str] = mapped_column(Text, nullable=False, default="")
    daily_kcal_cap: Mapped[int | None] = mapped_column(Integer, nullable=True)

    user: Mapped[User] = relationship(back_populates="week_plans")


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    name_zh: Mapped[str] = mapped_column(String(128), nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    body_part: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    gif_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    instructions_zh: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)


class PointsLedger(Base):
    __tablename__ = "points_ledger"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_points_idempotency_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)
    end_date: Mapped[str | None] = mapped_column(String(10), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Reward(Base):
    __tablename__ = "rewards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    creator_user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    scale_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cost_note: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    points_price: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="food")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending_review")
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Redemption(Base):
    __tablename__ = "redemptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    reward_id: Mapped[int] = mapped_column(Integer, ForeignKey("rewards.id"), nullable=False, index=True)
    redeemer_user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    points_spent: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AiReport(Base):
    __tablename__ = "ai_reports"
    __table_args__ = (UniqueConstraint("user_id", "kind", "period_key", name="uq_ai_report_user_kind_period"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    period_key: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class CoupleSettings(Base):
    """Shared couple-wide points settlement configuration (single row id=1)."""

    __tablename__ = "couple_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    settle_hour: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points_daily_water: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    points_daily_deficit: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    points_daily_workout_40: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    points_plan_tier_b: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    points_plan_tier_a: Mapped[int] = mapped_column(Integer, nullable=False, default=-2)
    points_plan_tier_fail: Mapped[int] = mapped_column(Integer, nullable=False, default=-5)


class SettlementRun(Base):
    """Idempotency record for daily / plan settlement runs."""

    __tablename__ = "settlement_runs"
    __table_args__ = (UniqueConstraint("run_date", "kind", name="uq_settlement_run_date_kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    meta_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class Achievement(Base):
    """Achievement catalog (shared rules or persona-specific thresholds)."""

    __tablename__ = "achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    scope: Mapped[str] = mapped_column(String(16), nullable=False, default="shared")
    metric: Mapped[str] = mapped_column(String(32), nullable=False)
    target_value: Mapped[float] = mapped_column(Float, nullable=False)
    points_reward: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    rule_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    bind_user_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("users.id"), nullable=True)
    bind_sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class UserAchievement(Base):
    """Manual claim record when user collects achievement points."""

    __tablename__ = "user_achievements"
    __table_args__ = (UniqueConstraint("user_id", "achievement_id", name="uq_user_achievement"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), nullable=False, index=True)
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey("achievements.id"), nullable=False, index=True)
    claimed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class PushBinding(Base):
    __tablename__ = "push_bindings"

    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), primary_key=True)
    token: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    remind_hours_json: Mapped[str] = mapped_column(Text, nullable=False, default="[12,21]")
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
