# 双人减 P2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付双方短/长期目标、按日/周完成规则自动积分、可自定义（含私密）奖励清单与积分兑奖闭环。

**Architecture:** 新增 `goals` / `rewards` / `points_ledger` / `redemptions` 表；积分发放做成可幂等服务（同一用户同一天同一规则只发一次）；目标进度由规则引擎根据 body/日历完成度更新；前端「目标」Tab 完成目标卡片、积分余额、奖励商场与兑奖。

**Tech Stack:** 同 P0/P1；无新基础设施。

**Depends on:** P0 + P1（需要 `day_status` / 周计划完成判定作为加分输入）。

**Spec:** `docs/superpowers/specs/2026-10-08-couple-weight-loss-design.md` §6.7 §8 P2

## Global Constraints

- 积分无真实货币/支付；兑奖仅为情侣约定状态机。
- 奖励可标记 `is_private`：列表默认折叠标题，详情需二次确认后展示完整说明。
- 积分价由创建者按「尺度 / 花费感」自定义整数。
- 发分规则默认（可在 config `app.points` 覆盖）：
  - `daily_all_three`: 当日 meal+water+workout 全 true → +10（每用户每天最多一次）
  - `weekly_plan_complete`: 自然周 Mon–Sun 该用户每天都 `level==full` → +50（每用户每周最多一次）
- 短/长期目标可互看；写仅本人（或创建者）。

---

## File Structure (P2)

```
backend/app/
  models.py                 # + Goal, Reward, PointsLedger, Redemption
  services/
    points.py               # grant / balance / idempotent keys
    goals_progress.py       # 刷新目标进度
  routers/
    goals.py
    rewards.py
    points.py
frontend/src/
  views/GoalsView.vue
  components/
    GoalCard.vue
    RewardList.vue
    RewardForm.vue
    PointsBadge.vue
  api/goals.ts, rewards.ts, points.ts
backend/tests/
  test_points.py
  test_goals.py
  test_rewards.py
```

---

### Task 1: 积分账本纯服务（幂等）

**Files:**
- Create: `backend/app/services/points.py`
- Create: `backend/tests/test_points.py`
- Modify: `backend/app/models.py`（PointsLedger）

**Interfaces:**
- Model `PointsLedger`: id, user_id, delta (int, 可负), reason (str), idempotency_key (str unique), meta_json, created_at
- `get_balance(db, user_id: str) -> int` 对 delta sum
- `grant(db, user_id: str, delta: int, reason: str, idempotency_key: str, meta: dict | None=None) -> tuple[bool, int]`  
  返回 `(created, balance)`；若 key 已存在则 `created=False` 且不重复加分

- [ ] **Step 1: 写测试**

```python
def test_grant_idempotent(db_session):
    from backend.app.services.points import grant, get_balance
    ok1, bal1 = grant(db_session, "dragon", 10, "daily_all_three", "dragon:2026-10-08:daily_all_three")
    ok2, bal2 = grant(db_session, "dragon", 10, "daily_all_three", "dragon:2026-10-08:daily_all_three")
    assert ok1 is True and bal1 == 10
    assert ok2 is False and bal2 == 10
    assert get_balance(db_session, "dragon") == 10
```

（`db_session` 在 conftest 提供与 API 测试相同的临时库。）

- [ ] **Step 2: FAIL → 实现 model + grant → PASS**

