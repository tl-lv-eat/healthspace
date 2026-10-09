def _balance(client, auth_header) -> int:
    return client.get("/api/points/balance", headers=auth_header).json()["balance"]


def _settle(client, auth_header, day: str):
    return client.post(f"/api/couple-settings/settle?date={day}", headers=auth_header)


def _low_deficit_meal(client, auth_header, day: str) -> None:
    """Breakfast+lunch+dinner so meals are complete; total intake still under BMR."""
    for meal_type, kcal in (("breakfast", 200), ("lunch", 200), ("dinner", 100)):
        client.post(
            "/api/meals",
            headers=auth_header,
            json={
                "date": day,
                "meal_type": meal_type,
                "food_summary": "light",
                "user_kcal": kcal,
            },
        )


def test_daily_settle_water_only(client, auth_header):
    day = "2026-10-08"
    client.post("/api/water", headers=auth_header, json={"date": day, "amount_ml": 2000})
    assert _settle(client, auth_header, day).status_code == 200
    assert _balance(client, auth_header) == 1


def test_daily_settle_water_and_deficit(client, auth_header):
    day = "2026-10-09"
    client.post("/api/water", headers=auth_header, json={"date": day, "amount_ml": 2000})
    _low_deficit_meal(client, auth_header, day)
    assert _settle(client, auth_header, day).status_code == 200
    assert _balance(client, auth_header) == 2


def test_daily_settle_workout_40_adds_two_more(client, auth_header):
    day = "2026-10-10"
    client.post("/api/water", headers=auth_header, json={"date": day, "amount_ml": 2000})
    _low_deficit_meal(client, auth_header, day)
    client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": day,
            "kind": "cardio",
            "cardio_type": "run",
            "duration_min": 40,
        },
    )
    assert _settle(client, auth_header, day).status_code == 200
    assert _balance(client, auth_header) == 4


def test_daily_settle_empty_day(client, auth_header):
    day = "2026-10-11"
    assert _settle(client, auth_header, day).status_code == 200
    assert _balance(client, auth_header) == 0


def test_daily_settle_idempotent_same_day(client, auth_header):
    day = "2026-10-12"
    client.post("/api/water", headers=auth_header, json={"date": day, "amount_ml": 2000})
    _settle(client, auth_header, day)
    bal = _balance(client, auth_header)
    _settle(client, auth_header, day)
    assert _balance(client, auth_header) == bal
