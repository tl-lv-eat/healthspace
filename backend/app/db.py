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


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()
    with SessionLocal() as db:
        for user_cfg in settings.users:
            existing = db.get(User, user_cfg.id)
            if existing is not None:
                continue
            db.add(
                User(
                    id=user_cfg.id,
                    display_name=user_cfg.display_name,
                    password_hash=_hash_password(user_cfg.password),
                    default_water_ml=user_cfg.default_water_ml,
                    role=user_cfg.role,
                )
            )
        db.commit()
