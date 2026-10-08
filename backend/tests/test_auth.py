def test_login_ok(client):
    r = client.post("/api/auth/login", json={"user_id": "dragon", "password": "dragon-pass"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["user"]["display_name"] == "龙龙"


def test_login_bad_password(client):
    r = client.post("/api/auth/login", json={"user_id": "dragon", "password": "wrong"})
    assert r.status_code == 401


def test_select_ok(client):
    r = client.post("/api/auth/select", json={"user_id": "leaf"})
    assert r.status_code == 200
    body = r.json()
    assert body["user"]["id"] == "leaf"
    assert "access_token" in body


def test_select_unknown(client):
    r = client.post("/api/auth/select", json={"user_id": "nobody"})
    assert r.status_code == 404


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401


def test_update_display_name(client, auth_header):
    r = client.patch("/api/auth/me", headers=auth_header, json={"display_name": "小龙"})
    assert r.status_code == 200
    assert r.json()["display_name"] == "小龙"
    personas = client.get("/api/auth/personas").json()
    dragon = next(p for p in personas if p["id"] == "dragon")
    assert dragon["display_name"] == "小龙"


def test_update_display_name_rejects_blank(client, auth_header):
    r = client.patch("/api/auth/me", headers=auth_header, json={"display_name": "  "})
    assert r.status_code == 400


def test_patch_me_sex_age(client, auth_header):
    r = client.patch(
        "/api/auth/me",
        headers=auth_header,
        json={"display_name": "龙龙", "sex": "male", "age": 30},
    )
    assert r.status_code == 200
    assert r.json()["sex"] == "male"
    assert r.json()["age"] == 30
