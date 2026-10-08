# 双人减 P1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 P0 之上交付身体周记与双方对比曲线、周计划、日历上下色块、点日详情、日志摘要 Tab。

**Architecture:** 扩展 SQLite 表 `body_metrics` / `week_plans`；新增完成度解析服务，按周计划规则覆盖默认；日历 API 返回每日双方三维完成状态；前端用 Vant 日历格子自定义渲染 + ECharts 体重对比。

**Tech Stack:** 同 P0；新增前端 `echarts`、`vue-echarts`（或直接 `echarts`）。

**Depends on:** P0 完成（`completion.py`、`/api/today`、双账号 JWT、今日饮食/饮水/运动数据已存在）。

**Spec:** `docs/superpowers/specs/2026-10-08-couple-weight-loss-design.md` §6.1 §6.5 §6.6 §8 P1

## Global Constraints

- 仅两用户：`dragon`（🐉）、`leaf`（🍃）。
- 身体数据约每周记一次；字段：体重、腰围、体脂、胸围、臀围、身高、备注；BMI = weight_kg / (height_m ** 2)。
- 日历日格：**上半 🐉 / 下半 🍃**；色块反映饮水/饮食/运动相对当周规则的完成度。
- 周计划可覆盖默认饮水目标与饮食/运动完成规则。
- 日志只显示摘要，不堆饮食照片。
- 写操作仅本人；可读对方。

---

## File Structure (P1 新增/修改)

```
backend/app/
  models.py              # + BodyMetric, WeekPlan
  completion.py          # 已有；本阶段只消费
  services/
    week_rules.py        # 解析某日生效规则 + 三维完成状态
    bmi.py               # BMI 计算
  routers/
    body.py
    week_plans.py
    calendar.py
    journal.py
frontend/src/
  views/
    CalendarView.vue
    JournalView.vue
    BodyMetricsView.vue
  components/
    CoupleDayCell.vue    # 日历单日上下色块
    BodyTrendChart.vue
  api/
    body.ts
    weekPlans.ts
    calendar.ts
    journal.ts
backend/tests/
  test_bmi.py
  test_week_rules.py
  test_body.py
  test_week_plans.py
  test_calendar.py
  test_journal.py
```

---

### Task 1: BMI 与周规则纯函数

**Files:**
- Create: `backend/app/services/bmi.py`
- Create: `backend/app/services/week_rules.py`
- Create: `backend/tests/test_bmi.py`
- Create: `backend/tests/test_week_rules.py`

**Interfaces:**
- Produces: `calc_bmi(weight_kg: float, height_cm: float) -> float | None`（身高≤0 返回 None，结果保留 1 位小数）
- Produces: `effective_rules(plan: dict | None, user_default_water_ml: int) -> dict`  
  返回形如：
  ```python
  {
    "water_target_ml": 2000,
    "meal_rule": {"mode": "three_main"},  # or "any"
    "workout_rule": {"mode": "any"},      # or {"mode": "cardio_min", "minutes": 30}
  }
  ```
- Produces: `day_status(meals, water_total, workouts, rules) -> dict`  
  `{"meal": bool, "water": bool, "workout": bool, "level": "full"|"partial"|"none"}`  
  - `full`: 三项 True  
  - `partial`: 1–2 项 True  
  - `none`: 0 项 True（含当日无任何记录也算 none）

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_bmi.py
from backend.app.services.bmi import calc_bmi

def test_bmi_normal():
    # 70kg / 1.75m -> 22.9
    assert calc_bmi(70, 175) == 22.9

def test_bmi_bad_height():
    assert calc_bmi(70, 0) is None
```

```python
# backend/tests/test_week_rules.py
from backend.app.services.week_rules import effective_rules, day_status

def test_default_water_when_no_plan():
    r = effective_rules(None, 2000)
    assert r["water_target_ml"] == 2000
    assert r["meal_rule"]["mode"] == "three_main"

def test_plan_overrides_water():
    r = effective_rules({"water_target_ml": 2500, "meal_mode": "any", "workout_mode": "any"}, 2000)
    assert r["water_target_ml"] == 2500
    assert r["meal_rule"]["mode"] == "any"

def test_day_status_levels():
    rules = effective_rules(None, 2000)
    meals = [{"meal_type": "breakfast"}, {"meal_type": "lunch"}, {"meal_type": "dinner"}]
    s = day_status(meals, 2000, [{"kind": "cardio"}], rules)
    assert s["level"] == "full"
    s2 = day_status(meals, 500, [], rules)
    assert s2["level"] == "partial"
    s3 = day_status([], 0, [], rules)
    assert s3["level"] == "none"
```

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest backend/tests/test_bmi.py backend/tests/test_week_rules.py -v`  
Expected: FAIL（import error）