```python
def grant(db, user_id: str, delta: int, reason: str, idempotency_key: str, meta=None):
    existing = db.query(PointsLedger).filter_by(idempotency_key=idempotency_key).first()
    if existing:
        return False, get_balance(db, user_id)
    row = PointsLedger(
        user_id=user_id,
        delta=int(delta),
        reason=reason,
        idempotency_key=idempotency_key,
        meta_json=json.dumps(meta or {}, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    return True, get_balance(db, user_id)
```

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add idempotent points ledger"
```

---

### Task 2: 日/周自动发分钩子

**Files:**
- Create: `backend/app/services/points_rules.py`
- Modify: 在 meals/water/workouts 写成功后调用 `evaluate_daily_points(user_id, date)`（避免漏发）
- Create: `backend/app/routers/points.py`（`GET /api/points/balance`，`GET /api/points/ledger`，`POST /api/points/evaluate` 手动补评）
- Create: `backend/tests/test_points_rules.py`

**Interfaces:**
- `evaluate_daily_points(db, user_id: str, day: date) -> dict`  
  用 P1 `week_rules.day_status`；若 `level==full` 则  
  `grant(..., key=f"{user_id}:{day.isoformat()}:daily_all_three", delta=10)`
- `evaluate_weekly_points(db, user_id: str, week_start: date) -> dict`  
  对 Mon..Sun 七天均 `level==full` 则  
  `grant(..., key=f"{user_id}:{week_start.isoformat()}:weekly_plan_complete", delta=50)`

分值从 settings 读取：

```yaml
# config.yaml app.points
daily_all_three: 10
weekly_plan_complete: 50
```

- [ ] **Step 1: 测试全日三项后余额 +10，重复调用不变**

```python
def test_daily_all_three_points(client, auth_header):
    # 造满三项记录（复用 API）后：
    r = client.post("/api/points/evaluate", headers=auth_header, json={"date": "2026-10-08"})
    assert r.status_code == 200
    bal = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal >= 10
    client.post("/api/points/evaluate", headers=auth_header, json={"date": "2026-10-08"})
    bal2 = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal2 == bal
```

- [ ] **Step 2: 实现 hooks + router → PASS → Commit**

```bash
git commit -m "feat: auto-grant points for daily and weekly completion"
```

---

### Task 3: Goals API 与进度刷新

**Files:**
- Modify: `backend/app/models.py`（Goal）
- Create: `backend/app/services/goals_progress.py`
- Create: `backend/app/routers/goals.py`
- Create: `backend/tests/test_goals.py`

**Interfaces:**
- Model Goal: id, user_id, kind (`short`|`long`), title, description, metric (`weight_kg`|`workout_days`|`custom`), target_value (float), current_value (float), unit (str), start_date, end_date (nullable), status (`active`|`done`|`cancelled`), created_at
- `POST /api/goals` 创建本人目标
- `GET /api/goals?scope=mine|all`（all=双方只读）
- `PATCH /api/goals/{id}` 本人改标题/目标值/状态
- `POST /api/goals/{id}/refresh` 按 metric 重算 current_value：
  - `weight_kg`: 取该用户最新 BodyMetric.weight_kg；进度方向「越接近 target 越好」——若 target < 起始，则 current 用最新体重
  - `workout_days`: 统计 `[start_date, end_date or today]` 内 `workout_done` 为 true 的天数
  - `custom`: 不自动算，仅允许 PATCH current_value
- 当 `metric==weight_kg` 且最新体重达到目标（减重：`latest <= target`；增重：`latest >= target`；用创建时 body 快照 `baseline_weight` 存 meta）：标记 `status=done` 并可额外 `grant` 奖励分（可选，默认 +20，key=`goal_done:{goal_id}`）

```python
def weight_goal_reached(baseline: float, target: float, latest: float) -> bool:
    if target <= baseline:  # 减重
        return latest <= target
    return latest >= target
```

- [ ] **Step 1: 测试创建短目标与 refresh**

```python
def test_create_weight_goal_and_refresh(client, auth_header):
    client.post("/api/body", headers=auth_header, json={
        "recorded_on": "2026-10-01", "weight_kg": 70, "height_cm": 175,
        "waist_cm": 80, "body_fat_pct": 18, "chest_cm": 95, "hip_cm": 96, "note": "",
    })
    g = client.post("/api/goals", headers=auth_header, json={
        "kind": "short",
        "title": "两周到68",
        "metric": "weight_kg",
        "target_value": 68,
        "unit": "kg",
        "start_date": "2026-10-01",
        "end_date": "2026-10-15",
    }).json()
    client.post("/api/body", headers=auth_header, json={
        "recorded_on": "2026-10-08", "weight_kg": 68, "height_cm": 175,
        "waist_cm": 79, "body_fat_pct": 17, "chest_cm": 95, "hip_cm": 95, "note": "",
    })
    r = client.post(f"/api/goals/{g['id']}/refresh", headers=auth_header)
    assert r.json()["current_value"] == 68
    assert r.json()["status"] == "done"
