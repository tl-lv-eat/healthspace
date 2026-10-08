# Points Mall Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Goals with a points mall: midnight (configurable) daily settlement, plan-end tier scoring, partner-approved categorized rewards, pending/used inventory.

**Architecture:** Keep `PointsLedger` idempotent grants; replace `points_rules` + disable `after_daily_activity` live grants; add `CoupleSettings` + `SettlementRun`; extend `Reward`/`Redemption`; scheduler loop in FastAPI lifespan; frontend new PointsMall page and Settings block; remove Goals routes/UI.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite, existing points ledger, Vue 3 + Vant, pytest

**Spec:** `docs/superpowers/specs/2026-10-08-points-mall-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/models.py` | `CoupleSettings`, `SettlementRun`; Reward status/category; optional Goal keep-table |
| `backend/app/db.py` | SQLite migrates |
| `backend/app/services/points_rules.py` | Daily + plan tier evaluation |
| `backend/app/services/workout_minutes.py` | Sum cardio+strength `duration_min` |
| `backend/app/services/settlement.py` | Run daily/plan settle; record runs |
| `backend/app/services/points_hooks.py` | No-op or remove callers |
| `backend/app/services/scheduler.py` | Minute tick at settle_hour |
| `backend/app/routers/settings_points.py` | GET/PATCH couple points settings; POST settle-now |
| `backend/app/routers/rewards.py` | Review flow + category |
| `backend/app/routers/goals.py` | Unmount / 410 |
| `backend/app/main.py` | Mount routes; start scheduler |
| `backend/app/routers/workouts.py` | Require strength `duration_min` |
| Frontend: `PointsMallView.vue`, `TabLayout`, `SettingsView`, `WorkoutSheet`, `RewardForm/List`, remove goals |

---

### Task 1: CoupleSettings + SettlementRun models

**Files:**
- Modify: `backend/app/models.py`, `backend/app/db.py`
- Create: `backend/app/routers/couple_settings.py` (or `settings_points.py`)
- Test: `backend/tests/test_couple_settings.py`

- [ ] **Step 1: Failing test** — GET settings returns defaults; PATCH `settle_hour=1` persists.

```python
def test_couple_settings_defaults_and_patch(client, auth_header):
    g = client.get("/api/couple-settings", headers=auth_header)
    assert g.status_code == 200
    assert g.json()["settle_hour"] == 0
    assert g.json()["points_daily_water"] == 1
    p = client.patch(
        "/api/couple-settings",
        headers=auth_header,
        json={"settle_hour": 1, "points_plan_tier_a": -2},
    )
    assert p.status_code == 200
    assert p.json()["settle_hour"] == 1
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement**

`CoupleSettings` single-row table `id=1` with fields from spec. `SettlementRun(id, run_date, kind, meta, created_at)` unique `(run_date, kind)` for `kind in (daily,)` and for plan use `kind=plan:{plan_id}` or separate unique.

Migrate SQLite additive columns / create tables in `db.py`.

Router: get-or-create defaults; patch validates hour 0–23.

- [ ] **Step 4: PASS + commit**

```bash
git commit -m "feat: couple settings for points settlement"
```

---

### Task 2: Workout minutes helper + strength duration validation

**Files:**
- Create: `backend/app/services/workout_minutes.py`
- Modify: `backend/app/routers/workouts.py`
- Test: `backend/tests/test_workout_minutes.py`, extend `test_workouts.py`

- [ ] **Step 1: Tests**

```python
def test_sum_minutes_cardio_and_strength():
    from backend.app.services.workout_minutes import total_workout_minutes
    assert total_workout_minutes([
        {"kind": "cardio", "payload": {"duration_min": 25}},
        {"kind": "strength", "payload": {"duration_min": 20, "sets": []}},
    ]) == 45

def test_strength_requires_duration(client, auth_header):
    r = client.post("/api/workouts", headers=auth_header, json={
        "date": "2026-10-08", "kind": "strength",
        "payload": {"exercise_id": 1, "sets": [{"reps": 10}]},
    })
    assert r.status_code == 422
