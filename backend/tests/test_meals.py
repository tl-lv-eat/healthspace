from __future__ import annotations

import io

from PIL import Image


def _tiny_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(200, 100, 50)).save(buf, format="JPEG")
    return buf.getvalue()


def test_create_meal_and_list(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.routers.meals.estimate_calories_from_image",
        lambda path: {"food_summary": "测试餐", "kcal": 500, "advice": "ok"},
    )
    r = client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "meal_type": "lunch",
            "food_summary": "测试餐",
            "ai_kcal": 500,
            "user_kcal": 480,
            "advice": "ok",
        },
    )
    assert r.status_code == 200
    listed = client.get("/api/meals", headers=auth_header, params={"date": "2026-10-08"})
    assert len(listed.json()) == 1
    assert listed.json()[0]["user_kcal"] == 480


def test_patch_meal_user_kcal(client, auth_header):
    created = client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "meal_type": "dinner",
            "food_summary": "沙拉",
            "user_kcal": 300,
        },
    ).json()
    r = client.patch(
        f"/api/meals/{created['id']}",
        headers=auth_header,
        json={"user_kcal": 280, "food_summary": "大份沙拉"},
    )
    assert r.status_code == 200
    assert r.json()["user_kcal"] == 280
    assert r.json()["food_summary"] == "大份沙拉"


def test_estimate_meal(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.routers.meals.estimate_calories_from_image",
        lambda path: {"food_summary": "估卡餐", "kcal": 500, "advice": "ok"},
    )
    r = client.post(
        "/api/meals/estimate",
        headers=auth_header,
        files={"file": ("meal.jpg", io.BytesIO(_tiny_jpeg()), "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["kcal"] == 500
    assert body["food_summary"] == "估卡餐"
    assert body.get("image_path")


def test_cannot_patch_other_users_meal(client, auth_header, leaf_auth_header):
    created = client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "meal_type": "breakfast",
            "food_summary": "粥",
            "user_kcal": 200,
        },
    ).json()
    r = client.patch(
        f"/api/meals/{created['id']}",
        headers=leaf_auth_header,
        json={"user_kcal": 999},
    )
    assert r.status_code == 404


def test_list_meals_only_current_user(client, auth_header, leaf_auth_header):
    client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "meal_type": "snack",
            "food_summary": "dragon",
            "user_kcal": 100,
        },
    )
    client.post(
        "/api/meals",
        headers=leaf_auth_header,
        json={
            "date": "2026-10-08",
            "meal_type": "snack",
            "food_summary": "leaf",
            "user_kcal": 100,
        },
    )
    dragon_list = client.get("/api/meals", headers=auth_header, params={"date": "2026-10-08"}).json()
    assert len(dragon_list) == 1
    assert dragon_list[0]["food_summary"] == "dragon"
