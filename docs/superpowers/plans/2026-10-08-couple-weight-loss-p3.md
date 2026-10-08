# 双人减 P3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付日终/周 AI 分析报告、减肥智能聊天、PushPlus 微信提醒（含绑定与失败可见）。

**Architecture:** APScheduler 挂在 FastAPI lifespan；报告写入 `ai_reports`；聊天写入 `chat_messages` 并在请求时注入该用户近 7 日摘要；PushPlus HTTP 推送，token 存 `push_bindings`。LLM 一律走扩展后的 `call_llm`（文本 `qwen3.8-27b`）。

**Tech Stack:** 同前；新增 `apscheduler`；PushPlus 用 `httpx`。

**Depends on:** P0（记录数据 + call_llm）；建议 P1 已有周规则摘要（聊天上下文更好）；PushPlus 与报告不强制依赖 P2。

**Spec:** `docs/superpowers/specs/2026-10-08-couple-weight-loss-design.md` §6.8 §6.9 §7 §8 P3

## Global Constraints

- 日终默认 22:00（config `app.schedule.daily_report_hour/minute`）；周报默认周一 00:30。
- LLM 失败：不覆盖已有报告；接口返回错误并允许「手动再生成」。
- 聊天页脚固定免责声明：「非医疗建议，不能替代医师诊断。」
- PushPlus：每人独立 token；仅向「有未完成项」的一方推送；失败记 `last_error`，不影响打卡。
- 不做微信公众号模板消息、不做企业微信。

---

## File Structure (P3)

```
backend/app/
  models.py                 # + AiReport, ChatMessage, PushBinding
  services/
    context_summary.py      # 近 N 日文本摘要
    daily_report.py
    weekly_report.py
    chat_coach.py
    pushplus.py
  scheduler.py              # APScheduler 注册
  routers/
    reports.py
    chat.py
    push.py
frontend/src/
  views/
    ReportView.vue
    ChatView.vue
    PushSettings.vue
  api/reports.ts, chat.ts, push.ts
backend/tests/
  test_context_summary.py
  test_daily_report_parse.py
  test_pushplus.py
  test_chat.py
scripts/
  smoke_daily_report.py
  smoke_pushplus.py
```

---

### Task 1: 用户近期摘要纯函数

**Files:**
- Create: `backend/app/services/context_summary.py`
- Create: `backend/tests/test_context_summary.py`

**Interfaces:**
- `build_user_day_blob(date: str, meals, water, workouts, done: dict) -> str`
- `build_user_range_summary(days: list[dict]) -> str` 供报告/聊天 system 附件

- [ ] **Step 1: 测试**

```python
from backend.app.services.context_summary import build_user_day_blob

def test_day_blob_contains_flags():
    text = build_user_day_blob(
        "2026-10-08",
        meals=[{"meal_type": "lunch", "user_kcal": 500, "food_summary": "面"}],
        water={"total_ml": 1200, "target_ml": 2000},
        workouts=[{"kind": "cardio", "payload": {"duration_min": 30, "cardio_type": "run"}}],
        done={"meal": False, "water": False, "workout": True},
    )
    assert "2026-10-08" in text
    assert "1200" in text
    assert "workout=True" in text or "运动完成" in text
```

- [ ] **Step 2: 实现简洁中文摘要 → PASS → Commit**

```bash
git commit -m "feat: add user daily context summary for LLM prompts"
```

---

### Task 2: 日终/周报生成服务与 API

**Files:**
- Modify: `backend/app/models.py`（AiReport: id, user_id, kind=`daily`|`weekly`, period_key 如 `2026-10-08` 或 `2026-W41`, content_md, created_at, unique(user_id, kind, period_key)）
- Create: `backend/app/services/daily_report.py`
- Create: `backend/app/services/weekly_report.py`
- Create: `backend/app/routers/reports.py`
- Create: `backend/tests/test_daily_report_parse.py`
- Create: `scripts/smoke_daily_report.py`

