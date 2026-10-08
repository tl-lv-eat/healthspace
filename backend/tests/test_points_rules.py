def _fill_daily_three(client, auth_header, day: str) -> None:
    for meal_type in ("breakfast", "lunch", "dinner"):
        client.post(
            "/api/meals",
            headers=auth_header,
            json={
                "date": day,
                "meal_type": meal_type,
                "food_summary": "test",
                "user_kcal": 500,
            },
        )
    client.post(
        "/api/water",
        headers=auth_header,
        json={"date": day, "amount_ml": 2000},
    )
    client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": day,
            "kind": "cardio",
            "cardio_type": "run",
            "duration_min": 30,
        },
    )


def test_daily_all_three_points(client, auth_header):
    day = "2026-10-08"
    _fill_daily_three(client, auth_header, day)
    r = client.post("/api/points/evaluate", headers=auth_header, json={"date": day})
    assert r.status_code == 200
    bal = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal >= 10
    client.post("/api/points/evaluate", headers=auth_header, json={"date": day})
    bal2 = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal2 == bal
