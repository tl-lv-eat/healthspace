def test_redeem_insufficient(client, auth_header):
    rw = client.post(
        "/api/rewards",
        headers=auth_header,
        json={
            "title": "火锅",
            "description": "双人火锅一次",
            "is_private": False,
            "scale_level": 2,
            "cost_note": "约200元",
            "points_price": 100,
        },
    ).json()
    r = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert r.status_code == 400


def test_redeem_ok(client, auth_header, db_session):
    from backend.app.services.points import grant

    grant(db_session, "dragon", 100, "test", "dragon:test:topup")
    rw = client.post(
        "/api/rewards",
        headers=auth_header,
        json={
            "title": "按摩",
            "description": "肩颈按摩",
            "is_private": True,
            "scale_level": 3,
            "cost_note": "私密",
            "points_price": 30,
        },
    ).json()
    listed = client.get("/api/rewards", headers=auth_header).json()
    private_item = next(x for x in listed if x["id"] == rw["id"])
    assert private_item["description"] is None
    r = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert r.status_code == 200
    bal = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal == 70


def test_redeem_cancel_refund(client, auth_header, db_session):
    from backend.app.services.points import grant

    grant(db_session, "dragon", 50, "test", "dragon:test:refund")
    rw = client.post(
        "/api/rewards",
        headers=auth_header,
        json={
            "title": "小奖",
            "description": "x",
            "is_private": False,
            "scale_level": 1,
            "cost_note": "",
            "points_price": 20,
        },
    ).json()
    red = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header).json()
    client.patch(
        f"/api/rewards/redemptions/{red['id']}",
        headers=auth_header,
        json={"status": "cancelled"},
    )
    bal = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal == 50
