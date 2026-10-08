"""P0 API-level acceptance (no browser, no vision).

Run from repo root:
  set PYTHONPATH=.   (Windows) / export PYTHONPATH=.  (Unix)
  python scripts/p0_api_acceptance.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.app.db import init_db
from backend.app.main import app

init_db()
c = TestClient(app)


def login(uid: str, pw: str) -> dict[str, str]:
    r = c.post("/api/auth/login", json={"user_id": uid, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def main() -> None:
    h_d = login("dragon", "dragon-pass")
    h_l = login("leaf", "leaf-pass")
    assert (
        c.post("/api/auth/login", json={"user_id": "dragon", "password": "dragon-pass"}).json()[
            "user"
        ]["display_name"]
        == "🐉"
    )
    assert (
        c.post("/api/auth/login", json={"user_id": "leaf", "password": "leaf-pass"}).json()[
            "user"
        ]["display_name"]
        == "🍃"
    )

    day = "2026-10-08"
    assert (
        c.post(
            "/api/meals",
            headers=h_d,
            json={
                "date": day,
                "meal_type": "breakfast",
                "food_summary": "粥",
                "user_kcal": 300,
                "ai_kcal": 300,
                "advice": "",
            },
        ).status_code
        == 200
    )
    assert (
        c.post("/api/water", headers=h_d, json={"date": day, "amount_ml": 500}).status_code
        == 200
    )
    assert (
        c.post(
            "/api/workouts",
            headers=h_d,
            json={"date": day, "kind": "cardio", "cardio_type": "run", "duration_min": 20},
        ).status_code
        == 200
    )

    c.post(
        "/api/meals",
        headers=h_l,
        json={
            "date": day,
            "meal_type": "lunch",
            "food_summary": "沙拉",
            "user_kcal": 400,
            "ai_kcal": 400,
            "advice": "",
        },
    )
    c.post("/api/water", headers=h_l, json={"date": day, "amount_ml": 250})
    c.post(
        "/api/workouts",
        headers=h_l,
        json={
            "date": day,
            "kind": "strength",
            "body_part": "chest",
            "exercise_name": "卧推",
            "sets": [{"reps": 10}],
        },
    )

    meal_id = c.get("/api/meals", headers=h_d, params={"date": day}).json()[0]["id"]
    bad = c.patch(f"/api/meals/{meal_id}", headers=h_l, json={"user_kcal": 1})
    assert bad.status_code in (403, 404), bad.status_code

    today = c.get("/api/today", headers=h_d, params={"date": day}).json()
    assert today["partner"]["user_id"] == "leaf"
    assert "meals" not in today["partner"]
    print("API_ACCEPTANCE_OK")


if __name__ == "__main__":
    main()