```

- [ ] **Step 2: 实现 → PASS → Commit**

```bash
git commit -m "feat: add short/long goals with progress refresh"
```

---

### Task 4: 奖励清单与兑奖

**Files:**
- Modify: `backend/app/models.py`（Reward, Redemption）
- Create: `backend/app/routers/rewards.py`
- Create: `backend/tests/test_rewards.py`

**Interfaces:**
- Reward: id, creator_user_id, title, description, is_private (bool), scale_level (int 1–5), cost_note (str), points_price (int), active (bool)
- Redemption: id, reward_id, redeemer_user_id, points_spent, status (`pending`|`fulfilled`|`cancelled`), created_at, fulfilled_at
- `GET /api/rewards` 双方可见列表；`is_private` 为 true 时响应 `description` 默认返回 `null`，另有 `POST /api/rewards/{id}/reveal` 返回完整 description（需登录即可，私用双人）
- `POST /api/rewards` 创建
- `PATCH /api/rewards/{id}` 创建者更新
- `POST /api/rewards/{id}/redeem`：  
  1. 查 balance ≥ price  
  2. `grant(delta=-price, reason="redeem", key=f"redeem:{user_id}:{uuid}")`（每次兑奖新 key）  
  3. 建 Redemption pending  
  余额不足 → 400
- `PATCH /api/redemptions/{id}` `{status: "fulfilled"|"cancelled"}`：双方任一可操作；`cancelled` 且原 pending 则退回积分（`grant` 正分，key=`redeem_refund:{redemption_id}`）

- [ ] **Step 1: 测试兑奖扣分与余额不足**

```python
def test_redeem_insufficient(client, auth_header):
    rw = client.post("/api/rewards", headers=auth_header, json={
        "title": "火锅",
        "description": "双人火锅一次",
        "is_private": False,
        "scale_level": 2,
        "cost_note": "约200元",
        "points_price": 100,
    }).json()
    r = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert r.status_code == 400

def test_redeem_ok(client, auth_header, db_session):
    from backend.app.services.points import grant
    grant(db_session, "dragon", 100, "test", "dragon:test:topup")
    rw = client.post("/api/rewards", headers=auth_header, json={
        "title": "按摩",
        "description": "肩颈按摩",
        "is_private": True,
        "scale_level": 3,
        "cost_note": "私密",
        "points_price": 30,
    }).json()
    listed = client.get("/api/rewards", headers=auth_header).json()
    private_item = next(x for x in listed if x["id"] == rw["id"])
    assert private_item["description"] is None
    r = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert r.status_code == 200
    bal = client.get("/api/points/balance", headers=auth_header).json()["balance"]
    assert bal == 70
```

- [ ] **Step 2: 实现 → PASS → Commit**

```bash
git commit -m "feat: add private-capable rewards and redemption flow"
```

---

### Task 5: 前端目标 Tab

**Files:**
- Create: `frontend/src/views/GoalsView.vue`
- Create: `frontend/src/components/GoalCard.vue`
- Create: `frontend/src/components/RewardList.vue`
- Create: `frontend/src/components/RewardForm.vue`
- Create: `frontend/src/components/PointsBadge.vue`
- Create: `frontend/src/api/goals.ts`, `rewards.ts`, `points.ts`
- Modify: `TabLayout` 目标 Tab 接真页面

**UI 结构（单页分块，非多 Tab 嵌套）：**
1. 顶栏 `PointsBadge` 显示余额 + 入口查看流水（van-action-sheet 列表 ledger）
2. 「目标」：短/长期分组；显示对方目标只读；本人可新建/refresh
3. 「奖励」：卡片列表；私密项显示锁图标，点「查看」调用 reveal；「兑换」按钮；「我的兑奖」pending/fulfilled

- [ ] **Step 1: 实现页面与 API 封装**
- [ ] **Step 2: 手测 — 凑全日三项见余额增加 → 建奖励 → 兑换 → 标记兑现**
- [ ] **Step 3: P2 验收清单**
  - [ ] 双方可见彼此目标
  - [ ] 全日三项只加一次分
  - [ ] 私密奖励默认隐藏详情
  - [ ] 兑奖扣分、取消退分、兑现状态可改
- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add goals tab with points and rewards UI"
```

---

## Self-review (author)

**Spec P2:** 短长期目标 ✅；积分与周/日联动 ✅；奖励自定义/私密/尺度积分价 ✅；兑奖状态 ✅。

**Idempotency:** daily/weekly/goal_done/redeem_refund keys 写死格式，避免重复发分。

**Consistency:** `PointsLedger.delta` 整数；Reward.`points_price` > 0 校验在 schema。
