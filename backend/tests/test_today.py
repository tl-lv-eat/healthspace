def test_today_summary_self_detail_and_partner_summary(client, auth_header, leaf_auth_header):
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
        headers=leaf_auth_header,
        json={"date": date, "amount_ml": 500},
    )
    client.post(
        "/api/workouts",
        headers=leaf_auth_header,
        json={"date": date, "kind": "cardio", "cardio_type": "run", "duration_min": 20},
    )

    r = client.get("/api/today", headers=auth_header, params={"date": date})
    assert r.status_code == 200
    data = r.json()
    assert data["date"] == date

    me = data["me"]
    assert me["user_id"] == "dragon"
    assert len(me["meals"]) == 3
    assert me["water"]["total_ml"] == 0
    assert me["water"]["target_ml"] == 2000
    assert me["water"]["done"] is False
    assert me["done"]["meal"] is True
    assert me["done"]["water"] is False
    assert me["done"]["workout"] is False
    assert isinstance(me["workouts"], list)

    partner = data["partner"]
    assert partner["user_id"] == "leaf"
    assert partner["display_name"] == "🍃"
    assert partner["done"]["meal"] is False
    assert partner["done"]["water"] is False
    assert partner["done"]["workout"] is True
    assert partner["water_total_ml"] == 500
    assert partner["water_target_ml"] == 2000
    assert "meals" not in partner


def test_today_requires_auth(client):
    r = client.get("/api/today", params={"date": "2026-10-08"})
    assert r.status_code == 401
