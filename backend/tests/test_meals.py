from __future__ import annotations

import io

from PIL import Image


def _tiny_jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), color=(200, 100, 50)).save(buf, format="JPEG")
    return buf.getvalue()


def test_create_meal_and_list(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.meal_ai.estimate_calories_from_image",
        lambda path: {
            "food_summary": "测试餐",
            "kcal": 500,
            "reason": "测试依据",
            "advice": "ok",
        },
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


def test_create_meal_without_ai(client, auth_header):
    r = client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "meal_type": "breakfast",
            "food_summary": "手填餐",
            "user_kcal": 350,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ai_kcal"] is None
    assert body["user_kcal"] == 350
    assert body["image_path"] is None


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
        "backend.app.services.meal_ai.estimate_calories_from_image",
        lambda path: {
            "food_summary": "估卡餐",
            "kcal": 500,
            "reason": "目测一碗面约500",
            "advice": "少油少酱",
        },
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
    assert "500" in body["reason"]
    assert body.get("image_path")
    assert body.get("estimate_failed") is False


def test_refine_meal_estimate(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.meal_ai.refine_calories_estimate",
        lambda **kwargs: {
            "food_summary": "大份面",
            "kcal": 680,
            "reason": "用户说份量更大",
            "advice": "分两次吃",
        },
    )
    r = client.post(
        "/api/meals/estimate/refine",
        headers=auth_header,
        json={
            "food_summary": "面",
            "kcal": 500,
            "reason": "一碗",
            "advice": "控油",
            "message": "其实是大碗",
        },
    )
    assert r.status_code == 200
    assert r.json()["kcal"] == 680


def test_delete_meal(client, auth_header):
    created = client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "meal_type": "snack",
            "food_summary": "酸奶",
            "user_kcal": 120,
        },
    ).json()
    r = client.delete(f"/api/meals/{created['id']}", headers=auth_header)
    assert r.status_code == 204
    listed = client.get("/api/meals", headers=auth_header, params={"date": "2026-10-08"})
    assert listed.json() == []


def test_estimate_meal_ai_failure_keeps_image_path(client, auth_header, monkeypatch):
    def _fail(_path):
        from backend.app.services.meal_ai import MealAIError

        raise MealAIError("vision unavailable")

    monkeypatch.setattr(
        "backend.app.services.meal_ai.estimate_calories_from_image",
        _fail,
    )
    r = client.post(
        "/api/meals/estimate",
        headers=auth_header,
        files={"file": ("meal.jpg", io.BytesIO(_tiny_jpeg()), "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["estimate_failed"] is True
    assert body["image_path"].startswith("dragon/")
    assert body["food_summary"] == ""
    assert body["kcal"] == 0


def test_create_meal_rejects_other_users_image_path(client, auth_header):
    r = client.post(
        "/api/meals",
        headers=auth_header,
        json={
            "date": "2026-10-08",
            "meal_type": "lunch",
            "food_summary": "偷图",
            "user_kcal": 400,
            "image_path": "leaf/deadbeef.jpg",
        },
    )
    assert r.status_code == 403


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
