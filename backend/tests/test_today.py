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
    assert partner["display_name"] == "叶子"
    assert partner["done"]["meal"] is False
    assert partner["done"]["water"] is False
    assert partner["done"]["workout"] is True
    assert partner["water"]["total_ml"] == 500
    assert partner["water"]["target_ml"] == 2000
    assert partner["energy"]["intake_kcal"] == 0
    assert len(partner["meals"]) == 0
    assert len(partner["workouts"]) == 1
    assert "energy" in partner


def test_today_includes_energy_and_water_entries(client, auth_header):
    date = "2026-10-08"
    client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": date,
            "meal_type": "lunch",
            "food_summary": "饭",
            "user_kcal": 400,
        },
    )
    client.post(
        "/api/water",
        headers=auth_header,
        json={"date": date, "amount_ml": 250},
    )
    r = client.get("/api/today", headers=auth_header, params={"date": date})
    assert r.status_code == 200
    me = r.json()["me"]
    assert "energy" in me
    e = me["energy"]
    for k in (
        "intake_kcal",
        "burn_kcal",
        "bmr",
        "surplus_kcal",
        "deficit_contrib",
        "meals_complete",
        "empty",
        "daily_deficit_target",
        "daily_kcal_cap",
        "water_target_ml",
        "period_days",
    ):
        assert k in e
    assert e["intake_kcal"] == 400
    assert e["empty"] is False
    assert e["meals_complete"] is False
    assert e["deficit_contrib"] == 0
    assert e["water_target_ml"] == 2000
    assert "entries" in me["water"]
    assert len(me["water"]["entries"]) == 1
    entry = me["water"]["entries"][0]
    assert entry["amount_ml"] == 250
    assert "id" in entry
    assert "created_at" in entry
    assert "plan" in me


def test_today_requires_auth(client):
    r = client.get("/api/today", params={"date": "2026-10-08"})
    assert r.status_code == 401
