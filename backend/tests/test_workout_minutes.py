def test_sum_minutes_cardio_and_strength():
    from backend.app.services.workout_minutes import total_workout_minutes

    assert total_workout_minutes(
        [
            {"kind": "cardio", "payload": {"duration_min": 25}},
            {"kind": "strength", "payload": {"duration_min": 20, "sets": []}},
        ]
    ) == 45
