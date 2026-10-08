def test_couple_settings_defaults_and_patch(client, auth_header):
    g = client.get("/api/couple-settings", headers=auth_header)
    assert g.status_code == 200
    assert g.json()["settle_hour"] == 0
    assert g.json()["points_daily_water"] == 1
    p = client.patch(
        "/api/couple-settings",
        headers=auth_header,
        json={"settle_hour": 1, "points_plan_tier_a": -2},
    )
    assert p.status_code == 200
    assert p.json()["settle_hour"] == 1
