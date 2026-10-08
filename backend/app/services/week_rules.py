from __future__ import annotations

import json

from backend.app.completion import meal_done, water_done, workout_done


def effective_rules(plan: dict | None, user_default_water_ml: int) -> dict:
    plan = plan or {}
    meal_mode = plan.get("meal_mode") or "three_main"
    workout_mode = plan.get("workout_mode") or "any"
    water = plan.get("water_target_ml")
    if water is None:
        water = user_default_water_ml
    workout_rule: dict = {"mode": workout_mode}
    if workout_mode == "cardio_min":
        workout_rule["minutes"] = int(plan.get("workout_cardio_min") or 30)
    if workout_mode == "strength_sets":
        workout_rule["sets"] = int(plan.get("workout_strength_sets") or 6)
    period_days = int(plan.get("period_days") or 7)
    return {
        "water_target_ml": int(water),
        "daily_kcal_cap": plan.get("daily_kcal_cap"),
        "weekly_kcal_deficit": int(plan.get("weekly_kcal_deficit") or 3500),
        "weekly_workout_sessions": int(plan.get("weekly_workout_sessions") or 4),
        "target_weight_kg": plan.get("target_weight_kg"),
        "period_days": max(1, period_days),
        "start_date": plan.get("start_date"),
        "end_date": plan.get("end_date"),
        "meal_rule": {"mode": meal_mode},
        "workout_rule": workout_rule,
    }


def _workout_done_extended(workouts: list, rule: dict) -> bool:
    mode = rule.get("mode", "any")
    parsed = []
    for x in workouts:
        if not isinstance(x, dict):
            continue
        p = x.get("payload") or {}
        if isinstance(p, str):
            p = json.loads(p)
        parsed.append({"kind": x.get("kind"), **p})
    if mode == "any":
        return workout_done(parsed, {"mode": "any"})
    if mode == "cardio_min":
        mins = sum(int(i.get("duration_min") or 0) for i in parsed if i.get("kind") == "cardio")
        return mins >= int(rule.get("minutes") or 30)
    if mode == "strength_sets":
        sets = 0
        for i in parsed:
            if i.get("kind") != "strength":
                continue
            sets += len(i.get("sets") or [])
        return sets >= int(rule.get("sets") or 6)
    return len(parsed) >= 1


def day_status(meals: list, water_total: int, workouts: list, rules: dict) -> dict:
    m = meal_done(meals, rules["meal_rule"])
    w = water_done(water_total, rules["water_target_ml"])
    wo = _workout_done_extended(workouts, rules["workout_rule"])
    n = sum([m, w, wo])
    level = "full" if n == 3 else ("partial" if n >= 1 else "none")
    return {"meal": m, "water": w, "workout": wo, "level": level}
