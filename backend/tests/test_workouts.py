def test_strength_requires_duration(client, auth_header):
    r = client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "kind": "strength",
            "body_part": "chest",
            "exercise_name": "卧推",
            "exercise_id": 1,
            "sets": [{"reps": 10}],
        },
    )
    assert r.status_code == 422


def test_strength_workout(client, auth_header):
    r = client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "kind": "strength",
            "body_part": "chest",
            "exercise_name": "杠铃卧推",
            "duration_min": 25,
            "sets": [{"reps": 10}, {"reps": 8}],
        },
    )
    assert r.status_code == 200
    listed = client.get("/api/workouts", headers=auth_header, params={"date": "2026-10-08"})
    assert listed.json()[0]["kind"] == "strength"


def test_cardio_workout(client, auth_header):
    r = client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "kind": "cardio",
            "cardio_type": "run",
            "duration_min": 30,
            "intensity": "medium",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "cardio"
    assert body["payload"]["cardio_type"] == "run"
    assert body["payload"]["duration_min"] == 30


def test_workout_delete_and_ownership(client, auth_header, leaf_auth_header):
    created = client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": "2026-10-09",
            "kind": "cardio",
            "cardio_type": "walk",
            "duration_min": 20,
        },
    ).json()
    delete_other = client.delete(f"/api/workouts/{created['id']}", headers=leaf_auth_header)
    assert delete_other.status_code == 404
    client.delete(f"/api/workouts/{created['id']}", headers=auth_header)
    listed = client.get("/api/workouts", headers=auth_header, params={"date": "2026-10-09"})
    assert listed.json() == []


def test_patch_cardio_and_strength(client, auth_header):
    cardio = client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": "2026-10-10",
            "kind": "cardio",
            "cardio_type": "run",
            "duration_min": 20,
        },
    ).json()
    patched = client.patch(
        f"/api/workouts/{cardio['id']}",
        headers=auth_header,
        json={"duration_min": 35, "intensity": "hard"},
    )
    assert patched.status_code == 200
    assert patched.json()["payload"]["duration_min"] == 35
    assert patched.json()["payload"]["intensity"] == "hard"

    strength = client.post(
        "/api/workouts",
        headers=auth_header,
        json={
            "date": "2026-10-10",
            "kind": "strength",
            "body_part": "bodyweight",
            "exercise_name": "标准俯卧撑",
            "duration_min": 15,
            "sets": [{"reps": 10}, {"reps": 10}],
        },
    ).json()
    patched_s = client.patch(
        f"/api/workouts/{strength['id']}",
        headers=auth_header,
        json={"exercise_name": "宽距俯卧撑", "sets": [{"reps": 12}, {"reps": 12}, {"reps": 12}]},
    )
    assert patched_s.status_code == 200
    assert patched_s.json()["payload"]["exercise_name"] == "宽距俯卧撑"
    assert len(patched_s.json()["payload"]["sets"]) == 3


def test_list_exercises_and_custom(client, auth_header):
    r = client.get("/api/exercises", headers=auth_header, params={"body_part": "chest"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)

    created = client.post(
        "/api/exercises",
        headers=auth_header,
        json={
            "name_zh": "我的变式卧推",
            "body_part": "chest",
            "instructions_zh": "慢速下放",
        },
    )
    assert created.status_code == 200
    data = created.json()
    assert data["is_custom"] is True
    assert data["owner_user_id"] == "dragon"

    listed = client.get("/api/exercises", headers=auth_header, params={"body_part": "chest"})
    ids = {x["id"] for x in listed.json()}
    assert data["id"] in ids
