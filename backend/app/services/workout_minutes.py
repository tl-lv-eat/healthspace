"""Sum cardio + strength duration_min for daily points (e.g. ≥40 min)."""


def total_workout_minutes(workouts: list[dict]) -> int:
    total = 0
    for w in workouts:
        kind = w.get("kind")
        if kind not in ("cardio", "strength"):
            continue
        payload = w.get("payload") or {}
        if not isinstance(payload, dict):
            continue
        mins = payload.get("duration_min")
        if mins is None:
            continue
        try:
            total += int(mins)
        except (TypeError, ValueError):
            continue
    return total
