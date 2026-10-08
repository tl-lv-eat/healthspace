from backend.app.services.points import get_balance, grant


def test_grant_idempotent(db_session):
    ok1, bal1 = grant(db_session, "dragon", 10, "daily_all_three", "dragon:2026-10-08:daily_all_three")
    ok2, bal2 = grant(db_session, "dragon", 10, "daily_all_three", "dragon:2026-10-08:daily_all_three")
    assert ok1 is True and bal1 == 10
    assert ok2 is False and bal2 == 10
    assert get_balance(db_session, "dragon") == 10


def test_grant_negative_balance(db_session):
    grant(db_session, "dragon", 100, "test", "dragon:test:100")
    ok, bal = grant(db_session, "dragon", -30, "redeem", "dragon:redeem:1")
    assert ok is True and bal == 70
