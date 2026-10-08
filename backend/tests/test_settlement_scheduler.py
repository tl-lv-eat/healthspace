from datetime import date, datetime
from zoneinfo import ZoneInfo

from backend.app.services.scheduler import should_run_daily

TZ = ZoneInfo("Asia/Shanghai")


def _at(day: str, hour: int, minute: int = 0) -> datetime:
    d = date.fromisoformat(day)
    return datetime(d.year, d.month, d.day, hour, minute, tzinfo=TZ)


def test_should_run_daily_wrong_hour():
    now = _at("2026-10-08", 10)
    assert should_run_daily(now, settle_hour=0, last_run=None) is False


def test_should_run_daily_at_settle_hour_no_prior_run():
    now = _at("2026-10-08", 0)
    assert should_run_daily(now, settle_hour=0, last_run=None) is True


def test_should_run_daily_already_settled_yesterday():
    now = _at("2026-10-08", 1)
    assert should_run_daily(now, settle_hour=1, last_run=date(2026, 10, 7)) is False


def test_should_run_daily_settle_hour_stale_last_run():
    now = _at("2026-10-08", 2)
    assert should_run_daily(now, settle_hour=2, last_run=date(2026, 10, 5)) is True


def test_water_activity_does_not_grant_live_points(client, auth_header):
    day = "2028-06-01"
    before = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    client.post("/api/water", headers=auth_header, json={"date": day, "amount_ml": 2000})
    after = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert after == before


def test_settle_creates_settlement_run(client, auth_header, db_session):
    from backend.app.models import SettlementRun

    day = "2028-06-02"
    client.post("/api/water", headers=auth_header, json={"date": day, "amount_ml": 2000})
    client.post(f"/api/couple-settings/settle?date={day}", headers=auth_header)
    row = (
        db_session.query(SettlementRun)
        .filter(SettlementRun.run_date == day, SettlementRun.kind == "daily")
        .one()
    )
    assert row.run_date == day