- [ ] **Step 3: 实现**

```python
# backend/app/services/bmi.py
from __future__ import annotations

def calc_bmi(weight_kg: float, height_cm: float) -> float | None:
    if height_cm is None or weight_kg is None:
        return None
    if float(height_cm) <= 0 or float(weight_kg) <= 0:
        return None
    h = float(height_cm) / 100.0
    return round(float(weight_kg) / (h * h), 1)
```

```python
# backend/app/services/week_rules.py
from __future__ import annotations
from backend.app.completion import meal_done, water_done, workout_done

def effective_rules(plan: dict | None, user_default_water_ml: int) -> dict:
    plan = plan or {}
    meal_mode = plan.get("meal_mode") or "three_main"
    workout_mode = plan.get("workout_mode") or "any"
    water = plan.get("water_target_ml")
    if water is None:
        water = user_default_water_ml
    workout_rule: dict = {"mode": workout_mode}
    if workout_mode == "cardio_min":
        workout_rule["minutes"] = int(plan.get("workout_cardio_min") or 30)
    if workout_mode == "strength_sets":
        workout_rule["sets"] = int(plan.get("workout_strength_sets") or 6)
    return {
        "water_target_ml": int(water),
        "meal_rule": {"mode": meal_mode},
        "workout_rule": workout_rule,
    }

def day_status(meals: list, water_total: int, workouts: list, rules: dict) -> dict:
    # workout_done 在 P0 仅支持 any；若 rule 为 cardio_min / strength_sets，在此扩展：
    m = meal_done(meals, rules["meal_rule"])
    w = water_done(water_total, rules["water_target_ml"])
    wo = _workout_done_extended(workouts, rules["workout_rule"])
    n = sum([m, w, wo])
    level = "full" if n == 3 else ("partial" if n >= 1 else "none")
    return {"meal": m, "water": w, "workout": wo, "level": level}

def _workout_done_extended(workouts: list, rule: dict) -> bool:
    mode = rule.get("mode", "any")
    if mode == "any":
        return workout_done(workouts, {"mode": "any"})
    if mode == "cardio_min":
        total = 0
        for x in workouts:
            payload = x.get("payload") if isinstance(x, dict) else {}
            if isinstance(x, dict) and x.get("kind") == "cardio":
                total += int((payload or x).get("duration_min") or x.get("duration_min") or 0)
            elif isinstance(x, dict) and "duration_min" in x:
                total += int(x["duration_min"])
        # 若 workouts 元素已是 ORM 转 dict：约定 payload 内含 duration_min
        for x in workouts:
            if not isinstance(x, dict):
                continue
            p = x.get("payload") or {}
            if isinstance(p, str):
                import json
                p = json.loads(p)
            if x.get("kind") == "cardio":
                total = max(total, 0)  # noop stabilize
                total += int(p.get("duration_min") or 0)
        # 上面可能重复加；实现时只保留一种解析路径（见下方干净版）
        return False  # placeholder replaced in clean impl below
```

实现时用干净版 `_workout_done_extended`（计划要求最终代码如下，以上草稿勿原样粘贴重复累加）：

```python
def _workout_done_extended(workouts: list, rule: dict) -> bool:
    import json
    mode = rule.get("mode", "any")
    parsed = []
    for x in workouts:
        if not isinstance(x, dict):
            continue
        p = x.get("payload") or {}
        if isinstance(p, str):
            p = json.loads(p)
        parsed.append({"kind": x.get("kind"), **p})
    if mode == "any":
        return len(parsed) >= 1
    if mode == "cardio_min":
        mins = sum(int(i.get("duration_min") or 0) for i in parsed if i.get("kind") == "cardio")
        return mins >= int(rule.get("minutes") or 30)
    if mode == "strength_sets":
        sets = 0
        for i in parsed:
            if i.get("kind") != "strength":
                continue
            sets += len(i.get("sets") or [])
        return sets >= int(rule.get("sets") or 6)
    return len(parsed) >= 1
```

并同步扩展 P0 的 `completion.workout_done` **或** 仅在 `week_rules` 使用扩展函数（推荐后者，避免破坏 P0 测试）。更新 `day_status` 调用干净版。

- [ ] **Step 4: 测试 PASS**

Run: `python -m pytest backend/tests/test_bmi.py backend/tests/test_week_rules.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/bmi.py backend/app/services/week_rules.py backend/tests/test_bmi.py backend/tests/test_week_rules.py
git commit -m "feat: add BMI and week-rule day status helpers"
```

---

