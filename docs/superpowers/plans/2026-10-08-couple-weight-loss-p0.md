# 双人减 P0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付可本机运行的情侣双人减肥 H5：固定账号登录、今日饮食（含 `qwen3.8-27b` 看图估卡）、饮水、运动卡片记录，数据存 SQLite。

**Architecture:** FastAPI 单进程提供 REST + 静态前端；SQLite 存业务数据；复用并扩展根目录 `call_llm.py` 支持 `image_url` 多模态消息；Vue3 + Vant 手机 H5 调用 API。P1–P3（日历、目标奖励、日周报/聊天/PushPlus）另开计划。

**Tech Stack:** Python 3.11+、FastAPI、SQLAlchemy 2、SQLite、PyJWT、openai SDK（经 call_llm）、Vue3、Vite、Vant4、Pinia、Vue Router、pytest

**Spec:** `docs/superpowers/specs/2026-10-08-couple-weight-loss-design.md`

## Global Constraints

- 仅两用户：`dragon`（🐉）、`leaf`（🍃）；无注册。
- LLM：`provider=maas`，默认 model=`qwen3.8-27b`；看图与文本同一模型。
- 估卡失败必须可手填 kcal；用户可覆盖 AI kcal。
- 不可改对方数据（写接口校验 `user_id == current_user`）。
- 样例图路径：`data/img/`（两张 jpg，用于估卡联调）。
- 不做微信小程序、不做多租户、不做支付。

---

## File Structure (P0)

```
jianfei/
├── call_llm.py                 # 现有；扩展多模态消息
├── config.yaml                 # llm + app 用户密码等
├── requirements.txt
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI app、挂载静态与路由
│   │   ├── settings.py         # 读 config.yaml / 环境变量
│   │   ├── db.py               # engine、SessionLocal、get_db
│   │   ├── models.py           # SQLAlchemy 表
│   │   ├── auth.py             # 登录、JWT、依赖 get_current_user
│   │   ├── schemas.py          # Pydantic 出入参
│   │   ├── completion.py       # 当日饮食/饮水/运动完成度纯函数
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── meals.py
│   │   │   ├── water.py
│   │   │   ├── workouts.py
│   │   │   ├── exercises.py
│   │   │   └── today.py
│   │   └── services/
│   │       ├── meal_ai.py      # 看图估卡
│   │       └── uploads.py      # 保存饮食照片
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_completion.py
│       ├── test_water.py
│       ├── test_workouts.py
│       └── test_meal_ai.py     # 可用 mock；另有手工联调步骤
├── frontend/                   # Vue3 + Vant H5
│   ├── package.json
│   ├── vite.config.ts
│   └── src/...
├── data/img/                   # 样例饮食图（已有）
├── uploads/meals/              # 运行时上传（gitignore）
└── scripts/
    └── seed_exercises.py       # 写入精选动作 + 中文名 + gif URL
```

---

### Task 1: 后端骨架、配置、数据库模型、完成度纯函数

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`（若不存在；含 llm 与 users，**勿提交真实 api_key**，用环境变量覆盖）
- Create: `backend/app/settings.py`
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/app/completion.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_completion.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: `get_settings() -> Settings`；`SessionLocal`；models `User`（seed 用）、`Meal`、`WaterEntry`、`Workout`、`Exercise`；`completion.meal_done(meals, rule) -> bool`、`water_done(ml, target) -> bool`、`workout_done(workouts, rule) -> bool`

- [ ] **Step 1: 写完成度失败测试**

```python
# backend/tests/test_completion.py
from backend.app.completion import meal_done, water_done, workout_done

def test_meal_done_requires_three_main_meals():
    meals = [
        {"meal_type": "breakfast"},
        {"meal_type": "lunch"},
    ]
    assert meal_done(meals, {"mode": "three_main"}) is False
    meals.append({"meal_type": "dinner"})
    assert meal_done(meals, {"mode": "three_main"}) is True

def test_water_done():
    assert water_done(1500, 2000) is False
    assert water_done(2000, 2000) is True

