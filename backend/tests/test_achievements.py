from __future__ import annotations

import json

from backend.app.models import Achievement, BodyMetric, User, UserAchievement, Workout
from backend.app.services.achievement_eval import eval_workout_sessions, eval_workout_minutes_total
from backend.app.services.points import get_balance


def _seed_workouts(db_session, user_id: str, n: int) -> None:
    for i in range(n):
        db_session.add(
            Workout(
                user_id=user_id,
                date=f"2026-01-{i + 1:02d}",
                kind="cardio",
                payload=json.dumps({"duration_min": 20}),
            )
        )
    db_session.commit()


def test_eval_workout_metrics(db_session):
    user = db_session.get(User, "dragon")
    _seed_workouts(db_session, "dragon", 3)
    assert eval_workout_sessions(user, db_session) == 3.0
    assert eval_workout_minutes_total(user, db_session) == 60.0


def test_mine_lists_and_claim_idempotent(client, auth_header, db_session):
    _seed_workouts(db_session, "dragon", 5)
    r = client.get("/api/achievements/mine", headers=auth_header)
    assert r.status_code == 200
    data = r.json()
    claimable = data["claimable"]
    workout_ach = next(x for x in claimable if x["achievement"]["slug"] == "workouts_5")
    ach_id = workout_ach["achievement"]["id"]
    c1 = client.post(f"/api/achievements/{ach_id}/claim", headers=auth_header)
    assert c1.status_code == 200
    assert c1.json()["status"] == "claimed"
    assert get_balance(db_session, "dragon") == 10
    c2 = client.post(f"/api/achievements/{ach_id}/claim", headers=auth_header)
    assert c2.status_code == 200
    assert c2.json()["status"] == "claimed"
    assert get_balance(db_session, "dragon") == 10
    assert db_session.query(UserAchievement).filter_by(user_id="dragon", achievement_id=ach_id).count() == 1


def test_claim_rejects_incomplete(client, auth_header, db_session):
    ach = db_session.query(Achievement).filter(Achievement.slug == "workouts_5").one()
    r = client.post(f"/api/achievements/{ach.id}/claim", headers=auth_header)
    assert r.status_code == 400


def test_persona_bmi_claim(client, auth_header, db_session):
    db_session.add(
        BodyMetric(
            user_id="dragon",
            recorded_on="2026-10-01",
            weight_kg=70.0,
            height_cm=175.0,
            body_fat_pct=18.0,
        )
    )
    db_session.commit()
    r = client.get("/api/achievements/mine", headers=auth_header)
    bmi_item = next(
        x
        for x in r.json()["claimable"]
        if x["achievement"]["slug"] == "bmi_healthy"
    )
    cid = bmi_item["achievement"]["id"]
    claim = client.post(f"/api/achievements/{cid}/claim", headers=auth_header)
    assert claim.status_code == 200
    assert get_balance(db_session, "dragon") == 25


def test_catalog_crud(client, auth_header, partner_header):
    create = client.post(
        "/api/achievements",
        headers=partner_header,
        json={
            "slug": "custom_test",
            "title": "测试成就",
            "metric": "workout_sessions",
            "target_value": 1,
            "points_reward": 5,
        },
    )
    assert create.status_code == 201
    ach_id = create.json()["id"]
    patch = client.patch(
        f"/api/achievements/{ach_id}",
        headers=auth_header,
        json={"title": "测试成就改"},
    )
    assert patch.status_code == 200
    assert patch.json()["title"] == "测试成就改"
    delete = client.delete(f"/api/achievements/{ach_id}", headers=partner_header)
    assert delete.status_code == 204