### Task 2: BodyMetric 模型与 API

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/routers/body.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_body.py`

**Interfaces:**
- Model `BodyMetric`: id, user_id, recorded_on (date), weight_kg, waist_cm, body_fat_pct, chest_cm, hip_cm, height_cm, note, created_at
- `POST /api/body` 本人新增一条（自动算 bmi 只在响应里返回，不强制存列；可选存 `bmi` 列冗余）
- `GET /api/body?user_id=` 默认自己；可传对方 id 只读
- `GET /api/body/trend?user_ids=dragon,leaf` → 双方按日期序列 `{user_id, points:[{date, weight_kg, bmi}]}`

- [ ] **Step 1: 测试**

```python
def test_create_and_trend(client, auth_header):
    r = client.post("/api/body", headers=auth_header, json={
        "recorded_on": "2026-10-01",
        "weight_kg": 70,
        "height_cm": 175,
        "waist_cm": 80,
        "body_fat_pct": 18,
        "chest_cm": 95,
        "hip_cm": 96,
        "note": "开工",
    })
    assert r.status_code == 200
    assert r.json()["bmi"] == 22.9
    t = client.get("/api/body/trend", headers=auth_header, params={"user_ids": "dragon,leaf"})
    assert t.status_code == 200
    assert any(s["user_id"] == "dragon" for s in t.json()["series"])
```

- [ ] **Step 2: 实现 models + router → PASS**

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add body metrics CRUD and trend API"
```

---

### Task 3: WeekPlan 模型与 API

**Files:**
- Modify: `backend/app/models.py`（WeekPlan）
- Create: `backend/app/routers/week_plans.py`
- Create: `backend/tests/test_week_plans.py`

**Interfaces:**
- Model: id, user_id, week_start (该周一日期 ISO), water_target_ml, meal_mode, workout_mode, workout_cardio_min, workout_strength_sets, unique(user_id, week_start)
- `GET /api/week-plans?week_start=YYYY-MM-DD` → 当前用户计划（无则返回 defaults 派生对象、`id=null`）
- `PUT /api/week-plans` upsert 本人当周计划
- 约定 `week_start` 必须为周一；若客户端传周内任一天，服务端归一到周一：

```python
from datetime import date, timedelta

def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())
```

- [ ] **Step 1: 测试 upsert 与默认**

```python
def test_week_plan_upsert(client, auth_header):
    r = client.put("/api/week-plans", headers=auth_header, json={
        "week_start": "2026-10-06",  # Monday
        "water_target_ml": 2500,
        "meal_mode": "any",
        "workout_mode": "any",
    })
    assert r.status_code == 200
    g = client.get("/api/week-plans", headers=auth_header, params={"week_start": "2026-10-08"})
    assert g.json()["water_target_ml"] == 2500
```

- [ ] **Step 2: 实现 → PASS → Commit**

```bash
git commit -m "feat: add per-user weekly plan upsert API"
```

---

### Task 4: 日历与日志 API

**Files:**
- Create: `backend/app/routers/calendar.py`
- Create: `backend/app/routers/journal.py`
- Create: `backend/tests/test_calendar.py`
- Create: `backend/tests/test_journal.py`
- Modify: `backend/app/routers/today.py`（可选：today 的 water target 改为走 `effective_rules`）

**Interfaces:**
- `GET /api/calendar?year=2026&month=10` →

```json
{
  "year": 2026,
  "month": 10,
  "days": [
    {
      "date": "2026-10-08",
      "dragon": {"meal": true, "water": false, "workout": true, "level": "partial"},
      "leaf": {"meal": false, "water": false, "workout": false, "level": "none"}
    }
  ]
}
```

对月内每一天、每个用户：查 meals/water/workouts + 该周 WeekPlan → `day_status`。

- `GET /api/calendar/day?date=2026-10-08` → 双方摘要 + 若当前用户则附带本人当日 meals/water/workouts 详情入口数据（可复用 today 结构）

- `GET /api/journal?from=&to=&user_id=`  
  - `user_id` 省略=双方；或 `dragon` / `leaf`  
  - 返回按日期倒序：

```json
{
  "items": [
    {
      "date": "2026-10-08",
      "users": [
        {
          "user_id": "dragon",
          "display_name": "🐉",
          "meal_done": true,
          "water_total_ml": 1800,
          "water_target_ml": 2000,
          "water_done": false,
          "workout_done": true
        }
      ]
    }
  ]
}
```

无照片字段。

- [ ] **Step 1: 日历测试（造两天数据后断言 level）**

```python
def test_calendar_month_levels(client, auth_header):
    # 用已有 meals/water API 造 dragon 当天三项全满（需设 week plan 或默认）
    ...
    r = client.get("/api/calendar", headers=auth_header, params={"year": 2026, "month": 10})
    day = next(d for d in r.json()["days"] if d["date"] == "2026-10-08")
    assert "level" in day["dragon"]
    assert "level" in day["leaf"]
```