def test_workout_done_any():
    assert workout_done([], {"mode": "any"}) is False
    assert workout_done([{"kind": "cardio"}], {"mode": "any"}) is True
```

- [ ] **Step 2: 运行确认失败**

Run: `cd d:\Program\Private\jianfei && python -m pytest backend/tests/test_completion.py -v`  
Expected: FAIL（module not found / import error）

- [ ] **Step 3: 实现 `completion.py` 与包结构**

```python
# backend/app/completion.py
from __future__ import annotations

MAIN = {"breakfast", "lunch", "dinner"}

def meal_done(meals: list[dict], rule: dict | None = None) -> bool:
    rule = rule or {"mode": "three_main"}
    mode = rule.get("mode", "three_main")
    types = {m.get("meal_type") for m in meals}
    if mode == "any":
        return len(meals) >= 1
    return MAIN.issubset(types)

def water_done(total_ml: int, target_ml: int) -> bool:
    return int(total_ml) >= int(target_ml)

def workout_done(workouts: list[dict], rule: dict | None = None) -> bool:
    rule = rule or {"mode": "any"}
    if rule.get("mode", "any") == "any":
        return len(workouts) >= 1
    return len(workouts) >= 1
```

同时创建：`backend/app/__init__.py`（可空）、`requirements.txt`：

```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
sqlalchemy>=2.0.36
pydantic>=2.9.0
pydantic-settings>=2.6.0
pyjwt>=2.9.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.12
pyyaml>=6.0.2
openai>=1.50.0
httpx>=0.27.0
pytest>=8.3.0
pillow>=10.4.0
```

`.gitignore` 至少包含：`uploads/`、`*.db`、`.env`、`frontend/node_modules/`、`frontend/dist/`、`__pycache__/`、`config.local.yaml`

- [ ] **Step 4: 实现 settings / db / models**

`Settings` 字段：`database_url`（默认 `sqlite:///./data/jianfei.db`）、`jwt_secret`、`jwt_expire_hours=720`、`upload_dir=uploads/meals`、`users` 列表（id/password/display_name/default_water_ml）。从 `config.yaml` 的 `app` 段读取；`llm` 段仍由 `call_llm.load_config` 使用。

`models.py` 表（字段名固定，后续 Task 依赖）：

- `users`: id(str PK), display_name, password_hash, default_water_ml, role
- `meals`: id, user_id, date(YYYY-MM-DD), meal_type, image_path(nullable), food_summary, ai_kcal(nullable), user_kcal, advice, created_at
- `water_entries`: id, user_id, date, amount_ml, created_at
- `workouts`: id, user_id, date, kind(`cardio`|`strength`), payload(JSON 文本), created_at
- `exercises`: id, slug, name_zh, name_en, body_part, gif_url, instructions_zh, is_custom, owner_user_id(nullable)

启动时若不存在两用户则按 settings 插入（Task 2 auth 里做也可以，本 Task 在 `db.init_db()` 里 seed users）。

- [ ] **Step 5: 跑通完成度测试**

Run: `python -m pytest backend/tests/test_completion.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add requirements.txt .gitignore backend/app backend/tests/test_completion.py backend/tests/conftest.py
git commit -m "feat: add backend skeleton and daily completion helpers"
```

---

### Task 2: 登录与 JWT

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/schemas.py`（LoginRequest, TokenResponse, UserOut）
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/main.py`（最小挂载）
- Create: `backend/tests/test_auth.py`
- Modify: `backend/tests/conftest.py`（TestClient + 临时 SQLite）

**Interfaces:**
- Consumes: `User` model, `get_settings`, `get_db`
- Produces: `POST /api/auth/login` → `{access_token, token_type, user}`；依赖 `get_current_user() -> User`；密码用 passlib bcrypt 校验（seed 时对明文 hash）

- [ ] **Step 1: 写登录测试**

```python
def test_login_ok(client):
    r = client.post("/api/auth/login", json={"user_id": "dragon", "password": "dragon-pass"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["user"]["display_name"] == "🐉"

def test_login_bad_password(client):
    r = client.post("/api/auth/login", json={"user_id": "dragon", "password": "wrong"})
    assert r.status_code == 401

def test_me_requires_auth(client):
    assert client.get("/api/auth/me").status_code == 401
```

