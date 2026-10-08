def _reward_payload(**overrides):
    base = {
        "title": "火锅",
        "description": "双人火锅一次",
        "is_private": False,
        "scale_level": 2,
        "cost_note": "约200元",
        "points_price": 100,
        "category": "food",
    }
    base.update(overrides)
    return base


def _create_reward(client, headers, **overrides):
    r = client.post("/api/rewards", headers=headers, json=_reward_payload(**overrides))
    assert r.status_code == 200, r.text
    return r.json()


def _approve(client, partner_header, reward_id: int):
    r = client.post(f"/api/rewards/{reward_id}/approve", headers=partner_header)
    assert r.status_code == 200, r.text
    return r.json()


def test_reward_needs_partner_approve_before_redeem(
    client, auth_header, partner_header, db_session
):
    from backend.app.services.points import grant

    rw = _create_reward(client, auth_header)
    assert rw["status"] == "pending_review"

    r = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert r.status_code == 400

    listed = _approve(client, partner_header, rw["id"])
    assert listed["status"] == "listed"

    grant(db_session, "dragon", 100, "test", "dragon:test:approve-flow")
    red = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert red.status_code == 200
    assert red.json()["status"] == "pending"

    fulfilled = client.patch(
        f"/api/rewards/redemptions/{red.json()['id']}",
        headers=auth_header,
        json={"status": "fulfilled"},
    )
    assert fulfilled.status_code == 200
    assert fulfilled.json()["status"] == "fulfilled"


def test_reward_reject_resubmit_and_list_scopes(client, auth_header, partner_header):
    rw = _create_reward(client, auth_header, title="按摩", category="intimacy")
    rej = client.post(
        f"/api/rewards/{rw['id']}/reject",
        headers=partner_header,
        json={"reason": "太贵了"},
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"
    assert rej.json()["reject_reason"] == "太贵了"

    mall = client.get("/api/rewards", headers=auth_header).json()
    assert not any(x["id"] == rw["id"] for x in mall)

    mine = client.get("/api/rewards", headers=auth_header, params={"scope": "mine"}).json()
    assert any(x["id"] == rw["id"] and x["status"] == "rejected" for x in mine)

    pending_for_partner = client.get(
        "/api/rewards", headers=partner_header, params={"scope": "pending_review_for_me"}
    ).json()
    assert not any(x["id"] == rw["id"] for x in pending_for_partner)

    resub = client.post(f"/api/rewards/{rw['id']}/resubmit", headers=auth_header)
    assert resub.status_code == 200
    assert resub.json()["status"] == "pending_review"

    pending_for_partner = client.get(
        "/api/rewards", headers=partner_header, params={"scope": "pending_review_for_me"}
    ).json()
    assert any(x["id"] == rw["id"] for x in pending_for_partner)


def test_reward_category_required_and_filter(client, auth_header, partner_header):
    bad = client.post(
        "/api/rewards",
        headers=auth_header,
        json={
            "title": "x",
            "points_price": 10,
            "category": "not-a-category",
        },
    )
    assert bad.status_code == 422

    missing = client.post(
        "/api/rewards",
        headers=auth_header,
        json={"title": "x", "points_price": 10},
    )
    assert missing.status_code == 422

    food = _create_reward(client, auth_header, title="蛋糕", category="food")
    fun = _create_reward(client, auth_header, title="电影", category="fun")
    _approve(client, partner_header, food["id"])
    _approve(client, partner_header, fun["id"])

    only_food = client.get(
        "/api/rewards", headers=auth_header, params={"category": "food"}
    ).json()
    ids = {x["id"] for x in only_food}
    assert food["id"] in ids
    assert fun["id"] not in ids


def test_redeem_insufficient(client, auth_header, partner_header):
    rw = _create_reward(client, auth_header)
    _approve(client, partner_header, rw["id"])
    r = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert r.status_code == 400


def test_redeem_ok(client, auth_header, partner_header, db_session):
    from backend.app.services.points import grant

    grant(db_session, "dragon", 100, "test", "dragon:test:topup")
    rw = _create_reward(
        client,
        auth_header,
        title="按摩",
        description="肩颈按摩",
        is_private=True,
        scale_level=3,
        cost_note="私密",
        points_price=30,
        category="intimacy",
    )
    _approve(client, partner_header, rw["id"])
    listed = client.get("/api/rewards", headers=auth_header).json()
    private_item = next(x for x in listed if x["id"] == rw["id"])
    assert private_item["description"] is None
    r = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert r.status_code == 200
    bal = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal == 70


def test_redeem_cancel_refund(client, auth_header, partner_header, db_session):
    from backend.app.services.points import grant

    grant(db_session, "dragon", 50, "test", "dragon:test:refund")
    rw = _create_reward(
        client,
        auth_header,
        title="小奖",
        description="x",
        is_private=False,
        scale_level=1,
        cost_note="",
        points_price=20,
        category="fun",
    )
    _approve(client, partner_header, rw["id"])
    red = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header).json()
    client.patch(
        f"/api/rewards/redemptions/{red['id']}",
        headers=auth_header,
        json={"status": "cancelled"},
    )
    bal = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal == 50
