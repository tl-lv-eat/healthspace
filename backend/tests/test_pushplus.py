import json

from backend.app.models import PushBinding
from backend.app.services.pushplus import PushPlusError, run_reminders_now, send_pushplus


def test_send_pushplus_ok(monkeypatch):
    class _Resp:
        status_code = 200

        def json(self):
            return {"code": 200}

        text = "ok"

    monkeypatch.setattr(
        "backend.app.services.pushplus.httpx.post",
        lambda *a, **k: _Resp(),
    )
    send_pushplus("tok", "标题", "内容")


def test_send_pushplus_api_error(monkeypatch):
    class _Resp:
        status_code = 200

        def json(self):
            return {"code": 500, "msg": "bad token"}

        text = "bad"

    monkeypatch.setattr(
        "backend.app.services.pushplus.httpx.post",
        lambda *a, **k: _Resp(),
    )
    try:
        send_pushplus("tok", "t", "c")
        assert False
    except PushPlusError:
        pass


def test_reminder_skips_when_all_done(db_session, monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.pushplus.send_pushplus",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not send")),
    )
    from datetime import date

    today = date.today().isoformat()
    db_session.add(
        PushBinding(
            user_id="dragon",
            token="x",
            enabled=True,
            remind_hours_json=json.dumps([12]),
        )
    )
    db_session.commit()

    from backend.app.models import Meal, WaterEntry, Workout
    from backend.app.models import User

    user = db_session.get(User, "dragon")
    assert user is not None
    db_session.add(
        Meal(
            user_id="dragon",
            date=today,
            meal_type="breakfast",
            food_summary="粥",
            user_kcal=300,
        )
    )
    db_session.add(
        Meal(
            user_id="dragon",
            date=today,
            meal_type="lunch",
            food_summary="面",
            user_kcal=500,
        )
    )
    db_session.add(
        Meal(
            user_id="dragon",
            date=today,
            meal_type="dinner",
            food_summary="菜",
            user_kcal=400,
        )
    )
    db_session.add(WaterEntry(user_id="dragon", date=today, amount_ml=2500))
    db_session.add(
        Workout(
            user_id="dragon",
            date=today,
            kind="cardio",
            payload=json.dumps({"duration_min": 30, "cardio_type": "run"}),
        )
    )
    db_session.commit()

    run_reminders_now(db_session, hour=12)