```

- [ ] **Step 2–4: Implement, PASS, commit**

```bash
git commit -m "feat: require strength duration_min for points"
```

---

### Task 3: Daily settlement rules

**Files:**
- Rewrite: `backend/app/services/points_rules.py` (or new `settle_daily.py`)
- Modify: `backend/app/services/settlement.py`
- Test: `backend/tests/test_points_rules.py` (replace old daily_all_three tests)

- [ ] **Step 1: Tests** — water only → +1; water+deficit → +2; +40min workout → +2 more; empty day → 0; second run same day → no change.

Use `client` + seed water/meals/workouts + call `POST /api/couple-settings/settle?date=...` or service function in-process with db fixture.

- [ ] **Step 2–4: Implement using existing energy status helpers / calendar `_status_for_user` patterns; grant() with new reason keys; PASS; commit**

```bash
git commit -m "feat: daily points settlement water deficit workout"
```

---

### Task 4: Plan tier settlement

**Files:**
- Modify: `backend/app/services/settlement.py` / `points_rules.py`
- Test: `backend/tests/test_plan_settle.py`

- [ ] **Step 1: Three tests** — fabricate plan + daily statuses → B/+5, A/−2, fail/−5; idempotent.

Reuse calendar progress logic (deficit sum, workout days, water_ok each day).

- [ ] **Step 2–4: Implement, PASS, commit**

```bash
git commit -m "feat: plan end tier points B A fail"
```

---

### Task 5: Disable live hooks + scheduler

**Files:**
- Modify: `backend/app/services/points_hooks.py` → empty `after_daily_activity`
- Create: `backend/app/services/scheduler.py`
- Modify: `backend/app/main.py` lifespan start/stop
- Test: `backend/tests/test_settlement_scheduler.py` (unit: `should_run_daily(now, settle_hour, last_run)`)

- [ ] **Step 1: Test** hour gate + settle-now endpoint still works without waiting.

- [ ] **Step 2: Implement** Background thread or AsyncIOScheduler every 60s; if local hour == settle_hour and no `SettlementRun` for yesterday `daily`, settle both users + due plans.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: scheduled points settlement and disable live grants"
```

---

### Task 6: Reward category + review workflow

**Files:**
- Modify: `backend/app/models.py` Reward
- Modify: `backend/app/routers/rewards.py`
- Modify: schemas / migrate
- Test: `backend/tests/test_rewards.py`

- [ ] **Step 1: Tests**

```python
def test_reward_needs_partner_approve_before_redeem(client, auth_header, partner_header):
    # create as dragon → pending_review
    # redeem fails
    # partner approve → listed
    # redeem ok → pending redemption
    # mark fulfilled by owner
```

Also reject with reason; resubmit; category required enum; filter `?category=food`.

- [ ] **Step 2–4: Implement status machine; remove auto-active create; list endpoints for listed / pending_review_for_me / mine; PASS; commit**

```bash
git commit -m "feat: reward categories and partner approval mall"
```

Partner auth: use second user token fixture (add to conftest if missing: login/select leaf).

---

### Task 7: Redemption inventory both users; no refund

**Files:**
- Modify: `backend/app/routers/rewards.py`
- Test: extend `test_rewards.py`

- [ ] **Step 1: GET `/api/redemptions?scope=couple`** returns both users' pending+fulfilled. PATCH cancel refund path: remove or 400. Fulfilled only by redeemer.

- [ ] **Step 2–4: Implement, commit**

```bash
git commit -m "feat: couple redemption inventory without refund"
```

---

### Task 8: Remove Goals API from app

**Files:**
- Modify: `backend/app/main.py` (unmount goals router)
- Delete or keep `goals.py` unused
- Modify/remove: `backend/tests/test_goals.py` (skip or delete)
- Commit

```bash
git commit -m "chore: remove goals API from app"
```

---

### Task 9: Frontend Points Mall page + tab

**Files:**
- Create: `frontend/src/views/PointsMallView.vue`
- Modify: `frontend/src/layouts/TabLayout.vue`, `frontend/src/router/index.ts`
- Modify: `frontend/src/api/rewards.ts`, `points.ts`, new `coupleSettings.ts`
- Rewrite: `RewardForm.vue` (category + submit for review), `RewardList.vue`
- Remove goals from `GoalsView` or replace file content and rename route to `/points-mall` with redirect from `/goals`

- [ ] Sections: balance + ledger; mall by category tabs; pending my review; my rejected; couple pending/used rewards; settle-now button optional

- [ ] `npm run build` PASS

```bash
git commit -m "feat: points mall tab replacing goals"
```

---

### Task 10: Settings points UI + strength duration UI

**Files:**
- Modify: `frontend/src/views/SettingsView.vue`
- Modify: `frontend/src/components/WorkoutSheet.vue` / strength form

- [ ] Settings: settle hour + point fields  
- [ ] Strength: duration_min required input  
- [ ] Build PASS; commit

```bash
git commit -m "feat: settings points rules and strength duration"
```

---

### Task 11: Full verification

- [ ] `pytest backend/tests -q --tb=line`  
- [ ] `npm run build`  
- [ ] Spec status → implemented; commit docs  
- [ ] Report smoke checklist in `.superpowers/sdd/` if using SDD

---

## Spec coverage

| Spec | Task |
|------|------|
| Couple settings / settle hour | 1, 5, 10 |
| Daily water/deficit/40min | 2, 3 |
| Plan B/A/fail | 4 |
| Scheduler + no live grant | 5 |
| Category + approve mall | 6 |
| Inventory both + self fulfill | 7, 9 |
| Remove goals | 8, 9 |
| Strength duration | 2, 10 |

## Notes

- Prefer extracting day status for settle from `day_section` / energy helpers — do not duplicate surplus math.  
- `partner_header` fixture: `POST /api/auth/select` with `leaf` if not present.  
- Config.yaml `points:` legacy keys can remain unused.
