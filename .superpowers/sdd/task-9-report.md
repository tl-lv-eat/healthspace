# Task 9 Report: 今日页饮水 + 饮食

**Status:** Complete  
**Date:** 2026-10-08

## Deliverables

| File | Change |
|------|--------|
| `frontend/src/api/today.ts` | `GET /today` types + 日期工具 |
| `frontend/src/api/water.ts` | 饮水 CRUD |
| `frontend/src/api/meals.ts` | 饮食列表 / estimate / create / patch |
| `frontend/src/components/WaterPanel.vue` | 目标与快捷加水、条目改删 |
| `frontend/src/components/MealPanel.vue` | 四餐卡片、选图估卡、失败手填、手填保存 |
| `frontend/src/views/TodayView.vue` | 顶栏日期、对方 done 摘要、整合两面板 |

## Verification

```text
cd frontend && npm run build  → OK
```

浏览器手测饮水累加与一餐保存：**未在本会话执行**（需 backend + dev/proxy）。

## Commit

`feat: add today water and meal panels`

## Interface checklist

- [x] 顶栏日期 + 对方饮食/饮水/运动 done 摘要
- [x] 饮水 total/target、+100/+200/+250/+500、列表改删
- [x] 四餐选图 → `/meals/estimate` → 可改 kcal → `POST /meals`
- [x] `estimate_failed` + `image_path` 手填保存
- [x] 无图手填入口
