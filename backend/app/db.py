from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.models import Achievement, Base, Reward, User
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
    "leaf": {"🍃", "Leaf", "叶子"},
}


def _ensure_user_profile_columns() -> None:
    """SQLite additive migrate for user sex/age/bmr_kcal."""
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
        if "bmr_kcal" not in existing:
            alters.append("ALTER TABLE users ADD COLUMN bmr_kcal INTEGER")
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
        if "title" not in existing:
            alters.append("ALTER TABLE week_plans ADD COLUMN title VARCHAR(128)")
        if "note" not in existing:
            alters.append("ALTER TABLE week_plans ADD COLUMN note TEXT NOT NULL DEFAULT ''")
        if "daily_kcal_cap" not in existing:
            alters.append("ALTER TABLE week_plans ADD COLUMN daily_kcal_cap INTEGER")
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


def _ensure_reward_mall_columns() -> None:
    """SQLite additive migrate for reward category + review workflow."""
    if not str(engine.url).startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.exec_driver_sql("PRAGMA table_info(rewards)").fetchall()
        existing = {r[1] for r in rows}
        alters = []
        if "category" not in existing:
            alters.append("ALTER TABLE rewards ADD COLUMN category VARCHAR(32) NOT NULL DEFAULT 'food'")
        if "status" not in existing:
            alters.append(
                "ALTER TABLE rewards ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'pending_review'"
            )
        if "reject_reason" not in existing:
            alters.append("ALTER TABLE rewards ADD COLUMN reject_reason TEXT")
        if "reviewed_by" not in existing:
            alters.append("ALTER TABLE rewards ADD COLUMN reviewed_by VARCHAR(32)")
        if "reviewed_at" not in existing:
            alters.append("ALTER TABLE rewards ADD COLUMN reviewed_at DATETIME")
        for sql in alters:
            conn.exec_driver_sql(sql)
        if "status" in existing or any("status" in a for a in alters):
            conn.exec_driver_sql(
                "UPDATE rewards SET status = 'listed', active = 1 "
                "WHERE (status IS NULL OR status = 'pending_review') AND active = 1"
            )
            conn.exec_driver_sql(
                "UPDATE rewards SET status = 'archived', active = 0 "
                "WHERE (status IS NULL OR status = 'pending_review') AND active = 0"
            )


_DEFAULT_ACHIEVEMENTS: list[dict] = [
    {
        "slug": "green_days_7",
        "title": "绿日达人",
        "description": "累计 7 个日历绿日（饮水达标且热量未超标）",
        "scope": "shared",
        "metric": "green_days_total",
        "target_value": 7,
        "points_reward": 10,
        "sort_order": 10,
    },
    {
        "slug": "green_streak_3",
        "title": "连续自律",
        "description": "最长连续 3 天绿日",
        "scope": "shared",
        "metric": "green_streak",
        "target_value": 3,
        "points_reward": 15,
        "sort_order": 20,
    },
    {
        "slug": "workouts_5",
        "title": "运动起步",
        "description": "累计记录 5 次运动",
        "scope": "shared",
        "metric": "workout_sessions",
        "target_value": 5,
        "points_reward": 10,
        "sort_order": 30,
    },
    {
        "slug": "workout_minutes_100",
        "title": "百炼成钢",
        "description": "运动总时长达到 100 分钟",
        "scope": "shared",
        "metric": "workout_minutes_total",
        "target_value": 100,
        "points_reward": 20,
        "sort_order": 40,
    },
    {
        "slug": "water_ok_7",
        "title": "饮水常客",
        "description": "累计 7 天饮水达标",
        "scope": "shared",
        "metric": "water_ok_days",
        "target_value": 7,
        "points_reward": 10,
        "sort_order": 50,
    },
    {
        "slug": "bmi_healthy",
        "title": "BMI 健康区间",
        "description": "最新身体数据 BMI 落在健康区间",
        "scope": "persona",
        "metric": "bmi_in_range",
        "target_value": 1,
        "points_reward": 25,
        "rule_json": '{"bmi_min": 18.5, "bmi_max": 24.0}',
        "sort_order": 60,
    },
    {
        "slug": "body_fat_ok",
        "title": "体脂达标",
        "description": "最新体脂率在性别默认上限以内（男 20% / 女 28%）",
        "scope": "persona",
        "metric": "body_fat_max",
        "target_value": 1,
        "points_reward": 30,
        "rule_json": '{"male_max": 20, "female_max": 28}',
        "sort_order": 70,
    },
]


