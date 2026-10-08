# Plan · Calendar · Today Linkage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Role-scoped period plans (title/note/kcal cap, couple can edit either), month history under calendar, dual-column Today-like day detail, Today folded energy + plan targets, BMR sex/age in Settings/Mine.

**Architecture:** Extend `WeekPlan` / `User` columns and existing routers (`week_plans`, `today`, `calendar`, `auth`). Reuse `_build_me_section` for both personas on calendar day. Frontend: enrich `WeekPlanEditor` + `CalendarView` list; rebuild `DayDetailView` as dual columns from full sections; add collapsible energy on `TodayView`; Settings for sex/age feeding `user_bmr()`.

**Tech Stack:** FastAPI + SQLAlchemy/SQLite, Vue 3 + Vant + Pinia, pytest

**Spec:** `docs/superpowers/specs/2026-10-08-plan-calendar-today-linkage-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/models.py` | `User.sex`, `User.age`; `WeekPlan.title`, `note`, `daily_kcal_cap` |
| `backend/app/db.py` | SQLite additive migrate for new columns |
| `backend/app/schemas.py` | Profile + WeekPlan + UserOut fields |
| `backend/app/services/energy.py` | Prefer User sex/age in `resolve_body_profile` |
| `backend/app/services/week_rules.py` | Pass through `daily_kcal_cap` in `effective_rules` |
| `backend/app/routers/week_plans.py` | `target_user_id`, month couple list, new fields |
| `backend/app/routers/today.py` | Attach `energy` + plan targets; export section builder; water entries on me |
| `backend/app/routers/calendar.py` | Day endpoint returns dual today-shaped sections |
| `backend/app/routers/auth.py` | PATCH sex/age |
| `backend/tests/test_energy.py` | BMR from User fields |
| `backend/tests/test_week_plans.py` | Cross-user create, month filter, new fields |
| `backend/tests/test_today.py` | Energy block |
| `backend/tests/test_calendar.py` | Day dual sections with water entries |
| `backend/tests/test_auth.py` | Profile sex/age |
| `frontend/src/api/*.ts` | Types + list params |
| `frontend/src/components/WeekPlanEditor.vue` | Persona pick + title/note/cap |
| `frontend/src/views/CalendarView.vue` | Month plans grouped by role |
| `frontend/src/views/DayDetailView.vue` | Dual-column today-like |
| `frontend/src/views/TodayView.vue` | Folded energy ledger |
| `frontend/src/views/SettingsView.vue` | Sex/age fields |
| `frontend/src/stores/auth.ts` | `updateProfile` payload |

---

### Task 1: User sex/age + BMR resolution

**Files:**
- Modify: `backend/app/models.py` (`User`)
- Modify: `backend/app/db.py` (`_ensure_*` migrate)
- Modify: `backend/app/schemas.py` (`UserOut`, `ProfileUpdateRequest`)
- Modify: `backend/app/services/energy.py` (`resolve_body_profile`)
- Modify: `backend/app/routers/auth.py` (`update_me`)
- Test: `backend/tests/test_energy.py`, `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

Add to `backend/tests/test_energy.py`:

```python
def test_user_bmr_uses_user_sex_age(db_session, dragon_user):
    from backend.app.services.energy import user_bmr
    dragon_user.sex = "male"
    dragon_user.age = 40
    db_session.add(dragon_user)
    db_session.commit()
    bmr_old_age = user_bmr(dragon_user, db_session)
    dragon_user.age = 25
    db_session.commit()
    bmr_young = user_bmr(dragon_user, db_session)
    assert bmr_young > bmr_old_age
```

If fixtures differ, use whatever conftest provides (`client` + DB via app). Prefer:

```python
def test_bmr_respects_patched_age(client, auth_header):
    # patch age then hit an endpoint that exposes bmr, or call service in-process
    ...
```

Simplest reliable pattern matching this repo: open SessionLocal in test or use existing energy unit tests. Add:

```python
def test_resolve_body_profile_prefers_user_fields():
    from backend.app.db import SessionLocal
    from backend.app.models import User
    from backend.app.services.energy import resolve_body_profile

    with SessionLocal() as db:
        u = db.get(User, "dragon")
        assert u is not None
        u.sex = "female"
        u.age = 35
        db.commit()
        db.refresh(u)
        p = resolve_body_profile(u, db)
        assert p["sex"] == "female"
        assert p["age"] == 35
```

Add auth test:

```python
def test_patch_me_sex_age(client, auth_header):
    r = client.patch(
        "/api/auth/me",
        headers=auth_header,
        json={"display_name": "龙龙", "sex": "male", "age": 30},
    )
    assert r.status_code == 200
    assert r.json()["sex"] == "male"
    assert r.json()["age"] == 30
