"""Plan end tier settlement (B +5, A −2, fail −5) via POST /api/couple-settings/settle."""

from __future__ import annotations


def _balance(client, auth_header) -> int:
    return client.get("/api/points/balance", headers=auth_header).json()["balance"]


def _settle(client, auth_header, day: str):
    return client.post(f"/api/couple-settings/settle?date={day}", headers=auth_header)


def _put_plan(client, auth_header, *, start: str, end: str, deficit: int, workout_days: int) -> None:
    r = client.put(
        "/api/week-plans",
        headers=auth_header,
        json={
            "start_date": start,
            "end_date": end,
            "water_target_ml": 2000,
            "weekly_kcal_deficit": deficit,
            "weekly_workout_sessions": workout_days,
            "meal_mode": "any",
            "workout_mode": "any",
        },
    )
    assert r.status_code == 200


def _low_deficit_meal(client, auth_header, day: str) -> None:
    client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": day,
            "meal_type": "lunch",
            "food_summary": "light",
            "user_kcal": 500,
        },
    )


def _workout(client, auth_header, day: str) -> None:
    client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": day,
            "kind": "cardio",
            "cardio_type": "run",
            "duration_min": 15,
        },
    )


def _water(client, auth_header, day: str, ml: int = 2000) -> None:
    client.post("/api/water", headers=auth_header, json={"date": day, "amount_ml": ml})


def _seed_plan_period(
    client,
    auth_header,
    *,
    start: str,
    end: str,
    water_ml_per_day: int | list[int],
) -> None:
    from datetime import date, timedelta

    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    cur = s
    idx = 0
    while cur <= e:
        day = cur.isoformat()
        if isinstance(water_ml_per_day, list):
            ml = water_ml_per_day[idx]
        else:
            ml = water_ml_per_day
        if ml > 0:
            _water(client, auth_header, day, ml)
        _low_deficit_meal(client, auth_header, day)
        _workout(client, auth_header, day)
        cur += timedelta(days=1)
        idx += 1


def test_plan_settle_tier_b_plus_five(client, auth_header):
    start, end, settle = "2026-11-01", "2026-11-03", "2026-11-04"
    _put_plan(client, auth_header, start=start, end=end, deficit=300, workout_days=3)
    _seed_plan_period(client, auth_header, start=start, end=end, water_ml_per_day=2000)

    before = _balance(client, auth_header)
    assert _settle(client, auth_header, settle).status_code == 200
    assert _balance(client, auth_header) - before == 5


def test_plan_settle_tier_a_minus_two(client, auth_header):
    start, end, settle = "2026-12-01", "2026-12-03", "2026-12-04"
    _put_plan(client, auth_header, start=start, end=end, deficit=300, workout_days=3)
    _seed_plan_period(
        client,
        auth_header,
        start=start,
        end=end,
        water_ml_per_day=[2000, 1500, 2000],
    )

    before = _balance(client, auth_header)
    assert _settle(client, auth_header, settle).status_code == 200
    assert _balance(client, auth_header) - before == -2


def test_plan_settle_tier_fail_minus_five(client, auth_header):
    start, end, settle = "2027-01-01", "2027-01-03", "2027-01-04"
    _put_plan(client, auth_header, start=start, end=end, deficit=300, workout_days=3)
    from datetime import date, timedelta

    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    cur = s
    while cur <= e:
        day = cur.isoformat()
        _water(client, auth_header, day)
        _low_deficit_meal(client, auth_header, day)
        if cur == s:
            _workout(client, auth_header, day)
        cur += timedelta(days=1)

    before = _balance(client, auth_header)
    assert _settle(client, auth_header, settle).status_code == 200
    assert _balance(client, auth_header) - before == -5


def test_plan_settle_idempotent(client, auth_header):
    start, end, settle = "2027-02-01", "2027-02-03", "2027-02-04"
    _put_plan(client, auth_header, start=start, end=end, deficit=300, workout_days=3)
    _seed_plan_period(client, auth_header, start=start, end=end, water_ml_per_day=2000)

    before = _balance(client, auth_header)
    _settle(client, auth_header, settle)
    after_first = _balance(client, auth_header)
    assert after_first - before == 5
    _settle(client, auth_header, settle)
    assert _balance(client, auth_header) == after_first
