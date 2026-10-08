def test_week_plan_upsert(client, auth_header):
    r = client.put(
        "/api/week-plans",
        headers=auth_header,
        json={
            "start_date": "2026-10-06",
            "end_date": "2026-10-12",
            "week_start": "2026-10-06",
            "water_target_ml": 2500,
            "weekly_kcal_deficit": 4200,
            "weekly_workout_sessions": 3,
            "target_weight_kg": 70.5,
            "meal_mode": "any",
            "workout_mode": "any",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["start_date"] == "2026-10-06"
    assert body["end_date"] == "2026-10-12"
    assert body["period_days"] == 7

    g = client.get("/api/week-plans", headers=auth_header, params={"on": "2026-10-08"})
    got = g.json()
    assert got["water_target_ml"] == 2500
    assert got["weekly_kcal_deficit"] == 4200
    assert got["weekly_workout_sessions"] == 3
    assert got["target_weight_kg"] == 70.5
    assert got["end_date"] == "2026-10-12"


def test_week_plan_custom_range_and_list(client, auth_header):
    r = client.put(
        "/api/week-plans",
        headers=auth_header,
        json={
            "start_date": "2026-10-01",
            "end_date": "2026-10-14",
            "water_target_ml": 2200,
            "weekly_kcal_deficit": 7000,
            "weekly_workout_sessions": 5,
            "meal_mode": "three_main",
            "workout_mode": "any",
        },
    )
    assert r.status_code == 200
    assert r.json()["period_days"] == 14

    g = client.get("/api/week-plans", headers=auth_header, params={"on": "2026-10-10"})
    assert g.json()["water_target_ml"] == 2200

    outside = client.get("/api/week-plans", headers=auth_header, params={"on": "2026-11-01"})
    assert outside.status_code == 200
    assert outside.json().get("id") is None or outside.json()["start_date"] != "2026-10-01"

    listed = client.get("/api/week-plans", headers=auth_header, params={"list": True})
    assert listed.status_code == 200
    assert isinstance(listed.json(), list)
    assert any(p["start_date"] == "2026-10-01" for p in listed.json())


def test_create_plan_for_partner(client, auth_header):
    # auth_header is dragon
    r = client.put(
        "/api/week-plans",
        headers=auth_header,
        json={
            "target_user_id": "leaf",
            "start_date": "2026-10-01",
            "end_date": "2026-10-14",
            "title": "叶子冲刺",
            "note": "少油",
            "daily_kcal_cap": 1600,
            "water_target_ml": 2200,
            "weekly_kcal_deficit": 7000,
            "weekly_workout_sessions": 4,
            "meal_mode": "three_main",
            "workout_mode": "any",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "leaf"
    assert body["title"] == "叶子冲刺"
    assert body["daily_kcal_cap"] == 1600

    listed = client.get(
        "/api/week-plans",
        headers=auth_header,
        params={"list": True, "month": "2026-10"},
    )
    assert listed.status_code == 200
    assert any(p["user_id"] == "leaf" and p["title"] == "叶子冲刺" for p in listed.json())

    on = client.get("/api/week-plans", headers=auth_header, params={"on": "2026-10-05", "user_id": "leaf"})
    assert on.json()["water_target_ml"] == 2200


def test_put_plan_by_id_rejects_wrong_target_user(client, leaf_auth_header):
    created = client.put(
        "/api/week-plans",
        headers=leaf_auth_header,
        json={
            "start_date": "2026-08-04",
            "end_date": "2026-08-10",
            "water_target_ml": 2100,
            "weekly_kcal_deficit": 3500,
            "weekly_workout_sessions": 3,
            "meal_mode": "three_main",
            "workout_mode": "any",
        },
    )
    assert created.status_code == 200
    plan_id = created.json()["id"]
    assert created.json()["user_id"] == "leaf"

    hijack = client.put(
        "/api/week-plans",
        headers=leaf_auth_header,
        json={
            "id": plan_id,
            "target_user_id": "dragon",
            "start_date": "2026-08-04",
            "end_date": "2026-08-10",
            "water_target_ml": 9999,
            "weekly_kcal_deficit": 3500,
            "weekly_workout_sessions": 3,
            "meal_mode": "three_main",
            "workout_mode": "any",
        },
    )
    assert hijack.status_code == 404


def test_week_plan_delete(client, auth_header):
    r = client.put(
        "/api/week-plans",
        headers=auth_header,
        json={
            "start_date": "2026-09-01",
            "end_date": "2026-09-07",
            "water_target_ml": 2000,
            "weekly_kcal_deficit": 3000,
            "weekly_workout_sessions": 2,
            "meal_mode": "three_main",
            "workout_mode": "any",
        },
    )
    assert r.status_code == 200
    pid = r.json()["id"]
    assert pid is not None
    d = client.delete(f"/api/week-plans/{pid}", headers=auth_header)
    assert d.status_code == 204
    g = client.get("/api/week-plans", headers=auth_header, params={"on": "2026-09-03"})
    assert g.json().get("id") is None
