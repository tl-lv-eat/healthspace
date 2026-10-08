from backend.app.completion import meal_done, water_done, workout_done


def test_meal_done_requires_three_main_meals():
    meals = [
        {"meal_type": "breakfast"},
        {"meal_type": "lunch"},
    ]
    assert meal_done(meals, {"mode": "three_main"}) is False
    meals.append({"meal_type": "dinner"})
    assert meal_done(meals, {"mode": "three_main"}) is True


def test_water_done():
    assert water_done(1500, 2000) is False
    assert water_done(2000, 2000) is True


def test_workout_done_any():
    assert workout_done([], {"mode": "any"}) is False
    assert workout_done([{"kind": "cardio"}], {"mode": "any"}) is True
