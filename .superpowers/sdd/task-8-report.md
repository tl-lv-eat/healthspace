# Task 8 Report: CalendarView month history by role

## Status
**Complete**

## Summary
Calendar month view now loads plans with `listWeekPlans(\`${year}-${month padded}\`)` whenever the month grid loads or changes. Plans are listed in two sections (🐉 龙龙 / 🍃 叶子), sorted by start date descending. Cards show title (or「未命名计划」), date range, water, period deficit, and optional daily kcal cap. Each section’s「+ 新建」opens `WeekPlanEditor` with `initialTargetUserId` pre-set; create flow still shows persona chips. Month grid unchanged — `CoupleDayCell` color levels only.

## Files changed
- `frontend/src/views/CalendarView.vue` — month-scoped list, persona grouping, enriched cards, `initialTargetUserId` wiring

## Verification
```text
cd frontend && npm run build   → vue-tsc + vite OK
```

Manual smoke (recommended): 日历 → switch months → Network `GET /week-plans?list=true&month=YYYY-MM`. Tap section「+ 新建」→ editor opens with matching persona selected. Save plan overlapping month → appears under correct role group with title/range/water/deficit/cap.

## Commit
```
feat: calendar month plans grouped by persona
```

## Concerns / follow-ups
- Empty month shows one global hint plus per-persona empty lines; acceptable but slightly redundant when both lists are empty.
- Plans are filtered server-side by month overlap; client only groups by `user_id` — unknown ids would not appear in either column (only `dragon` / `leaf` expected).
- `weekProgress` banner at top remains viewer-centric from calendar API, not split by persona (unchanged from prior behavior).
