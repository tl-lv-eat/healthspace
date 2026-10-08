from datetime import date

from backend.app.models import AiReport
from backend.app.services.daily_report import ReportError, generate_daily_report


def test_skip_overwrite_without_force(db_session, monkeypatch):
    day = date(2026, 10, 8)
    db_session.add(
        AiReport(
            user_id="dragon",
            kind="daily",
            period_key="2026-10-08",
            content_md="已有报告",
        )
    )
    db_session.commit()

    calls: list[int] = []
    monkeypatch.setattr(
        "backend.app.services.daily_report.call_llm.responses_chat_messages",
        lambda *a, **k: calls.append(1),
    )

    row = generate_daily_report(db_session, "dragon", day, force=False)
    assert row.content_md == "已有报告"
    assert calls == []


def test_llm_failure_does_not_overwrite(db_session, monkeypatch):
    day = date(2026, 10, 8)
    db_session.add(
        AiReport(
            user_id="dragon",
            kind="daily",
            period_key="2026-10-08",
            content_md="保留",
        )
    )
    db_session.commit()

    def _boom(*a, **k):
        raise RuntimeError("llm down")

    monkeypatch.setattr("backend.app.services.daily_report.call_llm.responses_chat_messages", _boom)

    try:
        generate_daily_report(db_session, "dragon", day, force=True)
        assert False, "expected ReportError"
    except ReportError:
        pass

    again = (
        db_session.query(AiReport)
        .filter(AiReport.user_id == "dragon", AiReport.period_key == "2026-10-08")
        .one()
    )
    assert again.content_md == "保留"


def test_generate_creates_when_missing(db_session, monkeypatch):
    class _R:
        text = "## 今日小结\n好\n## 本周趋势\n好\n## 明日建议\n喝水"

    monkeypatch.setattr(
        "backend.app.services.daily_report.call_llm.responses_chat_messages",
        lambda *a, **k: _R(),
    )
    row = generate_daily_report(db_session, "dragon", date(2026, 10, 8), force=False)
    assert "今日小结" in row.content_md