def _seed_default_achievements(db: Session) -> None:
    for spec in _DEFAULT_ACHIEVEMENTS:
        if db.query(Achievement).filter(Achievement.slug == spec["slug"]).first():
            continue
        db.add(
            Achievement(
                slug=spec["slug"],
                title=spec["title"],
                description=spec["description"],
                scope=spec["scope"],
                metric=spec["metric"],
                target_value=float(spec["target_value"]),
                points_reward=int(spec["points_reward"]),
                rule_json=spec.get("rule_json", "{}"),
                sort_order=int(spec.get("sort_order", 0)),
            )
        )


# System mall seeds — already listed (skip partner review). cost_note holds seed key.
_DEFAULT_REWARDS: list[dict] = [
    {
        "seed_key": "seed:milk_tea",
        "title": "奶茶自由一次",
        "description": "任选一杯日常奶茶/咖啡，快乐续命。",
        "category": "food",
        "points_price": 12,
        "scale_level": 1,
        "creator_user_id": "dragon",
        "reviewed_by": "leaf",
    },
    {
        "seed_key": "seed:nice_dinner",
        "title": "双人像样晚餐",
        "description": "一起吃一顿不赶时间的正经晚饭（外卖或下馆子都行）。",
        "category": "food",
        "points_price": 35,
        "scale_level": 2,
        "creator_user_id": "leaf",
        "reviewed_by": "dragon",
    },
    {
        "seed_key": "seed:movie_night",
        "title": "电影之夜",
        "description": "电影院或家投影，选一部双方都想看的片，零食自备。",
        "category": "fun",
        "points_price": 20,
        "scale_level": 2,
        "creator_user_id": "dragon",
        "reviewed_by": "leaf",
    },
    {
        "seed_key": "seed:day_trip",
        "title": "半日小出行",
        "description": "城市周边走走：公园、展览、逛街，不赶通宵。",
        "category": "fun",
        "points_price": 45,
        "scale_level": 3,
        "creator_user_id": "leaf",
        "reviewed_by": "dragon",
    },
    {
        "seed_key": "seed:massage",
        "title": "肩颈按摩 15 分钟",
        "description": "对方提供肩颈/背部放松按摩约一刻钟。",
        "category": "intimacy",
        "points_price": 18,
        "scale_level": 2,
        "creator_user_id": "dragon",
        "reviewed_by": "leaf",
    },
    {
        "seed_key": "seed:cuddle_movie",
        "title": "依偎看剧一晚",
        "description": "关掉手机工作通知，抱着看一晚剧/综艺。",
        "category": "intimacy",
        "points_price": 15,
        "scale_level": 1,
        "creator_user_id": "leaf",
        "reviewed_by": "dragon",
    },
    {
        "seed_key": "seed:adult_wish",
        "title": "一夜所愿（双方协商）",
        "description": "在双方都同意的前提下，兑现一次私下约定的亲密愿望。",
        "category": "adult",
        "points_price": 60,
        "scale_level": 4,
        "is_private": True,
        "creator_user_id": "dragon",
        "reviewed_by": "leaf",
    },
    {
        "seed_key": "seed:breakfast_bed",
        "title": "床边早餐投喂",
        "description": "对方做好/买好早餐送到床边，不许催起床干活。",
        "category": "food",
        "points_price": 22,
        "scale_level": 2,
        "creator_user_id": "leaf",
        "reviewed_by": "dragon",
    },
]


def _seed_default_rewards(db: Session) -> None:
    from datetime import datetime

    for spec in _DEFAULT_REWARDS:
        key = spec["seed_key"]
        if db.query(Reward).filter(Reward.cost_note == key).first():
            continue
        db.add(
            Reward(
                creator_user_id=spec["creator_user_id"],
                title=spec["title"],
                description=spec["description"],
                is_private=bool(spec.get("is_private", False)),
                scale_level=int(spec.get("scale_level", 1)),
                cost_note=key,
                points_price=int(spec["points_price"]),
                category=spec["category"],
                status="listed",
                active=True,
                reviewed_by=spec["reviewed_by"],
                reviewed_at=datetime.utcnow(),
            )
        )


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_user_profile_columns()
    _ensure_week_plan_columns()
    _ensure_reward_mall_columns()
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
        _seed_default_achievements(db)
        _seed_default_rewards(db)
        db.commit()