`conftest.py` 用临时文件 DB，settings 覆盖两用户密码为 `dragon-pass` / `leaf-pass`。

- [ ] **Step 2: 运行确认失败**

Run: `python -m pytest backend/tests/test_auth.py -v`  
Expected: FAIL

- [ ] **Step 3: 实现 auth 路由与 JWT**

```python
# 核心逻辑示意
def create_access_token(user_id: str) -> str: ...
def get_current_user(authorization: str | None = Header(None), db=Depends(get_db)) -> User: ...
```

`main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.db import init_db
from backend.app.routers import auth as auth_router

app = FastAPI(title="双人减")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(auth_router.router, prefix="/api/auth", tags=["auth"])

@app.on_event("startup")
def on_startup():
    init_db()
```

- [ ] **Step 4: 测试通过**

Run: `python -m pytest backend/tests/test_auth.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app backend/tests
git commit -m "feat: add fixed dual-account login with JWT"
```

---

### Task 3: 扩展 `call_llm.py` 支持看图 + 饮食估卡服务

**Files:**
- Modify: `call_llm.py`（增加 `responses_chat_messages` / 或让 `responses_chat` 接受 `messages` 列表）
- Create: `backend/app/services/meal_ai.py`
- Create: `backend/tests/test_meal_ai_parse.py`
- Create: `scripts/smoke_meal_vision.py`（对 `data/img` 真机联调，非 CI 强制）

**Interfaces:**
- Produces: `call_llm.responses_chat_messages(messages: list[dict], cfg=None, **kwargs) -> LLMResult`
- Produces: `meal_ai.estimate_calories_from_image(path: Path) -> dict` 返回  
  `{"food_summary": str, "kcal": int, "advice": str}`  
  解析失败抛 `MealAIError`

- [ ] **Step 1: 写 JSON 解析单测（不打真实 API）**

```python
# backend/tests/test_meal_ai_parse.py
from backend.app.services.meal_ai import parse_estimate_json

def test_parse_estimate_json_ok():
    raw = '{"food_summary":"鸡胸肉沙拉","kcal":420,"advice":"蛋白质不错，少酱料"}'
    d = parse_estimate_json(raw)
    assert d["kcal"] == 420
    assert "鸡胸" in d["food_summary"]

def test_parse_estimate_json_embedded():
    raw = '好的\n{"food_summary":"米饭","kcal":300,"advice":"控量"}\n'
    assert parse_estimate_json(raw)["kcal"] == 300
```

- [ ] **Step 2: 运行确认失败 → 实现 parse + 调用封装**

`estimate_calories_from_image`：把图片读成 base64，构造：

```python
messages = [
  {"role": "system", "content": "你是饮食热量估算助手。只输出 JSON：food_summary,kcal,advice。kcal 为整数。不要 markdown。"},
  {"role": "user", "content": [
      {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
      {"type": "text", "text": "估算这餐大概卡路里，并给一句简短建议。"},
  ]},
]
```

调用扩展后的 `responses_chat_messages`（model 来自 config，默认 `qwen3.8-27b`）。

在 `call_llm.py` 增加：

```python
def responses_chat_messages(
    messages: list[dict[str, Any]],
    cfg: dict | None = None,
    *,
    enable_thinking: bool = False,
    **kwargs: Any,
) -> LLMResult:
    """非流式；messages 可为多模态 content 列表。"""
    # 与 responses_chat 相同 client 调用，但直接使用传入 messages
    ...
```

- [ ] **Step 3: 解析单测 PASS**

Run: `python -m pytest backend/tests/test_meal_ai_parse.py -v`  
Expected: PASS

- [ ] **Step 4: 手工烟测（需有效 DASHSCOPE/config api_key）**

```bash
python scripts/smoke_meal_vision.py
```

脚本对 `data/img` 下每张图调用 `estimate_calories_from_image`，打印 JSON。  
Expected: 每张图打印含 `kcal` 的 dict；若无 key 则跳过本步并在 README 注明，但代码路径保留。

