# Task 4 Report: Meal API (upload, estimate, CRUD)

**Status:** Complete  
**Branch:** feature/p0-couple-weight-loss  
**Date:** 2026-10-08

## Deliverables

| File | Change |
|------|--------|
| `backend/app/services/uploads.py` | `save_meal_image`, 5MB cap, Pillow resize max edge 1280. |
| `backend/app/routers/meals.py` | `POST /estimate`, `POST /`, `GET /`, `PATCH /{id}`; ownership on write. |
| `backend/app/schemas.py` | `MealEstimateOut`, `MealCreate`, `MealPatch`, `MealOut`. |
| `backend/app/main.py` | Mount meals router at `/api/meals`. |
| `backend/tests/test_meals.py` | 5 API tests (estimate mocked). |
| `backend/tests/conftest.py` | `auth_header`, `leaf_auth_header`, isolated `UPLOAD_DIR`. |

## Tests

```text
python -m pytest backend/tests -v  → 15 passed (5 meal + prior suite)
```

## Commit

`feat: add meal create/list with editable kcal`

## Interface checklist

- [x] `POST /api/meals/estimate` multipart → `{food_summary, kcal, advice, image_path}`
- [x] `POST /api/meals` JSON create
- [x] `GET /api/meals?date=` current user only
- [x] `PATCH /api/meals/{id}` `user_kcal` / `food_summary`, owner only

## Concerns

1. **Import side effect:** Importing `backend.app.routers.meals` pulls `meal_ai` → `call_llm` (torch) on first meal test (~9s collect). Lazy-import `estimate_calories_from_image` inside the estimate handler if CI startup hurts.
2. **`image_path` on estimate:** Brief lists three fields; added `image_path` so clients can chain estimate → create without re-upload.
3. **Static serving:** Uploaded files are stored under `upload_dir` but not yet exposed via HTTP (frontend Task later).
4. **Date validation:** `date` accepted as string without strict YYYY-MM-DD parse (P0 OK).

## Review fix (2026-10-08)

**UX choice — estimate AI failure:** Return **HTTP 200** with `estimate_failed: true`, empty `food_summary` / `advice`, `kcal: 0`, and **`image_path` preserved** (photo already saved). Client can chain to `POST /api/meals` with hand-filled kcal without re-upload. Aligns with design §7「估卡失败：保留照片，允许手填 kcal」.

**`image_path` on create:** Reject paths not under `{current_user.id}/` → **403**; malformed paths (`..`, extra segments) → **400**.

**Tests:** `test_estimate_meal_ai_failure_keeps_image_path`, `test_create_meal_rejects_other_users_image_path`, `test_create_meal_without_ai`; estimate mocks target `backend.app.services.meal_ai.estimate_calories_from_image`.

**Lazy import:** `meal_ai` imported inside `estimate_meal` only (router import no longer pulls torch).

```text
python -m pytest backend/tests/test_meals.py -v  → 8 passed
```
