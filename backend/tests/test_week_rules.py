from backend.app.services.week_rules import day_status, effective_rules


def test_default_water_when_no_plan():
    r = effective_rules(None, 2000)
    assert r["water_target_ml"] == 2000
    assert r["meal_rule"]["mode"] == "three_main"


def test_plan_overrides_water():
    r = effective_rules({"water_target_ml": 2500, "meal_mode": "any", "workout_mode": "any"}, 2000)
    assert r["water_target_ml"] == 2500
    assert r["meal_rule"]["mode"] == "any"


def test_day_status_levels():
    rules = effective_rules(None, 2000)
    meals = [{"meal_type": "breakfast"}, {"meal_type": "lunch"}, {"meal_type": "dinner"}]
    s = day_status(meals, 2000, [{"kind": "cardio"}], rules)
    assert s["level"] == "full"
    s2 = day_status(meals, 500, [], rules)
    assert s2["level"] == "partial"
    s3 = day_status([], 0, [], rules)
    assert s3["level"] == "none"