- [ ] **Step 5: Commit**

```bash
git add call_llm.py backend/app/services/meal_ai.py backend/tests/test_meal_ai_parse.py scripts/smoke_meal_vision.py
git commit -m "feat: add vision calorie estimate via qwen VL messages"
```

---

### Task 4: 饮食 API（上传、估卡、保存、列表）

**Files:**
- Create: `backend/app/services/uploads.py`
- Create: `backend/app/routers/meals.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_meals.py`

**Interfaces:**
- `POST /api/meals/estimate` multipart `file` → `{food_summary, kcal, advice}`（不落库也可先落临时文件）
- `POST /api/meals` JSON：`date, meal_type, food_summary, ai_kcal?, user_kcal, advice?, image_path?` 或 multipart 一次保存
- `GET /api/meals?date=YYYY-MM-DD` 仅当前用户
- `PATCH /api/meals/{id}` 可改 `user_kcal` / summary（仅本人）

推荐实现：先 `estimate` 再 `create`（带 image_path）；`uploads.save_meal_image(file, user_id) -> relative_path`，限制 5MB，可用 Pillow 压到最长边 1280。

- [ ] **Step 1: 写 API 测试（估卡 mock）**

```python
def test_create_meal_and_list(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.routers.meals.estimate_calories_from_image",
        lambda path: {"food_summary": "测试餐", "kcal": 500, "advice": "ok"},
    )
    # 若 create 不强制估卡：直接 POST JSON
    r = client.post("/api/meals", headers=auth_header, json={
        "date": "2026-10-08",
        "meal_type": "lunch",
        "food_summary": "测试餐",
        "ai_kcal": 500,
        "user_kcal": 480,
        "advice": "ok",
    })
    assert r.status_code == 200
    listed = client.get("/api/meals", headers=auth_header, params={"date": "2026-10-08"})
    assert len(listed.json()) == 1
    assert listed.json()[0]["user_kcal"] == 480
```

- [ ] **Step 2: 实现路由 → 测试 PASS → Commit**

```bash
git commit -m "feat: add meal create/list with editable kcal"
```

---

### Task 5: 饮水 API

**Files:**
- Create: `backend/app/routers/water.py`
- Modify: `backend/app/main.py`, `schemas.py`
- Create: `backend/tests/test_water.py`

**Interfaces:**
- `GET /api/water?date=` → `{target_ml, total_ml, entries: [...]}`；target = user.default_water_ml（P1 再接周计划覆盖）
- `POST /api/water` `{date, amount_ml}`
- `PATCH /api/water/{id}` `{amount_ml}`
- `DELETE /api/water/{id}`

- [ ] **Step 1: 测试加减删**

```python
def test_water_add_and_total(client, auth_header):
    client.post("/api/water", headers=auth_header, json={"date": "2026-10-08", "amount_ml": 250})
    client.post("/api/water", headers=auth_header, json={"date": "2026-10-08", "amount_ml": 500})
    r = client.get("/api/water", headers=auth_header, params={"date": "2026-10-08"})
    assert r.json()["total_ml"] == 750
```

- [ ] **Step 2: 实现 → PASS → Commit**

```bash
git commit -m "feat: add water intake entries API"
```

---

### Task 6: 动作库种子 + 运动 API

**Files:**
- Create: `scripts/seed_exercises.py`
- Create: `backend/app/routers/exercises.py`
- Create: `backend/app/routers/workouts.py`
- Create: `backend/tests/test_workouts.py`
- Create: `backend/data/exercises_seed.json`（精选 20–40 个：常见有氧类型不进 exercises 表也可硬编码；力量动作含 name_zh/gif_url）

**Interfaces:**
- `GET /api/exercises?body_part=`
- `POST /api/exercises` 自定义（当前用户）
- `POST /api/workouts`  
  - cardio: `{date, kind:"cardio", cardio_type, duration_min, intensity?}`  
  - strength: `{date, kind:"strength", body_part, exercise_id?, exercise_name, sets:[{reps, weight?}]}`  
  存入 `workouts.payload` JSON
