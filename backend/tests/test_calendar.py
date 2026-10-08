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
    client.post(
        "/api/water",
        headers=auth_header,
        json={"date": date, "amount_ml": 2000},
    )
    r = client.get("/api/calendar", headers=auth_header, params={"year": 2026, "month": 10})
    assert r.status_code == 200
    body = r.json()
    day = next(d for d in body["days"] if d["date"] == date)
    assert "level" in day["dragon"]
    assert "water_ok" in day["dragon"]
    assert "calorie_ok" in day["dragon"]
    assert "my_week_progress" in body


def test_calendar_day_dual_sections(client, auth_header):
    r = client.get("/api/calendar/day", headers=auth_header, params={"date": "2026-10-08"})
    assert r.status_code == 200
    body = r.json()
    assert "sections" in body
    for key in ("dragon", "leaf"):
        s = body["sections"][key]
        assert "meals" in s and "workouts" in s
        assert "entries" in s["water"]
        assert "energy" in s
