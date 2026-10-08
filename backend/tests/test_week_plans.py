def test_week_plan_upsert(client, auth_header):
    r = client.put(
        "/api/week-plans",
        headers=auth_header,
        json={
            "week_start": "2026-10-06",
            "water_target_ml": 2500,
            "meal_mode": "any",
            "workout_mode": "any",
        },
    )
    assert r.status_code == 200
    g = client.get("/api/week-plans", headers=auth_header, params={"week_start": "2026-10-08"})
    assert g.json()["water_target_ml"] == 2500
