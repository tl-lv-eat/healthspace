def test_create_and_trend(client, auth_header):
    r = client.post(
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
            "note": "开工",
        },
    )
    assert r.status_code == 200
    assert r.json()["bmi"] == 22.9
    t = client.get("/api/body/trend", headers=auth_header, params={"user_ids": "dragon,leaf"})
    assert t.status_code == 200
    assert any(s["user_id"] == "dragon" for s in t.json()["series"])
