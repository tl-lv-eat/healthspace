def test_calendar_month_levels(client, auth_header):
    date = "2026-10-08"
    for meal_type in ("breakfast", "lunch", "dinner"):
        client.post(
            "/api/meals",
            headers=auth_header,
            json={
                "date": date,
                "meal_type": meal_type,
                "food_summary": "test",
                "user_kcal": 100,
            },
        )
    r = client.get("/api/calendar", headers=auth_header, params={"year": 2026, "month": 10})
    assert r.status_code == 200
    day = next(d for d in r.json()["days"] if d["date"] == date)
    assert "level" in day["dragon"]
    assert "level" in day["leaf"]