- `GET /api/workouts?date=`
- `DELETE /api/workouts/{id}`

GIF base（写入 seed）：  
`https://cdn.jsdelivr.net/gh/JahelCuadrado/ExerciseGymGifsDB@v1.1.0/{muscle}/{slug}.gif`

有氧类型前端写死列表：`run, walk, cycle, rope, elliptical, other`（中文标签在前端）。

- [ ] **Step 1: 测试创建力量训练并列表**

```python
def test_strength_workout(client, auth_header):
    r = client.post("/api/workouts", headers=auth_header, json={
        "date": "2026-10-08",
        "kind": "strength",
        "body_part": "chest",
        "exercise_name": "杠铃卧推",
        "sets": [{"reps": 10}, {"reps": 8}],
    })
    assert r.status_code == 200
    listed = client.get("/api/workouts", headers=auth_header, params={"date": "2026-10-08"})
    assert listed.json()[0]["kind"] == "strength"
```

- [ ] **Step 2: seed 脚本 + 路由实现 → PASS → Commit**

```bash
git commit -m "feat: add exercise catalog and workout logging API"
```

---

### Task 7: 今日汇总 API

**Files:**
- Create: `backend/app/routers/today.py`
- Create: `backend/tests/test_today.py`

**Interfaces:**
- `GET /api/today?date=` → 当前用户详细 + 对方摘要：

```json
{
  "date": "2026-10-08",
  "me": {
    "user_id": "dragon",
    "meals": [...],
    "water": {"total_ml": 0, "target_ml": 2000, "done": false},
    "workouts": [...],
    "done": {"meal": false, "water": false, "workout": false}
  },
  "partner": {
    "user_id": "leaf",
    "display_name": "🍃",
    "done": {"meal": false, "water": false, "workout": false},
    "water_total_ml": 0,
    "water_target_ml": 2000
  }
}
```

用 Task 1 的 `completion.*`。对方只返回摘要，不含对方餐图详情列表（P0 可只返回 done 标志）。

- [ ] **Step 1: 测试双方摘要字段存在 → 实现 → PASS → Commit**

```bash
git commit -m "feat: add today summary API for self and partner"
```

---

### Task 8: 前端脚手架 + 登录

**Files:**
- Create: `frontend/`（`npm create` vue-ts 或手动最小 Vite Vue3；依赖 `vue-router` `pinia` `vant` `axios`）
- Create: `frontend/src/api/http.ts`（axios baseURL `/api`，拦截器带 Bearer）
- Create: `frontend/src/stores/auth.ts`
- Create: `frontend/src/views/LoginView.vue`
- Create: `frontend/src/router/index.ts`
- Modify: `backend/app/main.py`（开发期 CORS 已开；生产挂载 `frontend/dist`）

**Interfaces:**
- 登录页两个大按钮/卡片：🐉 / 🍃，输入密码 → `POST /api/auth/login` → 存 token → 进 `/today`

- [ ] **Step 1: 初始化 frontend**

```bash
cd frontend
npm create vite@latest . -- --template vue-ts
npm i vue-router pinia vant axios
```

按 Vant 文档配置按需引入或全量引入（P0 全量可接受）。

- [ ] **Step 2: 实现 LoginView + auth store + 路由守卫**

未登录访问业务页 → 重定向 `/login`。

- [ ] **Step 3: 手动验证**

Run backend: `uvicorn backend.app.main:app --reload --port 8000`  
Run frontend: `npm run dev`（vite proxy `/api` → `http://127.0.0.1:8000`）  
Expected: 可用 `dragon` / `dragon-pass` 登录进入空白今日页壳子。

- [ ] **Step 4: Commit**

```bash
git add frontend backend/app/main.py
git commit -m "feat: add Vue H5 login shell with Vant"
```

---

### Task 9: 前端今日页 — 饮水 + 饮食

**Files:**
- Create: `frontend/src/views/TodayView.vue`
- Create: `frontend/src/components/WaterPanel.vue`
- Create: `frontend/src/components/MealPanel.vue`
- Create: `frontend/src/api/today.ts`, `meals.ts`, `water.ts`