```

- [ ] **Step 2: Run tests — expect FAIL**

```bash
$env:PYTHONPATH="d:\Program\Private\jianfei"; python -m pytest backend/tests/test_energy.py backend/tests/test_auth.py -q --tb=line
```

Expected: fail on missing `sex`/`age` or schema rejection.

- [ ] **Step 3: Implement**

`User` model add:

```python
sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
age: Mapped[int | None] = mapped_column(Integer, nullable=True)
```

In `db.py`, extend migrate (new helper or existing) to `ALTER TABLE users ADD COLUMN sex` / `age`.

`ProfileUpdateRequest`:

```python
class ProfileUpdateRequest(BaseModel):
    display_name: str
    sex: str | None = None  # male|female
    age: int | None = None
```

`UserOut` add `sex: str | None = None`, `age: int | None = None`.

`update_me`: after name, if `body.sex in ("male","female")` set it; if `body.age` is int 10–100 set it.

`resolve_body_profile`:

```python
defaults = DEFAULT_PROFILES.get(user.id, DEFAULT_PROFILES["dragon"])
sex = getattr(user, "sex", None) or defaults["sex"]
age = int(getattr(user, "age", None) or defaults["age"])
# weight/height from BodyMetric as today
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
$env:PYTHONPATH="d:\Program\Private\jianfei"; python -m pytest backend/tests/test_energy.py backend/tests/test_auth.py -q --tb=line
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/app/db.py backend/app/schemas.py backend/app/services/energy.py backend/app/routers/auth.py backend/tests/test_energy.py backend/tests/test_auth.py
git commit -m "feat: persist user sex/age for BMR"
```

---

### Task 2: WeekPlan title, note, daily_kcal_cap + couple write/list

**Files:**
- Modify: `backend/app/models.py` (`WeekPlan`)
- Modify: `backend/app/db.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/routers/week_plans.py`
- Modify: `backend/app/services/week_rules.py`
- Test: `backend/tests/test_week_plans.py`

- [ ] **Step 1: Write failing tests**

```python
def test_create_plan_for_partner(client, auth_header):
    # auth_header is dragon
    r = client.put(
        "/api/week-plans",
        headers=auth_header,
        json={
            "target_user_id": "leaf",
            "start_date": "2026-10-01",
            "end_date": "2026-10-14",
            "title": "叶子冲刺",
            "note": "少油",
            "daily_kcal_cap": 1600,
            "water_target_ml": 2200,
            "weekly_kcal_deficit": 7000,
            "weekly_workout_sessions": 4,
            "meal_mode": "three_main",
            "workout_mode": "any",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == "leaf"
    assert body["title"] == "叶子冲刺"
    assert body["daily_kcal_cap"] == 1600

    listed = client.get(
        "/api/week-plans",
        headers=auth_header,
        params={"list": True, "month": "2026-10"},
    )
    assert listed.status_code == 200
    assert any(p["user_id"] == "leaf" and p["title"] == "叶子冲刺" for p in listed.json())

    on = client.get("/api/week-plans", headers=auth_header, params={"on": "2026-10-05", "user_id": "leaf"})
    assert on.json()["water_target_ml"] == 2200
```

- [ ] **Step 2: Run — expect FAIL**

```bash
$env:PYTHONPATH="d:\Program\Private\jianfei"; python -m pytest backend/tests/test_week_plans.py::test_create_plan_for_partner -q --tb=short
```

- [ ] **Step 3: Implement**

Model columns: `title` String(128) nullable, `note` Text default `""`, `daily_kcal_cap` Integer nullable.

Migrate in `db.py`.

Schemas: add fields to Upsert/Out; Upsert add `target_user_id: str | None = None`.

`week_rules.effective_rules`: include `"daily_kcal_cap": plan.get("daily_kcal_cap")`.

`_plan_dict` / `_plan_to_out`: include title, note, daily_kcal_cap.

`_couple_user_ids` helper: `{"dragon","leaf"}`.

On PUT: `owner_id = body.target_user_id or user.id`; if owner_id not in couple → 422; load/create plan with `user_id=owner_id`.

DELETE: allow if plan.user_id in couple (not only JWT user).

GET list: if `list` and `month=YYYY-MM`, query both users where ranges intersect month:

```python
# month_start, month_end iso strings
# plan intersects if week_start <= month_end and (end_date or week_start) >= month_start
```

GET single: optional `user_id` query — resolve plan for that user on `on` date (default current user).

- [ ] **Step 4: Run — expect PASS**

```bash
$env:PYTHONPATH="d:\Program\Private\jianfei"; python -m pytest backend/tests/test_week_plans.py -q --tb=line
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models.py backend/app/db.py backend/app/schemas.py backend/app/routers/week_plans.py backend/app/services/week_rules.py backend/tests/test_week_plans.py
git commit -m "feat: couple week plans with title note and kcal cap"
```

---

### Task 3: Today energy + plan targets; water entries on me section

**Files:**
- Modify: `backend/app/routers/today.py`
- Test: `backend/tests/test_today.py`

- [ ] **Step 1: Write failing test**

```python
def test_today_includes_energy(client, auth_header):
    # seed a meal via API if helpers exist; otherwise minimal assert on shape
    r = client.get("/api/today", headers=auth_header, params={"date": "2026-10-08"})
    assert r.status_code == 200
    me = r.json()["me"]
    assert "energy" in me
    e = me["energy"]
    for k in ("intake_kcal", "burn_kcal", "bmr", "surplus_kcal", "daily_deficit_target", "daily_kcal_cap", "water_target_ml"):
        assert k in e
    assert "water_entries" in me["water"] or "entries" in me
```

Prefer attaching entries as `me.water.entries` list of `{id, amount_ml, created_at}`.

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement**

In `_build_me_section` (and a shared `_build_full_section` used for any user):

```python
from backend.app.services.energy import daily_energy_snapshot, user_bmr, estimate_workout_burn_kcal
# build workout dicts, intake sum, plan rules
snap = daily_energy_snapshot(...)
plan = get_week_plan_for_user(...)
rules = effective_rules(...)
entries = [...]  # WaterEntry outs
return {
  ...
  "water": {"total_ml", "target_ml", "done", "entries": entries},
  "energy": {
    "intake_kcal": snap["intake_kcal"],
    "burn_kcal": snap["burn_kcal"],
    "bmr": snap["bmr"],
    "surplus_kcal": snap["surplus_kcal"],
    "daily_deficit_target": snap["daily_deficit_target"],
    "daily_kcal_cap": rules.get("daily_kcal_cap"),
    "water_target_ml": rules["water_target_ml"],
    "period_days": rules.get("period_days") or 7,
  },
  "plan": {
    "title": ...,
    "id": ...,
    "start_date": ...,
    "end_date": ...,
  }  # optional null
}
```

Refactor `_build_partner_section` to call the same full builder (or thin wrapper) so calendar day can reuse — partner may keep summary fields for Today duo rail **plus** full data under `partner.full` OR change Today partner to full section. Spec: day detail needs full both sides. Simplest: `_build_full_section(user, date, db)` returns full shape; Today returns `me=full(me)`, `partner=full(partner)` and update Today UI types (partner rail can still read `done` / water totals from full).

- [ ] **Step 4: pytest `test_today.py` PASS; update frontend types in a later task if tests are backend-only**

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: today section energy and water entries"
```

---

### Task 4: Calendar day returns dual full sections

**Files:**
- Modify: `backend/app/routers/calendar.py`
- Test: `backend/tests/test_calendar.py`

- [ ] **Step 1: Failing test**

```python
def test_calendar_day_dual_sections(client, auth_header):
    r = client.get("/api/calendar/day", headers=auth_header, params={"date": "2026-10-08"})
    assert r.status_code == 200
    body = r.json()
    assert "dragon_section" in body or (body["dragon"].get("meals") is not None)
    # Preferred shape:
    # body["sections"]["dragon"] and body["sections"]["leaf"] each with meals, water.entries, workouts, done, energy
```

Use explicit:

```python
assert "sections" in body
for key in ("dragon", "leaf"):
    s = body["sections"][key]
    assert "meals" in s and "workouts" in s
    assert "entries" in s["water"]
    assert "energy" in s
```

Keep legacy `dragon`/`leaf` status for level if needed, or nest `status` inside section.

- [ ] **Step 2: FAIL then implement** — `get_calendar_day` calls `_build_full_section` for dragon and leaf from `today` module (import carefully to avoid cycles; move builders to `backend/app/services/day_section.py` if import cycle appears).

Recommended: create `backend/app/services/day_section.py` with `build_day_section(user, date, db) -> dict` moved from today.py; today + calendar both import it.

- [ ] **Step 3: PASS + commit**

```bash
git commit -m "feat: calendar day dual full day sections"
```

---

### Task 5: Frontend API types + auth profile

**Files:**
- Modify: `frontend/src/api/weekPlans.ts`
- Modify: `frontend/src/api/today.ts`
- Modify: `frontend/src/api/calendar.ts`
- Modify: `frontend/src/stores/auth.ts`

- [ ] **Step 1: Update types**

`WeekPlan`: `title`, `note`, `daily_kcal_cap`, keep dates.

`listWeekPlans(month?: string)` → `params: { list: true, month }`.

`saveWeekPlan` body includes `target_user_id`, `title`, `note`, `daily_kcal_cap`.

`TodayMe` / shared `DaySection`:

```typescript
export interface DayEnergy {
  intake_kcal: number
  burn_kcal: number
  bmr: number
  surplus_kcal: number
  daily_deficit_target: number
  daily_kcal_cap: number | null
  water_target_ml: number
  period_days: number
}
```

`CalendarDayDetail.sections: { dragon: DaySection, leaf: DaySection }`.

`auth.updateProfile({ display_name, sex?, age? })`.

- [ ] **Step 2: Commit**

```bash
git commit -m "chore: frontend types for plan and energy linkage"
```

---

### Task 6: Settings sex/age UI

**Files:**
- Modify: `frontend/src/views/SettingsView.vue`
- Modify: `frontend/src/stores/auth.ts` (if not done)

- [ ] **Step 1: Add fields** — radio/select 男/女, number age; save with display_name via `updateProfile`.

- [ ] **Step 2: Manual smoke** — save, reload `/api/auth/me`, confirm fields.

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: settings sex and age for BMR"
```

---

### Task 7: WeekPlanEditor — persona + richer fields

**Files:**
- Modify: `frontend/src/components/WeekPlanEditor.vue`

- [ ] **Step 1: UI** — on create: persona chips 龙龙/叶子 → set `targetUserId`. On edit: show owner, locked or still changeable. Fields: title, note textarea, daily_kcal_cap number, existing date/water/deficit/workouts/weight. Hint text for cap vs deficit.

- [ ] **Step 2: Save payload includes new fields + `target_user_id`.**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: week plan editor persona title note cap"
```

---

### Task 8: CalendarView — month history by role

**Files:**
- Modify: `frontend/src/views/CalendarView.vue`

- [ ] **Step 1:** `listWeekPlans(\`${year}-${month}\`)` on load; group `dragon` / `leaf`; cards show title, range, water, deficit, cap; new opens editor with persona step; keep month grid color-only (CoupleDayCell levels).

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: calendar month plans grouped by persona"
```

---

### Task 9: TodayView folded energy ledger

**Files:**
- Modify: `frontend/src/views/TodayView.vue`

- [ ] **Step 1:** Collapsible `<details>` or button 「能量账本」 showing intake / burn / BMR / surplus|deficit; compare to `daily_deficit_target` and `daily_kcal_cap` (warn style if intake > cap). Water target already from API — verify it updates when plan covers date.

- [ ] **Step 2: Commit**

```bash
git commit -m "feat: today collapsible energy ledger"
```

---

### Task 10: DayDetailView dual-column Today-like

**Files:**
- Modify: `frontend/src/views/DayDetailView.vue`
- Optionally create: `frontend/src/components/DaySectionPanel.vue` (read-only meal/water/workout/energy/done)

- [ ] **Step 1: Implement layout** — CSS grid 1fr 1fr; `@media (max-width: 640px) { grid-template-columns: 1fr }`. Each column: name, done flags, meal list (`food_summary` + kcal), water total/target + entry times (`created_at` formatted HH:mm), workout summaries, folded energy. Top bar: back + 「去改记」 → `today?date=`.

- [ ] **Step 2: Wire `fetchCalendarDay` sections.**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: dual-column calendar day detail like today"
```

---

### Task 11: Full verification

- [ ] **Step 1: Backend**

```bash
$env:PYTHONPATH="d:\Program\Private\jianfei"; python -m pytest backend/tests -q --tb=line
```

Expected: all green.

- [ ] **Step 2: Smoke** — create leaf plan as dragon; open calendar month list; open a day dual columns; Today energy fold; Settings age changes BMR on day energy.

- [ ] **Step 3: Commit docs if linkage spec needs status bump**

```bash
git commit -m "docs: mark plan-calendar-today linkage implemented"
```

(only if you update status line in the spec)

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Plan title/note/cap | 2, 7 |
| target_user_id / couple edit | 2, 7 |
| Month history list | 2, 8 |
| Month grid colors only | 8 (no cell number change) |
| Day detail Today-like dual | 4, 10 |
| Today plan targets + energy fold | 3, 9 |
| BMR sex/age in settings | 1, 6 |
| calendar/day full sections | 4 |
| Overlap / 60-day rules | existing week_plans + Task 2 |

## Self-review notes

- No TBD placeholders in tasks.
- Prefer extracting `day_section.py` in Task 4 if today↔calendar import cycles appear — do that before duplicating builders.
- `daily_kcal_cap` never blocks meal POST.
- Partner Today duo rail: after Task 3 full partner section, map `partner.done` etc. from the same object so TodayView does not break.
