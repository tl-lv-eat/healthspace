# 计划 · 日历 · 今日联动（角色计划 + 双栏日详情）

**Status:** approved for planning  
**Date:** 2026-10-08  
**Approach:** 薄改现有页（日历 / 今日 / 计划 API 扩展），不新开计划 Tab、不另做只读回放页。

## 背景

用户希望：

1. 日历下方「我的计划」先选角色再建计划，并能看到本月历史。
2. 计划内容更丰富（标题、备注、日摄入上限等）。
3. 月历色块按角色绑定，只表达单日达标程度（饮水 + 热量是否盈余）。
4. 点进某日看到与「今日」相似的详细记账（餐、饮水时间、运动、达标），双栏展示两人。
5. 周/区间计划变更后，今日页目标与统计随日期变化；今日增加摄入 / 消耗 / 基础代谢；BMR 在「我的」里设置。

## 已锁定的产品选择

| 主题 | 选择 |
|------|------|
| 月历格子 | 双人半格 **只上色**（不堆数字） |
| 日详情 | **今日同款结构 + 双栏**（窄屏上下堆叠） |
| 计划归属 | 登录 **任一方** 都可为龙龙 / 叶子创建与编辑 |
| 计划新增字段（一期） | **标题 + 备注**、**日摄入上限** |
| 今日能量区 | **默认折叠**的「能量账本」 |
| 实现策略 | 薄改现有路由与组件，复用今日面板 |

一期不做：自定义打卡清单、标签筛选、餐次/运动规则细化 UI（模型里可保留旧 `meal_mode` / `workout_mode` 默认值）。

## 数据模型

### WeekPlan（扩展）

保留现有：`user_id`（计划所属角色）、`week_start`（= start_date）、`end_date`、`water_target_ml`、`weekly_kcal_deficit`、`weekly_workout_sessions`、`target_weight_kg`、legacy meal/workout modes。

新增：

| 字段 | 说明 |
|------|------|
| `title` | 短标题，可空则 UI 用日期区间代替 |
| `note` | 自由备注 |
| `daily_kcal_cap` | 可选日摄入硬顶（kcal）；仅对照提示，不拦记账 |

**生效规则：** 对角色 U、日期 D，取 `user_id=U` 且 `start ≤ D ≤ end` 的计划；若多条重叠，取 **start 最新**，再比 `id`。无覆盖计划 → 饮水用 `User.default_water_ml`，无日摄入上限，缺口参考用默认（如 3500 / 7）。

**权限：** JWT 用户可为 couple 内任一 `target_user_id` 创建/更新/删除计划（私有双人 App）。

**列表：** `month=YYYY-MM` 时返回与该月有日期交集的双方计划，前端按角色分组。

区间最长 **60 天**（已有校验可延续）。

### User / BMR 档案

`PATCH /api/auth/me` 增加可写：

- `sex`: `male` | `female`
- `age`: int

身高、体重仍取该用户 **最近一条 BodyMetric**；无则用现有默认档案。BMR 公式保持 Mifflin–St Jeor；日历与今日共用 `user_bmr()`，优先读 User 上的 sex/age，去掉仅按 user_id 写死的路径（可作无档案时的 fallback）。

## 界面行为

### 日历月视图

- 格内：上半龙 / 下半叶，颜色 = `full | partial | none`（饮水达标 ∧ 摄入−消耗−BMR≤0）。
- 下方「本月计划」：按角色分组卡片（标题、区间、饮水、缺口、上限摘要）；「进行中」标记覆盖今天的计划。
- **+ 新建**：先选角色 → 起止日期 → 标题/备注/饮水/期间缺口/日摄入上限/运动次数/体重目标。
- 点卡片编辑（双方可改）。

### 日详情（点进某日）

- 布局：双栏（桌面/宽屏左右；手机上下），每栏对齐今日信息架构：
  - 达标摘要
  - 餐食列表（吃了啥、kcal）
  - 饮水总量 / 目标 + **时间线**（何时喝的、每笔 ml）
  - 运动内容
  - 可选展开能量一行
- 数据：双方该日完整明细，不是只有 level。
- 改记：跳转今日并带 `?date=`，或以当前身份编辑自己栏；改对方需切到该角色（避免误改）。顶栏保留「去改记」入口。

### 今日

- 饮水目标、日均缺口参考、日摄入上限：来自 **当前登录角色** 在该 `date` 上生效的计划。
- 折叠「能量账本」：摄入、运动消耗、BMR、盈余或缺口；对照日摄入上限与 `期间缺口÷天数`。
- 改计划后，凡被覆盖的日期打开今日即反映新目标。

### 我的

- 设置性别、年龄（BMR）。
- 引导完善身体记录（身高体重）以提升 BMR 精度。

## API 变更摘要

| 端点 | 变更 |
|------|------|
| `GET /api/week-plans?list=1&month=` | 返回 couple 双方、与月相交的计划；可带 `user_id` 过滤 |
| `PUT /api/week-plans` | `target_user_id`、`title`、`note`、`daily_kcal_cap`；`id` 更新时校验归属 |
| `DELETE /api/week-plans/{id}` | 允许删对方计划（couple 内） |
| `GET /api/today` | 增加 `energy`：intake/burn/bmr/surplus + 计划目标字段 |
| `GET /api/calendar/day` | 每侧嵌套与 `/today` 同构的 section（餐列表、水时间线、运动、done、energy），供双栏渲染 |
| `PATCH /api/auth/me` | `sex`、`age` |

日历月接口可保持 `level` 为主；进度条仍对 **当前用户** 的生效计划区间汇总（可选后续做成「当前查看角色」）。

## 联动公式（不变）

- `surplus = intake − burn − BMR`
- 热量 OK ⇔ `surplus ≤ 0`
- 饮水 OK ⇔ `water_ml ≥ water_target_ml`（目标来自当日计划）
- 日色 `full` / `partial` / `none` 规则保持现有 energy snapshot
- 日均缺口参考 = `weekly_kcal_deficit / period_days`

日摄入上限：UI 对照（如摄入超过上限时提示），**不**阻止写入餐食。

## 测试要点

- 为 leaf 建计划后，dragon 登录仍能 list/edit；`on=` 按 leaf 查到该计划。
- 同角色重叠区间取最新 start。
- 今日无计划 vs 有计划时 `water_target` / `daily_kcal_cap` / energy 字段。
- User sex/age 变更后 `user_bmr` 与日历色变化。
- `calendar/day` 含饮水多笔时间与餐列表。
- 月列表只含与 `month` 相交的计划。

## 非目标（本期）

- 独立计划 Tab
- 月历格内显示饮水/缺口数字
- 自定义打卡项、标签、复杂餐/练规则编辑器
- 用摄入上限强制拒绝记账
