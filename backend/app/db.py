from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models import Base, User
from backend.app.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _ensure_sqlite_parent_dir(database_url: str) -> None:
    if database_url == "sqlite:///:memory:" or not database_url.startswith("sqlite"):
        return
    if database_url.startswith("sqlite:///"):
        raw = database_url[len("sqlite:///") :]
    else:
        raw = database_url[len("sqlite://") :]
    if not raw:
        return
    if raw.startswith("/") and len(raw) >= 3 and raw[2] == ":":
        raw = raw[1:]
    db_path = Path(raw)
    db_path.parent.mkdir(parents=True, exist_ok=True)


def _make_engine(database_url: str) -> Engine:
    _ensure_sqlite_parent_dir(database_url)
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    return create_engine(database_url, connect_args=connect_args)


def rebind_engine() -> None:
    global engine, SessionLocal
    settings = get_settings()
    engine = _make_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


rebind_engine()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


_LEGACY_DISPLAY_NAMES = {
    "dragon": {"🐉", "Dragon"},
    "leaf": {"🍃", "Leaf"},
}


def _ensure_user_profile_columns() -> None:
    """SQLite additive migrate for user sex/age (BMR)."""
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
        existing = {r[1] for r in rows}
        alters = []
        if "sex" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN sex VARCHAR(16)")
        if "age" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN age INTEGER")
        for sql in alters:
            conn.exec_driver_sql(sql)


def _ensure_week_plan_columns() -> None:
    """SQLite additive migrate for week-plan energy fields."""
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(week_plans)").fetchall()
        existing = {r[1] for r in rows}
        alters = []
        if "weekly_kcal_deficit" not in existing:
            alters.append(
                "ALTER TABLE week_plans ADD COLUMN weekly_kcal_deficit INTEGER NOT NULL DEFAULT 3500"
            )
        if "weekly_workout_sessions" not in existing:
            alters.append(
                "ALTER TABLE week_plans ADD COLUMN weekly_workout_sessions INTEGER NOT NULL DEFAULT 4"
            )
        if "target_weight_kg" not in existing:
            alters.append("ALTER TABLE week_plans ADD COLUMN target_weight_kg FLOAT")
        if "end_date" not in existing:
            alters.append("ALTER TABLE week_plans ADD COLUMN end_date VARCHAR(10)")
        for sql in alters:
            conn.exec_driver_sql(sql)
        # Backfill end_date = week_start + 6 days for legacy rows
        rows = conn.exec_driver_sql(
            "SELECT id, week_start FROM week_plans WHERE end_date IS NULL OR end_date = ''"
        ).fetchall()
        for rid, ws in rows:
            try:
                from datetime import date, timedelta

                end = (date.fromisoformat(ws) + timedelta(days=6)).isoformat()
                conn.exec_driver_sql(
                    "UPDATE week_plans SET end_date = ? WHERE id = ?",
                    (end, rid),
                )
            except ValueError:
                pass


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_user_profile_columns()
    _ensure_week_plan_columns()
    settings = get_settings()
    with SessionLocal() as db:
        for user_cfg in settings.users:
            existing = db.get(User, user_cfg.id)
            if existing is None:
                db.add(
                    User(
                        id=user_cfg.id,
                        display_name=user_cfg.display_name,
                        password_hash=_hash_password(user_cfg.password),
                        default_water_ml=user_cfg.default_water_ml,
                        role=user_cfg.role,
                    )
                )
                continue
            # One-shot migrate old emoji defaults → 龙龙/叶子 (skip if user renamed).
            legacy = _LEGACY_DISPLAY_NAMES.get(user_cfg.id, set())
            if existing.display_name in legacy:
                existing.display_name = user_cfg.display_name
        db.commit()