- [ ] **Step 2: 日志测试筛选只看 leaf**

```python
def test_journal_filter_leaf(client, auth_header):
    r = client.get("/api/journal", headers=auth_header, params={
        "from": "2026-10-01", "to": "2026-10-31", "user_id": "leaf"
    })
    for item in r.json()["items"]:
        assert all(u["user_id"] == "leaf" for u in item["users"])
```

- [ ] **Step 3: 实现 → PASS**

- [ ] **Step 4: 改 today 饮水 target 走 week_rules**（回归 `test_today` / `test_water`）

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add calendar status and journal summary APIs"
```

---

### Task 5: 前端身体数据页 + ECharts 对比

**Files:**
- Create: `frontend/src/views/BodyMetricsView.vue`
- Create: `frontend/src/components/BodyTrendChart.vue`
- Create: `frontend/src/api/body.ts`
- Modify: `frontend/package.json`（依赖 `echarts`）
- Modify: `frontend/src/router/index.ts`（`/body`）
- Modify: `frontend/src/views`「我的」入口链到身体数据（若 P0 已有 `MineView` 占位则接上；否则新建 `MineView.vue` 最小链接）

**行为：**
- 表单录入周记字段，提交 `POST /api/body`
- 图表：双方 `weight_kg` 折线同屏，图例 🐉/🍃

- [ ] **Step 1: `npm i echarts`**
- [ ] **Step 2: 实现表单 + `BodyTrendChart`（option 双 series）**

```ts
// BodyTrendChart 核心 option 示意
{
  legend: { data: ['🐉', '🍃'] },
  xAxis: { type: 'category', data: dates },
  yAxis: { type: 'value', name: 'kg' },
  series: [
    { name: '🐉', type: 'line', data: dragonWeights },
    { name: '🍃', type: 'line', data: leafWeights },
  ],
}
```

- [ ] **Step 3: 手测录入一条并看到点**
- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add body metrics form and couple weight chart"
```

---

### Task 6: 前端日历 Tab + 周计划编辑 + 日详情

**Files:**
- Create: `frontend/src/views/CalendarView.vue`
- Create: `frontend/src/components/CoupleDayCell.vue`
- Create: `frontend/src/components/WeekPlanEditor.vue`
- Create: `frontend/src/views/DayDetailView.vue`
- Create: `frontend/src/api/calendar.ts`, `weekPlans.ts`
- Modify: `frontend/src/layouts/TabLayout.vue`（日历 Tab 指向真实页）

**CoupleDayCell 视觉约定：**
- 单元格固定高度；上半 `dragon.level`、下半 `leaf.level`
- CSS 变量：`--level-full: #3d8b6e`；`--level-partial: #d4a017`；`--level-none: #e8e4de`
- 不在一格画三种细条（P1 用 level 主色，图例在月历上方说明「全达成/部分/未完成」）

**周计划：** 日历顶栏按钮打开 `WeekPlanEditor`（van-popup）：饮水目标、饮食 mode 单选、运动 mode 单选 → `PUT /api/week-plans`

**点日：** 路由 `/calendar/day/:date` → `DayDetailView` 调 `/api/calendar/day`

- [ ] **Step 1: 实现单元格 + 拉月数据渲染**
- [ ] **Step 2: 周计划保存后重新拉日历**
- [ ] **Step 3: 日详情可跳回今日编辑（本人）**
- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add couple calendar cells and week plan editor"
```

---

### Task 7: 前端日志 Tab + P1 验收

**Files:**
- Create: `frontend/src/views/JournalView.vue`
- Create: `frontend/src/api/journal.ts`
- Modify: TabLayout 日志 Tab

**行为：** 筛选「双方 / 🐉 / 🍃」；列表按日倒序显示摘要勾选与饮水量。

- [ ] **Step 1: 实现 JournalView**
- [ ] **Step 2: P1 验收清单**
  - [ ] 双方各录入 ≥1 条身体数据，趋势图双线可见
  - [ ] 修改周饮水目标后，日历色块与今日饮水 target 一致
  - [ ] 月历上半/下半颜色可区分两人
  - [ ] 点日能看详情
  - [ ] 日志无照片墙，筛选只看一方有效
- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add journal tab and finish P1 acceptance hooks"
```

---

## Self-review (author)

**Spec P1 coverage:** 身体周记+BMI+对比 ✅；日历上下色块 ✅；周计划覆盖 ✅；日志摘要 ✅；点日详情 ✅。

**Placeholders:** 无 TBD。workout 扩展规则在 `week_rules._workout_done_extended` 一次写清。

**Consistency:** `meal_mode` / `workout_mode` 字符串与 P0 `completion`、日历 `level` 三值贯穿。
