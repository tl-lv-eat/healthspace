def test_chat_stores_two_messages(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.chat_coach.call_llm.responses_chat_messages",
        lambda *a, **k: type("R", (), {"text": "多喝水，继续记录。"})(),
    )
    r = client.post("/api/chat", headers=auth_header, json={"message": "今天有点饿怎么办"})
    assert r.status_code == 200
    assert "水" in r.json()["reply"]
    hist = client.get("/api/chat/history", headers=auth_header).json()
    assert len(hist["messages"]) >= 2


def test_chat_clear_history(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.chat_coach.call_llm.responses_chat_messages",
        lambda *a, **k: type("R", (), {"text": "好的"})(),
    )
    client.post("/api/chat", headers=auth_header, json={"message": "hi"})
    client.delete("/api/chat/history", headers=auth_header)
    hist = client.get("/api/chat/history", headers=auth_header).json()
    assert hist["messages"] == []
