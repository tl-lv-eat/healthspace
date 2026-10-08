from __future__ import annotations

MAIN = {"breakfast", "lunch", "dinner"}


def meal_done(meals: list[dict], rule: dict | None = None) -> bool:
    rule = rule or {"mode": "three_main"}
    mode = rule.get("mode", "three_main")
    types = {m.get("meal_type") for m in meals}
    if mode == "any":
        return len(meals) >= 1
    return MAIN.issubset(types)


def water_done(total_ml: int, target_ml: int) -> bool:
    return int(total_ml) >= int(target_ml)


def workout_done(workouts: list[dict], rule: dict | None = None) -> bool:
    rule = rule or {"mode": "any"}
    if rule.get("mode", "any") == "any":
        return len(workouts) >= 1
    return len(workouts) >= 1
