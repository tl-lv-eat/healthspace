def test_create_weight_goal_and_refresh(client, auth_header):
    client.post(
        "/api/body",
        headers=auth_header,
        json={
            "recorded_on": "2026-10-01",
            "weight_kg": 70,
            "height_cm": 175,
            "waist_cm": 80,
            "body_fat_pct": 18,
            "chest_cm": 95,
            "hip_cm": 96,
            "note": "",
        },
    )
    g = client.post(
        "/api/goals",
        headers=auth_header,
        json={
            "kind": "short",
            "title": "两周到68",
            "metric": "weight_kg",
            "target_value": 68,
            "unit": "kg",
            "start_date": "2026-10-01",
            "end_date": "2026-10-15",
        },
    ).json()
    client.post(
        "/api/body",
        headers=auth_header,
        json={
            "recorded_on": "2026-10-08",
            "weight_kg": 68,
            "height_cm": 175,
            "waist_cm": 79,
            "body_fat_pct": 17,
            "chest_cm": 95,
            "hip_cm": 95,
            "note": "",
        },
    )
    r = client.post(f"/api/goals/{g['id']}/refresh", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    assert data["current_value"] == 68
    assert data["status"] == "done"


def test_goals_scope_all(client, auth_header, leaf_auth_header):
    client.post(
        "/api/goals",
        headers=auth_header,
        json={
            "kind": "long",
            "title": "dragon goal",
            "metric": "custom",
            "target_value": 10,
            "unit": "",
            "start_date": "2026-10-01",
        },
    )
    all_goals = client.get("/api/goals?scope=all", headers=leaf_auth_header).json()
    assert any(g["title"] == "dragon goal" for g in all_goals)
