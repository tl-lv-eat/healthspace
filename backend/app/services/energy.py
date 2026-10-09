"""BMR / workout burn / daily calorie surplus helpers for calendar ↔ week plan."""

from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from backend.app.models import BodyMetric, User


DEFAULT_PROFILES = {
    "dragon": {"sex": "male", "age": 28, "weight_kg": 75.0, "height_cm": 175.0, "bmr_kcal": 1700},
    "leaf": {"sex": "female", "age": 28, "weight_kg": 55.0, "height_cm": 162.0, "bmr_kcal": 1400},
}


def resolve_body_profile(user: User, db: Session) -> dict:
    """Weight/height/sex for achievements (BMI etc.); BMR is separate user field."""
    defaults = DEFAULT_PROFILES.get(user.id, DEFAULT_PROFILES["dragon"])
    sex = getattr(user, "sex", None) or defaults["sex"]
    age = int(getattr(user, "age", None) or defaults["age"])
    weight = float(defaults["weight_kg"])
    height = float(defaults["height_cm"])
    latest = (
        db.query(BodyMetric)
        .filter(BodyMetric.user_id == user.id)
        .order_by(BodyMetric.recorded_on.desc(), BodyMetric.id.desc())
        .first()
    )
    if latest is not None:
        if latest.weight_kg is not None and float(latest.weight_kg) > 0:
            weight = float(latest.weight_kg)
        if latest.height_cm is not None and float(latest.height_cm) > 0:
            height = float(latest.height_cm)
    return {"sex": sex, "age": age, "weight_kg": weight, "height_cm": height}


def user_bmr(user: User, db: Session | None = None) -> int:
    """User-entered daily BMR (kcal). Falls back to persona default if unset."""
    del db  # kept for call-site compatibility
    stored = getattr(user, "bmr_kcal", None)
    if stored is not None and int(stored) > 0:
        return int(stored)
    defaults = DEFAULT_PROFILES.get(user.id, DEFAULT_PROFILES["dragon"])
    return int(defaults["bmr_kcal"])


def estimate_workout_burn_kcal(workouts: list[dict]) -> int:
    """Rough burn from logged workouts (no heart-rate)."""
    total = 0
    for w in workouts:
        kind = w.get("kind")
        payload = w.get("payload") or {}
        if isinstance(payload, str):
            continue
        if kind == "cardio":
            mins = int(payload.get("duration_min") or 0)
            # ~7 kcal/min moderate cardio
            total += max(0, mins) * 7
        elif kind == "strength":
            sets = payload.get("sets") or []
            reps = sum(int(s.get("reps") or 0) for s in sets if isinstance(s, dict))
            # ~0.5 kcal/rep floor 40 per session
            total += max(40, int(reps * 0.5)) if sets else 40
    return int(total)


def daily_energy_snapshot(
    *,
    intake_kcal: int,
    workouts: list[dict],
    bmr: int,
    water_ml: int,
    water_target_ml: int,
    weekly_kcal_deficit: int,
    period_days: int = 7,
    meals_complete: bool = True,
) -> dict:
    """
    Linkage: period deficit is split evenly across period_days as a soft daily target.

    calorie_exceeded ⇔ intake - burn - BMR > 0  (net surplus)
    Deficit / calorie_ok only after meals_complete (plan meal_mode, default 早午晚).
    water_ok ⇔ water_ml >= water_target_ml

    Day level (calendar color):
      full    = water_ok and not calorie_exceeded (and has some intake or water log)
      partial = exactly one of water_ok / calorie_ok
      none    = neither, or completely empty day
    """
    burn = estimate_workout_burn_kcal(workouts)
    surplus = int(intake_kcal) - burn - int(bmr)
    calorie_exceeded = surplus > 0
    water_ok = int(water_ml) >= int(water_target_ml)
    days = max(1, int(period_days or 7))
    daily_deficit_target = max(0, int(weekly_kcal_deficit or 0) // days)
    empty = int(intake_kcal) == 0 and int(water_ml) == 0 and burn == 0
    complete = bool(meals_complete) and not empty
    # Incomplete meals: do not credit BMR-only or partial-day intake as plan deficit.
    calorie_ok = complete and not calorie_exceeded
    deficit_contrib = max(0, -surplus) if complete else 0

    if empty:
        level = "none"
    elif water_ok and calorie_ok:
        level = "full"
    elif water_ok or calorie_ok:
        level = "partial"
    else:
        level = "none"

    return {
        "intake_kcal": int(intake_kcal),
        "burn_kcal": burn,
        "bmr": int(bmr),
        "surplus_kcal": surplus,
        "calorie_exceeded": calorie_exceeded,
        "calorie_ok": calorie_ok,
        "water_ml": int(water_ml),
        "water_target_ml": int(water_target_ml),
        "water_ok": water_ok,
        "daily_deficit_target": daily_deficit_target,
        "deficit_contrib": deficit_contrib,
        "meals_complete": complete,
        "had_workout": burn > 0 or any(True for _ in workouts),
        "level": level,
        # legacy flags kept for older UI/tests
        "meal": int(intake_kcal) > 0,
        "water": water_ok,
        "workout": burn > 0 or len(workouts) > 0,
    }


def monday_iso(day: str) -> str:
    d = date.fromisoformat(day)
    return (d.fromordinal(d.toordinal() - d.weekday())).isoformat()
