from backend.app.models import User
from backend.app.services.energy import (
    daily_energy_snapshot,
    estimate_workout_burn_kcal,
    mifflin_st_jeor_bmr,
    resolve_body_profile,
    user_bmr,
)


def test_user_bmr_uses_user_sex_age(db_session, client):
    dragon_user = db_session.get(User, "dragon")
    assert dragon_user is not None
    dragon_user.sex = "male"
    dragon_user.age = 40
    db_session.add(dragon_user)
    db_session.commit()
    bmr_old_age = user_bmr(dragon_user, db_session)
    dragon_user.age = 25
    db_session.commit()
    bmr_young = user_bmr(dragon_user, db_session)
    assert bmr_young > bmr_old_age


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


def test_bmr_male_female():
    m = mifflin_st_jeor_bmr(sex="male", weight_kg=75, height_cm=175, age=28)
    f = mifflin_st_jeor_bmr(sex="female", weight_kg=55, height_cm=162, age=28)
    assert m > f
    assert m > 1400


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
