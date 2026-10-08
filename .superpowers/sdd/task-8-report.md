# Task 8 Report: Vue H5 scaffold + login

**Status:** Complete  
**Date:** 2026-10-08

## Deliverables

| File | Change |
|------|--------|
| `frontend/` | Vue3 + Vite + TS; Vant (full), Pinia, vue-router, axios; proxy `/api` → `127.0.0.1:8000`. |
| `frontend/src/api/http.ts` | Axios `/api`, Bearer from localStorage, 401 clears session keys. |
| `frontend/src/stores/auth.ts` | Login → token + user in localStorage. |
| `frontend/src/views/LoginView.vue` | 🐉 / 🍃 cards + password → `POST /auth/login`. |
| `frontend/src/router/index.ts` | Guard; `/today` placeholder shell. |
| `backend/app/main.py` | Mount `frontend/dist` when present. |

## Verification

```text
cd frontend && npm run build  → OK
python -m pytest backend/tests -q  → 28 passed
```

Manual H5 login in browser: **not run** (backend dev server not up in this session).

## Commit

`feat: add Vue H5 login shell with Vant`

## Interface checklist

- [x] Login UI 🐉 / 🍃 + password
- [x] JWT stored; unauthenticated → `/login`
- [x] Post-login → `/today` empty shell

## Follow-up (review Important)

**Issue:** HTTP 401 interceptor cleared `localStorage` only; Pinia `token`/`user` stayed in memory so `/today` could render stale auth until reload.

**Fix:**

| File | Change |
|------|--------|
| `frontend/src/api/http.ts` | `setUnauthorizedHandler`; on 401 (except `POST /auth/login`) invoke handler instead of clearing storage directly. |
| `frontend/src/main.ts` | After Pinia + router: handler calls `useAuthStore().clearSession()` and `router.push({ name: 'login' })`. |

**Verification:** `cd frontend && npm run build` → OK

**Commit:** _(SHA appended after commit)_
