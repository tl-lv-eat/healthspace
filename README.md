# 双人减

情侣双人减肥/健康记录 H5（Vue3 + FastAPI + SQLite）。P0 覆盖登录、今日饮食/饮水/运动；日历/日志/目标 Tab 为 P1/P2 占位。

## 本地运行

### 1. 配置

```bash
cp config.example.yaml config.yaml
```

在 `config.yaml` 中填写 `llm.api_key`，或设置环境变量 `DASHSCOPE_API_KEY`（二选一即可）。

**默认本地测试账号（仅开发用，部署前请改 `config.yaml` 中的密码与 `jwt_secret`）：**

| 用户 id | 展示名 | 示例密码（见 config.example.yaml） |
|---------|--------|-----------------------------------|
| `dragon` | 🐉 | `dragon-pass` |
| `leaf` | 🍃 | `leaf-pass` |

### 2. 后端依赖与数据

```bash
pip install -r requirements.txt
python scripts/seed_exercises.py
```

### 3. 启动 API

```bash
uvicorn backend.app.main:app --reload --port 8000
```

若已构建前端（`frontend/dist` 存在），同一进程会挂载静态资源，浏览器访问 `http://127.0.0.1:8000/` 即可。

### 4. 前端开发

```bash
cd frontend
npm i
npm run dev
```

开发时 Vite 代理 `/api` 到 `8000`（见 `frontend/vite.config.ts`）。

### 5. 饮食看图估卡联调（可选）

需有效 LLM API Key：

```bash
python scripts/smoke_meal_vision.py
```

脚本使用仓库内 `data/img` 样例图，验证估卡 JSON 与保存流程。

## P0 验收要点

- 🐉 / 🍃 分别登录
- 各至少 1 餐（可改 kcal）、多笔饮水、1 次运动
- `data/img` 估卡可改数保存
- 无法用 A 账号修改 B 的 meal/water（API 返回 403/404）

自动化：`pytest backend/tests`；前端：`cd frontend && npm run build`。
