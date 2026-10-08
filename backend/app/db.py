from __future__ import annotations

from collections.abc import Generator

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models import Base, User
from backend.app.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

engine = create_engine(
    get_settings().database_url,
    connect_args={"check_same_thread": False} if get_settings().database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
