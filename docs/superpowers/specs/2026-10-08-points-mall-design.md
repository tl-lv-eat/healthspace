# 积分与商城（去掉目标）

**Status:** approved for planning  
**Date:** 2026-10-08  
**Approach:** 改造现有 PointsLedger / Reward / Redemption；删除 Goal；Tab「目标」→「积分与商城」；定时按结算时刻日结/计划结。

## 背景

用户不再需要「目标」模式，改为：

1. 积分制度与日历/计划/运动联动  
2. 每日固定时刻结算「刚结束的那一天」  
3. 自建奖励商城，需对方审核上架  
4. 购买后进入个人待使用，可自助标已使用；双方互看待用/已用  

## 已锁定选择

| 主题 | 选择 |
|------|------|
| 日结时刻 | 默认 **00:00**，设置可改 0–23 整点；结算对象为**刚结束的日历日** |
| 计划结 | 计划 `end_date` 的**次日**同一结算时刻结一次 |
| 计划档位 | **B +5**（缺口+运动+天天饮水）；**A −2**（缺口+运动，饮水未天天达标）；**其他 −5** |
| 运动 +2 | 当日有氧 `duration_min` + 力量 `duration_min` **合计 ≥ 40** |
| 力量 | **必须填写时长（分钟）**，不再用组数折算 |
| Tab | **「积分与商城」**（账本 + 商城 + 双方奖励） |
| 核销 | **自己点「已使用」**；对方只读可见 |
| 规则配置 | 双人**共用一份**设置；可改时刻与各分值 |
| 实现 | 薄改现有积分/奖励，去掉 Goal |

## 日结规则

对用户 U、日期 D（在结算时刻到达后处理「昨天」或补结算指定日）：

| reason key | 条件 | 默认 delta |
|------------|------|------------|
| `daily_water` | `water_ml ≥ water_target`（目标来自当日生效计划，否则默认饮水） | +1 |
| `daily_deficit` | 当日非空（有餐/水/运动之一）且 `intake − burn − BMR ≤ 0` | +1 |
| `daily_workout_40` | 当日运动折合分钟 ≥ 40 | +2 |

幂等：`{user_id}:{D}:{reason}`。同一天重复跑不重复加分。

空日（完全无记）：三项均不加分。

## 计划结规则

对计划 P（`user_id`、`start`–`end`），在 `end+1` 日的结算时刻：

1. 用与日历进度相同的累计：缺口贡献 vs `weekly_kcal_deficit`；运动天数 vs `weekly_workout_sessions`；区间内每日 `water_ok`。  
2. 若缺口达标 ∧ 运动达标 ∧ **每一天** `water_ok` → 档 **B**（+5）  
3. 否则若缺口达标 ∧ 运动达标 → 档 **A**（−2）  
4. 否则档 **fail**（−5）  

幂等：`{user_id}:plan:{plan_id}:settle`。无计划可结则跳过。

分值均可在设置中覆盖（含负分绝对值保留符号语义：配置存整数，B 正、A/fail 可为负）。

## 设置

共享配置字段（建议表 `couple_settings` 单行或 JSON 文件+API）：

- `settle_hour`：0–23，默认 0  
- `points_daily_water`：默认 1  
- `points_daily_deficit`：默认 1  
- `points_daily_workout_40`：默认 2  
- `points_plan_tier_b`：默认 5  
- `points_plan_tier_a`：默认 -2  
- `points_plan_tier_fail`：默认 -5  

UI：设置页「积分结算」区块；积分页可「补结算昨天 / 指定日」（管理员式双人可用）。

时区：使用服务器本地时区（部署约定 Asia/Shanghai）；文档注明。

## 商城与奖励

### Reward 状态机

`draft` 不需要（创建即进待审）→ `pending_review` → `listed` | `rejected` → 可再编辑后重新 `pending_review`。`archived` = 下架（创建者可操作）。

字段：现有 title/description/points_price 等 + `status`、`reject_reason`、`reviewed_by`、`reviewed_at` + **`category`**。

**分类（必选，固定枚举）：**

| 值 | 展示名 |
|----|--------|
| `food` | 饮食奖励 |
| `fun` | 玩乐奖励 |
| `intimacy` | 亲密奖励 |
| `adult` | 18+奖励 |

商城列表按分类筛选/分组；`adult` 类目前不做额外锁（双人私密 App，默认可直接浏览）。创建与审核流程与其它分类相同。

仅 `listed` 可购买。列表：商城展示双方 `listed`；「待我审核」= 对方创建的 `pending_review`；「我的草稿/打回」= 自己的 pending/rejected。

### Redemption

购买：校验余额与 `listed` → ledger `redeem` 扣分 → `status=pending`（待使用）。  
已使用：持有者 PATCH → `fulfilled` + `fulfilled_at`。  
本期：**不提供退款/取消退分**（购买即消费积分）。

双方视图：按用户分组列出 pending / fulfilled 兑换记录（含奖励标题、花费、时间）。

## 力量时长

Workout strength payload 增加必填 `duration_min`（≥1）。前端力量记录表单项；旧数据无时长则日结「运动 40」视为 0 分钟该条。

## 调度

应用内后台任务（APScheduler 或等价循环）：每分钟检查是否到达 `settle_hour` 且该「日历结算日」未跑过；跑完写入 `settlement_runs`（date, kind=daily|plan, status）防重。

启动时可补跑最近 N 天未结（可选，默认补昨天）。

## 前端

- TabLayout：目标 → **积分与商城**；路由 `/goals` 可重定向到 `/points-mall` 或复用路径改内容。  
- 页内分区：余额与流水 | 商城（上架/待审/新建） | 双方待用/已用。  
- GoalsView / Goal API / GoalCard：**删除或停用**。  
- Settings：积分规则。  
- WorkoutSheet：力量时长。

## 停用

- Goal 模型可保留表但 API 410/移除；前端入口全删。  
- 旧积分 reason（`daily_all_three`、`weekly_plan_complete`、`goal_complete`）不再新发；历史流水保留。  
- 活动钩子 `after_daily_activity` 即时发日分：**关闭**，改调度结算。

## 测试要点

- 日结三项幂等与分值可配置  
- 运动分钟 = 有氧 + 力量 duration  
- 计划三档 B/A/fail 与幂等  
- 奖励：创建（含分类）→打回→再提审→通过→购买→待用→已用；按分类筛选  

- 非 listed 不可买；余额不足拒绝  
- Goal 路由移除后前端无死链  

## 成就系统（「我的」）

入口：**我的 → 成就**。进度两人独立；目录分通用 / 独立。

| 类型 | 说明 | 示例 |
|------|------|------|
| 通用 `scope=shared` | 规则相同，进度各自算 | 日历绿日累计/连续、运动次数、运动总分钟、饮水达标天数 |
| 独立 `scope=persona` | 按角色或性别不同阈值 | BMI 区间、体脂率上限（男女默认不同，可编辑） |

状态：`locked` → `claimable`（达标可提示领取）→ `claimed`（领取后入账，幂等）。**领取前不加分**。

预置可增删改；任一方可编辑通用成就；独立成就可绑 `user_id` 或按 `sex` 阈值。

## 品牌

App 显示名：**健康space🐉🍃**（原「双人减」）。

## 非目标

- 支付、库存限量、购买退款  
- 目标系统  
- 按人不同结算规则  
- 复杂审批流（多人）  
- 成就自动到账（必须手动领取）