**Interfaces:**
- `generate_daily_report(db, user_id: str, day: date, *, force: bool=False) -> AiReport`  
  - 组装当日 + 本周已过天数摘要 → `call_llm` 文本  
  - system: 减肥教练，输出 Markdown 三段：今日小结 / 本周趋势 / 明日建议  
  - 若已有报告且 `force=False`：直接返回旧报告  
  - LLM 异常：抛 `ReportError`，不写空行覆盖
- `generate_weekly_report(db, user_id, week_start: date, force=False)` 同类
- `GET /api/reports?kind=daily&period=2026-10-08`
- `POST /api/reports/generate` `{kind, period, force?}`

- [ ] **Step 1: 不打 API 的解析/跳过逻辑测试**

```python
def test_skip_overwrite_without_force(db_session, monkeypatch):
    # 插入已有报告后 generate(force=False) 不得调用 llm
    calls = []
    monkeypatch.setattr("backend.app.services.daily_report.call_llm", lambda *a, **k: calls.append(1))
    ...
    assert calls == []
```

- [ ] **Step 2: 实现服务 + 路由；smoke 脚本对真实用户一天数据生成一次**

```bash
python scripts/smoke_daily_report.py --user dragon --date 2026-10-08
```

Expected: 打印 Markdown 非空；第二次无 force 不耗新调用（日志可见）。

- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add daily and weekly AI report generation"
```

---

### Task 3: 调度器

**Files:**
- Create: `backend/app/scheduler.py`
- Modify: `backend/app/main.py` lifespan 启动/关闭 scheduler
- Modify: `config` / settings：`daily_report_hour=22`, `daily_report_minute=0`, `weekly_report_weekday=0`（周一）, `weekly_report_hour=0`, `weekly_report_minute=30`, `reminder_hours=[12,21]`

**Interfaces:**
- Job `job_daily_reports`: 对 dragon/leaf 各 `generate_daily_report(today)`，吞掉单用户异常并 log
- Job `job_weekly_reports`: 对两用户生成上周周报（week_start = 本周一 - 7 天）
- Job `job_reminders`: 调用 Task 5 的 `run_reminders_now()`

```python
# lifespan 示意
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    sched = start_scheduler()
    yield
    sched.shutdown(wait=False)
```

- [ ] **Step 1: 单测 mock — `start_scheduler` 注册 3 个 job（查 job ids）**
- [ ] **Step 2: 实现 → PASS → Commit**

```bash
git commit -m "feat: schedule daily reports weekly reports and reminders"
```

---

### Task 4: 智能聊天

**Files:**
- Modify: `models.py`（ChatMessage: id, user_id, role=`user`|`assistant`, content, created_at）
- Create: `backend/app/services/chat_coach.py`
- Create: `backend/app/routers/chat.py`
- Create: `backend/tests/test_chat.py`

**Interfaces:**
- `POST /api/chat` `{message: str}` → `{reply: str}`  
  构造 messages：system（教练人设 + 免责 + `build_user_range_summary` 近 7 日）+ 最近 10 条历史 + 当前 user  
  用 `responses_chat_messages` 或 `call_llm`  
  落库 user + assistant 两条
- `GET /api/chat/history?limit=50`
- `DELETE /api/chat/history` 清空本人会话

- [ ] **Step 1: 测试 mock LLM**

```python
def test_chat_stores_two_messages(client, auth_header, monkeypatch):
    monkeypatch.setattr(
        "backend.app.services.chat_coach.call_llm",
        lambda *a, **k: type("R", (), {"text": "多喝水，继续记录。"})(),
    )
    r = client.post("/api/chat", headers=auth_header, json={"message": "今天有点饿怎么办"})
    assert r.status_code == 200
    assert "水" in r.json()["reply"]
    hist = client.get("/api/chat/history", headers=auth_header).json()
    assert len(hist["messages"]) >= 2
```

- [ ] **Step 2: 实现 → PASS → Commit**

```bash
git commit -m "feat: add couple diet coach chat with history"
```

---

### Task 5: PushPlus 绑定与提醒

**Files:**
- Modify: `models.py`（PushBinding: user_id PK, token, enabled, remind_hours_json 默认 `[12,21]`, last_success_at, last_error）
- Create: `backend/app/services/pushplus.py`
- Create: `backend/app/routers/push.py`
- Create: `backend/tests/test_pushplus.py`
- Create: `scripts/smoke_pushplus.py`

**Interfaces:**
- `send_pushplus(token: str, title: str, content: str) -> None`  
  POST `http://www.pushplus.plus/send` JSON `{"token", "title", "content"}`；非 200 或 code!=200 抛错
