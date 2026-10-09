# 健康space🐉🍃

情侣健康记录 H5（Vue3 + FastAPI + SQLite）。原名「双人减」。

## 分期状态

| 阶段 | 内容 |
|------|------|
| P0 | 登录、今日饮食/饮水/运动、看图估卡 |
| P1 | 日历、周计划、身体数据、日志 |
| P2 | 积分、目标、奖励 |
| P3 | 日终/周报 AI、智能聊天、PushPlus 提醒与 APScheduler |

## 本地运行

### 1. 配置

```bash
cp config.example.yaml config.yaml
```

在 `config.yaml` 中填写 `llm.api_key`，或设置环境变量 `DASHSCOPE_API_KEY`（二选一即可）。

**App 常用配置（`app` 段）：**

- `jwt_secret`、`database_url`、`upload_dir`
- `schedule.daily_report_hour` / `daily_report_minute` — 日终报告默认 **22:00**
- `schedule.weekly_report_weekday`（0=周一）、`weekly_report_hour`、`weekly_report_minute` — 周报默认 **周一 00:30**
- `schedule.reminder_hours` — PushPlus 未完成项提醒小时，默认 `[12, 21]`

**默认本地测试账号（仅开发用，部署前请改密码与 `jwt_secret`）：**

| 用户 id | 展示名 | 示例密码（见 config.example.yaml） |
|---------|--------|-----------------------------------|
| `dragon` | 龙龙（🐉） | `dragon-pass`（仅兼容旧 login；入口已改为无密码选人） |
| `leaf` | 孙孙（🍃） | `leaf-pass` |

### 2. 后端依赖与数据

```bash
pip install -r requirements.txt
python scripts/seed_exercises.py
```

### 3. 启动 API

```bash
uvicorn backend.app.main:app --reload --port 8000
```

进程需**常驻**时，APScheduler 才会在配置时刻自动生成报告与发送提醒（云主机 / systemd / Docker 部署请注意，不要只用一次性命令）。

若已构建前端（`frontend/dist` 存在），同一进程会挂载静态资源，浏览器访问 `http://127.0.0.1:8000/` 即可。

测试环境可设 `DISABLE_SCHEDULER=1` 关闭调度器。

### 4. 前端开发

```bash
cd frontend
npm i
npm run dev
```

开发时 Vite 代理 `/api` 到 `8000`（见 `frontend/vite.config.ts`）。

### 5. 可选联调脚本

需有效 LLM API Key：

```bash
python scripts/smoke_meal_vision.py
python scripts/smoke_daily_report.py --user dragon --date 2026-10-08
```

PushPlus（微信）测试：

1. 在 [PushPlus](https://www.pushplus.plus/) 注册并获取 **token**，扫码绑定微信。
2. App「我的 → 推送设置」填入 token，或：`python scripts/smoke_pushplus.py --token YOUR_TOKEN`

### 6. P3 功能入口

- **我的**：AI 报告、智能聊天、推送设置
- **今日**：若已有当日日报告，显示摘要卡片
- 聊天页脚固定免责声明：「非医疗建议，不能替代医师诊断。」

## 验收与自动化

- P0：双人分别打卡、估卡、权限隔离
- P3：手动生成报告（失败不覆盖旧报告）、聊天带近 7 日上下文、Push 仅对未完成项提醒

```bash
set PYTHONPATH=.   # Windows；Linux/macOS: export PYTHONPATH=.
pytest backend/tests
cd frontend && npm run build
```
