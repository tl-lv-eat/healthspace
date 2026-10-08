from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]


class UserConfig(BaseModel):
    id: str
    password: str
    display_name: str
    default_water_ml: int = 2000
    role: str = "member"


class PointsConfig(BaseModel):
    daily_all_three: int = 10
    weekly_plan_complete: int = 50
    goal_complete: int = 20


class ScheduleConfig(BaseModel):
    daily_report_hour: int = 22
    daily_report_minute: int = 0
    weekly_report_weekday: int = 0
    weekly_report_hour: int = 0
    weekly_report_minute: int = 30
    reminder_hours: list[int] = Field(default_factory=lambda: [12, 21])


class Settings(BaseModel):
    database_url: str = "sqlite:///./data/jianfei.db"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_hours: int = 720
    upload_dir: str = "uploads/meals"
    users: list[UserConfig] = Field(default_factory=list)
    points: PointsConfig = Field(default_factory=PointsConfig)
    schedule: ScheduleConfig = Field(default_factory=ScheduleConfig)


def _config_path() -> Path:
    env = os.environ.get("JIANFEI_CONFIG", "").strip()
    if env:
        return Path(env)
    local = ROOT / "config.yaml"
    if local.is_file():
        return local
    return ROOT / "config.example.yaml"


def _load_yaml_app_section() -> dict[str, Any]:
    path = _config_path()
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("app") or {}


def _default_users() -> list[UserConfig]:
    return [
        UserConfig(
            id="dragon",
            password="dragon-pass",
            display_name="🐉",
            default_water_ml=2000,
            role="member",
        ),
        UserConfig(
            id="leaf",
            password="leaf-pass",
            display_name="🍃",
            default_water_ml=2000,
            role="member",
        ),
    ]


def _build_settings() -> Settings:
    app = _load_yaml_app_section()
    users_raw = app.get("users")
    if users_raw:
        users = [UserConfig.model_validate(u) for u in users_raw]
    else:
        users = _default_users()

    database_url = os.environ.get("DATABASE_URL") or app.get("database_url") or Settings.model_fields["database_url"].default
    jwt_secret = os.environ.get("JWT_SECRET") or app.get("jwt_secret") or Settings.model_fields["jwt_secret"].default
    jwt_expire_hours = int(
        os.environ.get("JWT_EXPIRE_HOURS") or app.get("jwt_expire_hours") or Settings.model_fields["jwt_expire_hours"].default
    )
    upload_dir = os.environ.get("UPLOAD_DIR") or app.get("upload_dir") or Settings.model_fields["upload_dir"].default
    points_raw = app.get("points") or {}
    points = PointsConfig.model_validate(points_raw) if points_raw else PointsConfig()
    schedule_raw = app.get("schedule") or {}
    schedule = ScheduleConfig.model_validate(schedule_raw) if schedule_raw else ScheduleConfig()

    return Settings(
        database_url=database_url,
        jwt_secret=jwt_secret,
        jwt_expire_hours=jwt_expire_hours,
        upload_dir=upload_dir,
        users=users,
        points=points,
        schedule=schedule,
    )


@lru_cache
def get_settings() -> Settings:
    return _build_settings()


def clear_settings_cache() -> None:
    get_settings.cache_clear()