- `run_reminders_now(db, *, hour: int | None=None)`：  
  对每个 enabled binding，若当前小时在 remind_hours：检查今日 `day_status`，收集未完成项文案；若有未完成则推送；成功清 `last_error`，失败写 `last_error=str(e)[:500]`
- `GET/PUT /api/push/settings` 本人 token/enabled/remind_hours
- `POST /api/push/test` 发一条测试消息

- [ ] **Step 1: 单测 send 使用 httpx mock**

```python
def test_send_pushplus_ok(httpx_mock):
    httpx_mock.add_response(url="http://www.pushplus.plus/send", json={"code": 200})
    from backend.app.services.pushplus import send_pushplus
    send_pushplus("tok", "标题", "内容")

def test_reminder_skips_when_all_done(db_session, monkeypatch):
    monkeypatch.setattr("backend.app.services.pushplus.send_pushplus", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not send")))
    # 构造当日 full 状态与 binding enabled 后 run_reminders_now 不应发送
    ...
```

（若项目未用 pytest-httpx，改用 `monkeypatch` 拦截 `httpx.post`。）

- [ ] **Step 2: 实现 → PASS**
- [ ] **Step 3: smoke（可选真 token）**

```bash
python scripts/smoke_pushplus.py --token YOUR_TOKEN
```

- [ ] **Step 4: Commit**

```bash
git commit -m "feat: add PushPlus bindings and incomplete-day reminders"
```

---

### Task 6: 前端报告 / 聊天 / 推送设置

**Files:**
- Create: `frontend/src/views/ReportView.vue`
- Create: `frontend/src/views/ChatView.vue`
- Create: `frontend/src/views/PushSettings.vue`（或并入 MineView）
- Create: `frontend/src/api/reports.ts`, `chat.ts`, `push.ts`
- Modify: `MineView.vue` 增加入口：AI 报告、智能聊天、推送设置
- Modify: `TodayView.vue` 可显示「今日报告」入口（有则展示摘要卡）

**ChatView：** 气泡列表 + 输入框；底部固定免责声明小字。  
**ReportView：** 日/周切换；「重新生成」调 `force=true`。  
**PushSettings：** token 输入、开关、时段多选、测试按钮、展示 `last_error`。

- [ ] **Step 1: 实现三页并对接**
- [ ] **Step 2: P3 验收清单**
  - [ ] 手动生成日报告成功；失败时旧报告仍在
  - [ ] 聊天有上下文感知（问「我今天喝了多少」能结合数据或明确说看不到时的合理回答）
  - [ ] Push 测试消息能到微信（真 token）
  - [ ] 未完成项在提醒时刻会推（可调小时做手测）
  - [ ] 页脚免责声明可见
- [ ] **Step 3: Commit**

```bash
git commit -m "feat: add report chat and push settings UI"
```

---

### Task 7: 总 README 补全与端到端说明

**Files:**
- Modify: `README.md`

补充：
- APScheduler 需进程常驻（云主机部署注意）
- PushPlus 申请与绑定步骤链接：`https://www.pushplus.plus/`
- 配置项列表：`daily_report_hour`、`reminder_hours`、LLM key
- 分期完成状态表（P0–P3）

- [ ] **Step 1: 更新 README**
- [ ] **Step 2: Commit**

```bash
git commit -m "docs: document P3 scheduling reports chat and PushPlus"
```

---

## Self-review (author)

**Spec P3:** 日终/周报 ✅；聊天+免责 ✅；PushPlus ✅；失败不覆盖报告 ✅；提醒只推未完成方 ✅。

**No placeholders:** PushPlus URL、idempotent report keys、调度默认时刻均写死。

**Consistency:** `AiReport.period_key`、`PushBinding.user_id`、chat `role` 枚举与前端 API 一致。
