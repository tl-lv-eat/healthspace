# 商城管理（我的 · 管理员设置）

**Status:** draft  
**Date:** 2026-10-08  
**Approach:** 「我的」独立瓷砖进入管理页；后端 `scope=catalog` + 双人可改价/下架/直接重新上架。

## 背景

积分商城已有上架审核、兑换与奖励柜。种子商品与已上架商品的**积分价 / 上下架**目前缺少集中入口：列表 `scope=mine` 不含已上架项，且 PATCH/archive 仅创建者可操作，对方无法维护目录。

需要在「我的」增加轻量管理员入口，供双人维护商城货架，而不替代「积分与商城」里的提案审核与兑换流程。

## 已锁定选择

| 主题 | 选择 |
|------|------|
| 谁可操作 | 龙龙 / 孙孙（`dragon` / `leaf`）**任一方**可改全部 catalog 商品（含种子与对方创建） |
| 能力范围 | **仅**改积分价、下架、重新上架；**不**在此页新建、删除、改标题/说明/分类/私密 |
| 入口 | 「我的」**单独瓷砖** → 路由 `/mall-admin` |
| 重新上架 | `archived` → **直接 `listed`**（免审核） |
| 待审核/已打回 | 仍只在「积分与商城」处理，不进管理页列表 |

## 整体结构

1. **MineView** 增加瓷砖：标题「商城管理」，说明「积分价 · 上下架」。  
2. **路由** `/mall-admin` → `MallAdminView`（需登录，与其它子页一致）。  
3. **页面**：Hero +「上架中」列表 +「已下架」列表；每行改价保存与状态切换。  
4. **后端**：扩展 list scope；放宽改价/archive 权限；新增 relist。

## 数据流与接口

### `GET /api/rewards?scope=catalog`

- 过滤：`creator_user_id ∈ {dragon, leaf}` 且 `status ∈ {listed, archived}`。  
- 可选沿用现有 `category` 查询参数（管理页可不筛）。  
- 返回现有 `RewardOut`；管理页可展示完整 description（catalog 视为管理视图，`reveal=true`）。

### `PATCH /api/rewards/{id}`（管理改价）

- 管理页只提交 `{ "points_price": N }`（N > 0）。  
- **权限拆分**（避免非创建者借 PATCH 改标题等）：  
  - **任一方** + 商品属双人 + `status ∈ {listed, archived}` + body **仅含** `points_price` → 允许。  
  - **创建者** + `status ∈ {pending_review, rejected, listed}` → 保持现有全字段编辑；`PATCH active:true` 仍可把 archived 送回 `pending_review`（提案流），**管理页不走这条**。  
- `archived` 必须可仅改价（当前若整单不可编辑 archived，需为「仅改价」放开）。

### `POST /api/rewards/{id}/archive`

- 任一方；仅 `listed` → `archived`；同步 `active=false`。

### `POST /api/rewards/{id}/relist`（新增）

- 任一方；仅 `archived` → `listed`；清空 reject/review 元数据可选；同步 `active=true`。  
- **不**使用现有 `PATCH active:true`（该路径会回到 `pending_review`）。

### 错误

| 情况 | HTTP |
|------|------|
| 非双人商品 | 404 |
| 状态不允许 | 400 |
| 非创建者改非价字段 | 403 |
| 积分价 ≤ 0 | 422 |

前端：失败 toast；成功后刷新列表。改价不做乐观假成功。

## 前端

### API 客户端

- `fetchRewards({ scope: 'catalog' })`  
- `relistReward(id)` → `POST .../relist`  
- 现有 `patchReward` / `archiveReward` 复用

### `MallAdminView`

- 视觉对齐设置/成就：圆角 hero、section label、卡片列表。  
- 上架中：标题、分类标签、积分输入、「保存」、「下架」。  
- 已下架：同上可改价 +「重新上架」。  
- 空态文案：「暂无上架商品」/「暂无下架商品」。

### 路由与导航

- `router`：`/mall-admin`，name `mall-admin`。  
- Mine 瓷砖链到该路由。

## 边界与不在范围

**在范围内**

- 改价后商城兑换立即按新价扣分。  
- 下架后 `scope=listed` 不再出现，不可兑。  
- 已兑换、待使用的奖励柜记录不受下架影响（仍按兑换时 `points_spent`）。

**不在范围**

- 硬删除商品  
- 批量改价  
- 独立 admin 角色/密码  
- 在管理页新建商品或走审核流  
- 改结算规则（仍在「设置」）

## 测试

- `scope=catalog` 返回 listed+archived，不含 pending/rejected。  
- 非创建者可改对方/种子商品 `points_price`。  
- 非创建者不可改对方商品 `title`。  
- 任一方 archive listed；任一方 relist archived → listed。  
- relist 后 `GET listed` 可见且可兑（积分足够时）。

## 与现有商城关系

| 能力 | 积分与商城 Tab | 商城管理页 |
|------|----------------|------------|
| 浏览兑换 | ✓ | — |
| 新建提案 / 审核 | ✓ | — |
| 改积分价 | 部分（创建者编辑提案） | ✓ 双人、上架+下架 |
| 下架 / 免审重新上架 | 创建者 archive（现） | ✓ 双人 + relist |