**行为：**
- 顶栏：日期 + 对方 `done` 三点摘要
- 饮水：显示 total/target；按钮 +100/+200/+250/+500；列表可改删
- 饮食：四餐卡片；点餐 → 选图 → 调 `estimate`（或先上传再估）→ 展示 AI 结果 → 可改 kcal → 保存；无图可手填

样例联调：开发时也可从本机选 `data/img` 里的图上传。

- [ ] **Step 1: 实现组件并对接 API**
- [ ] **Step 2: 浏览器手测饮水累加与一餐保存**
- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add today water and meal panels"
```

---

### Task 10: 前端运动全屏页

**Files:**
- Create: `frontend/src/views/WorkoutView.vue`
- Create: `frontend/src/components/CardioForm.vue`
- Create: `frontend/src/components/StrengthPicker.vue`
- Create: `frontend/src/api/workouts.ts`, `exercises.ts`

**行为：**
- 今日页「去记录」→ `/workout?date=`
- 有氧：类型卡片 → 时长 stepper → 保存
- 力量：部位 → 动作卡（`img` 显示 gif_url + name_zh + 一句话）→ 组数/次数 → 保存；可继续加动作
- 返回今日显示运动摘要

- [ ] **Step 1: 先跑 `python scripts/seed_exercises.py` 确保库非空**
- [ ] **Step 2: 实现页面 → 手测一条有氧+一条力量**
- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add card-based workout logging UI"
```

---

### Task 11: 底部导航壳 + README 运行说明 + P0 验收

**Files:**
- Create: `frontend/src/layouts/TabLayout.vue`（今日高亮；日历/日志/目标 Tab 可占位「P1/P2」灰态或简单敬请期待）
- Create: `README.md`
- Modify: `backend/app/main.py` 可选挂载静态：若 `frontend/dist` 存在则 `StaticFiles`

**README 必须包含：**
1. 复制 `config.example.yaml` → `config.yaml`，填 `llm.api_key` 或设 `DASHSCOPE_API_KEY`
2. `pip install -r requirements.txt`
3. `python scripts/seed_exercises.py`
4. `uvicorn backend.app.main:app --reload --port 8000`
5. `cd frontend && npm i && npm run dev`
6. 默认密码说明（仅本地，要求用户立即修改 config）
7. `python scripts/smoke_meal_vision.py` 用 `data/img` 测估卡

- [ ] **Step 1: 写 README + Tab 壳**
- [ ] **Step 2: P0 验收清单（全部勾上才算完）**
  - [ ] 🐉 与 🍃 分别登录成功
  - [ ] 各完成：至少 1 餐（含改 kcal）、饮水多笔、1 次运动
  - [ ] `data/img` 图估卡返回 JSON 且可改数保存
  - [ ] 无法用 A 账号改 B 的 water/meal（测 PATCH 返回 403/404）
- [ ] **Step 3: Commit**

```bash
git commit -m "docs: add P0 runbook and tab shell placeholders"
```

---

## Follow-up plans

| 计划 | 文件 |
|------|------|
| P1 | `docs/superpowers/plans/2026-10-08-couple-weight-loss-p1.md` |
| P2 | `docs/superpowers/plans/2026-10-08-couple-weight-loss-p2.md` |
| P3 | `docs/superpowers/plans/2026-10-08-couple-weight-loss-p3.md` |
| 总索引 | `docs/superpowers/plans/README.md` |

---

## Self-review (author)

**Spec coverage (P0):** 登录双账号 ✅；饮食拍照估卡可改 ✅；饮水 ✅；运动卡片+GIF ✅；SQLite ✅；`data/img` 联调 ✅；不可改对方 ✅。P1–P3 明确外置。

**Placeholders:** 无 TBD；密码示例仅测试/README。

**Type consistency:** `meal_type` 取值 `breakfast|lunch|dinner|snack`；`kind` `cardio|strength`；用户 id `dragon|leaf` 贯穿。
