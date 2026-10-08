from backend.app.services.context_summary import build_user_day_blob, build_user_range_summary


def test_day_blob_contains_flags():
    text = build_user_day_blob(
        "2026-10-08",
        meals=[{"meal_type": "lunch", "user_kcal": 500, "food_summary": "面"}],
        water={"total_ml": 1200, "target_ml": 2000},
        workouts=[{"kind": "cardio", "payload": {"duration_min": 30, "cardio_type": "run"}}],
        done={"meal": False, "water": False, "workout": True},
    )
    assert "2026-10-08" in text
    assert "1200" in text
    assert "workout=True" in text or "运动完成" in text


def test_range_summary_joins_days():
    days = [
        {
            "date": "2026-10-07",
            "meals": [],
            "water": {"total_ml": 0, "target_ml": 2000},
            "workouts": [],
            "done": {"meal": False, "water": False, "workout": False},
        },
        {
            "date": "2026-10-08",
            "meals": [{"meal_type": "breakfast", "user_kcal": 300, "food_summary": "粥"}],
            "water": {"total_ml": 500, "target_ml": 2000},
            "workouts": [],
            "done": {"meal": True, "water": False, "workout": False},
        },
    ]
    text = build_user_range_summary(days)
    assert "2026-10-07" in text
    assert "2026-10-08" in text
    assert "300" in text
