from backend.app.models import BodyMetric, User
from backend.app.services.energy import (
    daily_energy_snapshot,
    estimate_workout_burn_kcal,
    resolve_body_profile,
    user_bmr,
)


def test_user_bmr_uses_stored_value(db_session, client):
    dragon_user = db_session.get(User, "dragon")
    assert dragon_user is not None
    dragon_user.bmr_kcal = 1550
    db_session.add(dragon_user)
    db_session.commit()
    assert user_bmr(dragon_user, db_session) == 1550
    dragon_user.bmr_kcal = 1820
    db_session.commit()
    assert user_bmr(dragon_user, db_session) == 1820


def test_user_bmr_falls_back_to_persona_default(db_session, client):
    dragon_user = db_session.get(User, "dragon")
    assert dragon_user is not None
    dragon_user.bmr_kcal = None
    db_session.commit()
    assert user_bmr(dragon_user, db_session) == 1700


def test_resolve_body_profile_prefers_user_fields(db_session, client):
    u = db_session.get(User, "dragon")
    assert u is not None
    u.sex = "female"
    u.age = 35
    db_session.commit()
    db_session.refresh(u)
    p = resolve_body_profile(u, db_session)
    assert p["sex"] == "female"
    assert p["age"] == 35


def test_resolve_body_profile_uses_body_metric_weight_height(db_session, client):
    u = db_session.get(User, "dragon")
    assert u is not None
    u.sex = "female"
    u.age = 35
    db_session.add(
        BodyMetric(
            user_id="dragon",
            recorded_on="2026-10-01",
            weight_kg=82.5,
            height_cm=180.0,
        )
    )
    db_session.commit()
    db_session.refresh(u)
    p = resolve_body_profile(u, db_session)
    assert p["sex"] == "female"
    assert p["age"] == 35
    assert p["weight_kg"] == 82.5
    assert p["height_cm"] == 180.0


def test_burn_cardio():
    assert estimate_workout_burn_kcal([{"kind": "cardio", "payload": {"duration_min": 30}}]) == 210


def test_surplus_exceeded():
    snap = daily_energy_snapshot(
        intake_kcal=2500,
        workouts=[],
        bmr=1600,
        water_ml=2000,
        water_target_ml=2000,
        weekly_kcal_deficit=3500,
    )
    assert snap["calorie_exceeded"] is True
    assert snap["water_ok"] is True
    assert snap["level"] == "partial"


def test_deficit_full_day():
    snap = daily_energy_snapshot(
        intake_kcal=1200,
        workouts=[{"kind": "cardio", "payload": {"duration_min": 40}}],
        bmr=1600,
        water_ml=2000,
        water_target_ml=2000,
        weekly_kcal_deficit=3500,
    )
    assert snap["calorie_ok"] is True
    assert snap["water_ok"] is True
    assert snap["level"] == "full"
    assert snap["deficit_contrib"] > 0


def test_empty_day_no_deficit_contrib():
    """Calendar plan progress must not credit BMR on completely empty days."""
    snap = daily_energy_snapshot(
        intake_kcal=0,
        workouts=[],
        bmr=1600,
        water_ml=0,
        water_target_ml=2000,
        weekly_kcal_deficit=3500,
    )
    assert snap["level"] == "none"
    assert snap["deficit_contrib"] == 0
    assert snap["meals_complete"] is False
    assert snap["surplus_kcal"] == -1600


def test_incomplete_meals_no_deficit_contrib():
    snap = daily_energy_snapshot(
        intake_kcal=500,
        workouts=[],
        bmr=1600,
        water_ml=2000,
        water_target_ml=2000,
        weekly_kcal_deficit=3500,
        meals_complete=False,
    )
    assert snap["deficit_contrib"] == 0
    assert snap["calorie_ok"] is False
    assert snap["meals_complete"] is False
