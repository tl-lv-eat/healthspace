def test_water_add_and_total(client, auth_header):
    client.post("/api/water", headers=auth_header, json={"date": "2026-10-08", "amount_ml": 250})
    client.post("/api/water", headers=auth_header, json={"date": "2026-10-08", "amount_ml": 500})
    r = client.get("/api/water", headers=auth_header, params={"date": "2026-10-08"})
    assert r.status_code == 200
    data = r.json()
    assert data["total_ml"] == 750
    assert data["target_ml"] == 2000
    assert len(data["entries"]) == 2


def test_water_patch_and_delete(client, auth_header):
    created = client.post(
        "/api/water",
        headers=auth_header,
        json={"date": "2026-10-08", "amount_ml": 300},
    ).json()
    client.patch(
        f"/api/water/{created['id']}",
        headers=auth_header,
        json={"amount_ml": 400},
    )
    r = client.get("/api/water", headers=auth_header, params={"date": "2026-10-08"})
    assert r.json()["total_ml"] == 400

    client.delete(f"/api/water/{created['id']}", headers=auth_header)
    r = client.get("/api/water", headers=auth_header, params={"date": "2026-10-08"})
    assert r.json()["total_ml"] == 0
    assert r.json()["entries"] == []


def test_cannot_patch_or_delete_other_users_water(client, auth_header, leaf_auth_header):
    created = client.post(
        "/api/water",
        headers=auth_header,
        json={"date": "2026-10-08", "amount_ml": 250},
    ).json()
    patch_r = client.patch(
        f"/api/water/{created['id']}",
        headers=leaf_auth_header,
        json={"amount_ml": 999},
    )
    assert patch_r.status_code == 404
    delete_r = client.delete(f"/api/water/{created['id']}", headers=leaf_auth_header)
    assert delete_r.status_code == 404


def test_list_water_only_current_user(client, auth_header, leaf_auth_header):
    client.post("/api/water", headers=auth_header, json={"date": "2026-10-08", "amount_ml": 100})
    client.post("/api/water", headers=leaf_auth_header, json={"date": "2026-10-08", "amount_ml": 200})
    dragon = client.get("/api/water", headers=auth_header, params={"date": "2026-10-08"}).json()
    assert dragon["total_ml"] == 100
    assert len(dragon["entries"]) == 1
