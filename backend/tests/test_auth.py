def test_login_ok(client):
    r = client.post("/api/auth/login", json={"user_id": "dragon", "password": "dragon-pass"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["user"]["display_name"] == "🐉"


def test_login_bad_password(client):
    r = client.post("/api/auth/login", json={"user_id": "dragon", "password": "wrong"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401
