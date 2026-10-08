from datetime import date

from backend.app.models import AiReport


def test_get_report_404(client, auth_header):
    r = client.get(
        "/api/reports",
        headers=auth_header,
        params={"kind": "daily", "period": "2026-01-01"},
    )
    assert r.status_code == 404


def test_generate_report(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.daily_report.call_llm.responses_chat_messages",
        lambda *a, **k: type("R", (), {"text": "## 今日小结\nx"})(),
    )
    r = client.post(
        "/api/reports/generate",
        headers=auth_header,
        json={"kind": "daily", "period": "2026-10-08", "force": False},
    )
    assert r.status_code == 200
    assert "今日小结" in r.json()["content_md"]
