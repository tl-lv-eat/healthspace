def test_journal_filter_leaf(client, auth_header):
    r = client.get(
        "/api/journal",
        headers=auth_header,
        params={"from": "2026-10-01", "to": "2026-10-31", "user_id": "leaf"},
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert all(u["user_id"] == "leaf" for u in item["users"])
