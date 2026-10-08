# Task 11 Report — 底部导航壳 + README + P0 验收

**Status:** Done  
**Commit:** `docs: add P0 runbook and tab shell placeholders`

## Delivered

- `frontend/src/layouts/TabLayout.vue` — 五 Tab（今日/日历/日志/目标/我的）；`/workout` 仍全屏无 Tab
- `PlaceholderTabView.vue` — 日历、日志 P1；目标 P2「敬请期待」
- `MineView.vue` — 账号信息 + 退出登录
- `README.md` — config、pip、seed、uvicorn、npm、默认密码、smoke_meal_vision
- `backend/app/main.py` — 已有 `frontend/dist` 静态挂载（未改）

## Automated verification

| Check | Result |
|-------|--------|
| `pytest backend/tests` | ✅ 28 passed |
| `npm run build` | ✅ pass |
| `smoke_meal_vision.py` | ⏭ skipped（无有效 `llm.api_key` / `DASHSCOPE_API_KEY`） |

## P0 acceptance checklist

| Item | Result |
|------|--------|
| 🐉 与 🍃 分别登录成功 | ☐ 未做浏览器手测（`test_login_ok` 等 API 测通过） |
| 各完成 1 餐（改 kcal）、饮水多笔、1 次运动 | ☐ 未做浏览器手测 |
| `data/img` 估卡 JSON 可改数保存 | ☐ 未跑 smoke（无 API Key） |
| A 不能改 B 的 water/meal | ✅ `test_cannot_patch_other_users_*` 等 |
