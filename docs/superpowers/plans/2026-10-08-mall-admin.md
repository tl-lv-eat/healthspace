# Mall Admin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Mine-entry mall admin page where either partner can change reward point prices and shelf status (archive / direct relist).

**Architecture:** Extend `GET /api/rewards` with `scope=catalog` (listed+archived). Split `PATCH` so price-only updates on listed/archived work for either partner; keep full-field edit creator-only. Open `archive` to either partner; add `POST /relist` for archived→listed without review. Frontend: `/mall-admin` + Mine tile.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite, pytest, Vue 3 + existing design tokens

**Spec:** `docs/superpowers/specs/2026-10-08-mall-admin-design.md`

---

## File map

| File | Responsibility |
|------|----------------|
| `backend/app/routers/rewards.py` | `catalog` scope; price-only PATCH for either partner; open archive; `relist` |
| `backend/tests/test_rewards.py` | Catalog / price / archive / relist tests |
| `frontend/src/api/rewards.ts` | `catalog` scope type; `relistReward` |
| `frontend/src/views/MallAdminView.vue` | Admin UI: price + shelf |
| `frontend/src/router/index.ts` | `/mall-admin` route |
| `frontend/src/views/MineView.vue` | Tile link |
| `docs/superpowers/specs/2026-10-08-mall-admin-design.md` | Mark implemented when done |

---

### Task 1: `scope=catalog` list

**Files:**
- Modify: `backend/app/routers/rewards.py`
- Test: `backend/tests/test_rewards.py`

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_rewards.py`:

```python
def test_reward_catalog_scope_listed_and_archived(client, auth_header, partner_header):
    pending = _create_reward(client, auth_header, title="待审", category="food")
    listed = _create_reward(client, auth_header, title="上架", category="fun")
    _approve(client, partner_header, listed["id"])
    archived = _create_reward(client, auth_header, title="下架", category="food")
    _approve(client, partner_header, archived["id"])
    ar = client.post(f"/api/rewards/{archived['id']}/archive", headers=auth_header)
    assert ar.status_code == 200

    cat = client.get("/api/rewards", headers=partner_header, params={"scope": "catalog"})
    assert cat.status_code == 200
    ids = {x["id"] for x in cat.json()}
    assert listed["id"] in ids
    assert archived["id"] in ids
    assert pending["id"] not in ids
    statuses = {x["id"]: x["status"] for x in cat.json()}
    assert statuses[listed["id"]] == "listed"
    assert statuses[archived["id"]] == "archived"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_rewards.py::test_reward_catalog_scope_listed_and_archived -v`

Expected: FAIL (422 invalid scope or catalog missing)

- [ ] **Step 3: Minimal implementation**

In `backend/app/routers/rewards.py`:

```python
ListScope = Literal["listed", "pending_review_for_me", "mine", "catalog"]
```

In `list_rewards`, add branch:

```python
elif scope == "catalog":
    q = q.filter(Reward.status.in_(("listed", "archived")))
```

Set reveal for catalog:

```python
reveal = scope in ("mine", "catalog")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_rewards.py::test_reward_catalog_scope_listed_and_archived -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/rewards.py backend/tests/test_rewards.py
git commit -m "feat: rewards catalog scope for mall admin"
```

---

### Task 2: Either-partner price-only PATCH (listed + archived)

**Files:**
- Modify: `backend/app/routers/rewards.py` (`patch_reward`)
- Test: `backend/tests/test_rewards.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_partner_can_patch_listed_price_only(client, auth_header, partner_header):
    rw = _create_reward(client, auth_header, title="改价", points_price=50)
    _approve(client, partner_header, rw["id"])
    p = client.patch(
        f"/api/rewards/{rw['id']}",
        headers=partner_header,
        json={"points_price": 80},
    )
    assert p.status_code == 200
    assert p.json()["points_price"] == 80
    assert p.json()["title"] == "改价"


def test_partner_cannot_patch_listed_title(client, auth_header, partner_header):
    rw = _create_reward(client, auth_header, title="原名")
    _approve(client, partner_header, rw["id"])
    p = client.patch(
        f"/api/rewards/{rw['id']}",
        headers=partner_header,
        json={"title": "盗改"},
    )
    assert p.status_code == 403


def test_partner_can_patch_archived_price(client, auth_header, partner_header):
    rw = _create_reward(client, auth_header, title="归档改价", points_price=30)
    _approve(client, partner_header, rw["id"])
    client.post(f"/api/rewards/{rw['id']}/archive", headers=auth_header)
    p = client.patch(
        f"/api/rewards/{rw['id']}",
        headers=partner_header,
        json={"points_price": 40},
    )
    assert p.status_code == 200
    assert p.json()["points_price"] == 40
    assert p.json()["status"] == "archived"
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest backend/tests/test_rewards.py::test_partner_can_patch_listed_price_only backend/tests/test_rewards.py::test_partner_cannot_patch_listed_title backend/tests/test_rewards.py::test_partner_can_patch_archived_price -v`

Expected: FAIL (403 on partner price patch and/or 400 on archived)

- [ ] **Step 3: Implement `patch_reward` permission split**

Replace the start of `patch_reward` body with:

```python
def _is_price_only_patch(body: RewardPatch) -> bool:
    return body.model_fields_set == {"points_price"} and body.points_price is not None


@router.patch("/{reward_id}")
def patch_reward(
    reward_id: int,
    body: RewardPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RewardOut:
    row = _get_reward_or_404(db, reward_id)
    if _is_price_only_patch(body) and row.status in ("listed", "archived"):
        row.points_price = body.points_price  # type: ignore[assignment]
        db.commit()
        db.refresh(row)
        return _reward_to_out(row, reveal=True)

    if row.creator_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your reward")
    if row.status not in ("pending_review", "rejected", "listed"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reward not editable")
    # ... keep existing field updates unchanged ...
```

Keep the rest of the creator-only field update block as-is (including `active` → pending_review path).

- [ ] **Step 4: PASS**

Run: `pytest backend/tests/test_rewards.py::test_partner_can_patch_listed_price_only backend/tests/test_rewards.py::test_partner_cannot_patch_listed_title backend/tests/test_rewards.py::test_partner_can_patch_archived_price -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/rewards.py backend/tests/test_rewards.py
git commit -m "feat: either partner can patch catalog reward price"
```

---

### Task 3: Either-partner archive + `relist`

**Files:**
- Modify: `backend/app/routers/rewards.py`
- Test: `backend/tests/test_rewards.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_partner_can_archive_and_relist(client, auth_header, partner_header, db_session):
    from backend.app.services.points import grant

    rw = _create_reward(client, auth_header, title="货架", points_price=20)
    _approve(client, partner_header, rw["id"])

    ar = client.post(f"/api/rewards/{rw['id']}/archive", headers=partner_header)
    assert ar.status_code == 200
    assert ar.json()["status"] == "archived"
    assert ar.json()["active"] is False

    mall = client.get("/api/rewards", headers=auth_header).json()
    assert not any(x["id"] == rw["id"] for x in mall)

    rel = client.post(f"/api/rewards/{rw['id']}/relist", headers=partner_header)
    assert rel.status_code == 200
    assert rel.json()["status"] == "listed"
    assert rel.json()["active"] is True

    mall2 = client.get("/api/rewards", headers=auth_header).json()
    assert any(x["id"] == rw["id"] for x in mall2)

    grant(db_session, "dragon", 20, "test", "dragon:test:relist-redeem")
    red = client.post(f"/api/rewards/{rw['id']}/redeem", headers=auth_header)
    assert red.status_code == 200


def test_relist_rejects_non_archived(client, auth_header, partner_header):
    rw = _create_reward(client, auth_header, title="未下架")
    _approve(client, partner_header, rw["id"])
    bad = client.post(f"/api/rewards/{rw['id']}/relist", headers=auth_header)
    assert bad.status_code == 400
```

- [ ] **Step 2: Run — expect FAIL**

Run: `pytest backend/tests/test_rewards.py::test_partner_can_archive_and_relist backend/tests/test_rewards.py::test_relist_rejects_non_archived -v`

Expected: FAIL (403 on partner archive and/or 404 on relist)

- [ ] **Step 3: Implement**

In `archive_reward`, remove creator-only check (keep listed check):

```python
@router.post("/{reward_id}/archive")
def archive_reward(
    reward_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RewardOut:
    del user  # any authenticated couple member; row already scoped
    row = _get_reward_or_404(db, reward_id)
    if row.status != "listed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reward not listed")
    row.status = "archived"
    _sync_active(row)
    db.commit()
    db.refresh(row)
    return _reward_to_out(row, reveal=True)
```

Add after `archive_reward`:

```python
@router.post("/{reward_id}/relist")
def relist_reward(
    reward_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RewardOut:
    del user
    row = _get_reward_or_404(db, reward_id)
    if row.status != "archived":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reward not archived")
    row.status = "listed"
    row.reject_reason = None
    row.reviewed_by = None
    row.reviewed_at = None
    _sync_active(row)
    db.commit()
    db.refresh(row)
    return _reward_to_out(row, reveal=True)
```

- [ ] **Step 4: PASS full rewards file**

Run: `pytest backend/tests/test_rewards.py -v`

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/rewards.py backend/tests/test_rewards.py
git commit -m "feat: either partner archive and relist rewards"
```

---

### Task 4: Frontend API client

**Files:**
- Modify: `frontend/src/api/rewards.ts`

- [ ] **Step 1: Extend types and `relistReward`**

```typescript
export type RewardListScope = 'listed' | 'pending_review_for_me' | 'mine' | 'catalog'
```

After `archiveReward`:

```typescript
export async function relistReward(id: number): Promise<Reward> {
  const { data } = await http.post<Reward>(`/rewards/${id}/relist`)
  return data
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/rewards.ts
git commit -m "feat: frontend catalog scope and relistReward"
```

---

### Task 5: `MallAdminView` + route + Mine tile

**Files:**
- Create: `frontend/src/views/MallAdminView.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/MineView.vue`

- [ ] **Step 1: Add route** (next to settings/achievements)

```typescript
{
  path: '/mall-admin',
  name: 'mall-admin',
  component: () => import('@/views/MallAdminView.vue'),
  meta: { requiresAuth: true },
},
```

(Match whatever `meta` pattern neighboring routes use — if settings has no meta, omit meta and rely on global auth guard.)

- [ ] **Step 2: Create `MallAdminView.vue`**

Script responsibilities:

- `onMounted` → `fetchRewards({ scope: 'catalog' })`
- `listed = computed(() => items.filter(r => r.status === 'listed'))`
- `archived = computed(() => items.filter(r => r.status === 'archived'))`
- Local `draftPrices: Record<number, number>` initialized from loaded items
- `savePrice(r)` → `patchReward(r.id, { points_price: draftPrices[r.id] })` then reload; toast success/fail
- `onArchive(r)` → `archiveReward(r.id)` then reload
- `onRelist(r)` → `relistReward(r.id)` then reload
- Back via `router.back()`

Template structure (match Settings/Achievements premium shell):

```vue
<div class="ma">
  <header class="ma-hero">...</header>
  <section>
    <p class="fit-section-label">Listed</p>
    <h2>上架中</h2>
    <!-- card: cat label, title, number input, 保存, 下架 -->
    <p v-if="!listed.length" class="ma-empty">暂无上架商品</p>
  </section>
  <section>
    <p class="fit-section-label">Archived</p>
    <h2>已下架</h2>
    <!-- card: cat label, title, number input, 保存, 重新上架 -->
    <p v-if="!archived.length" class="ma-empty">暂无下架商品</p>
  </section>
</div>
```

Validate price: integer > 0 before PATCH; else `showFailToast('积分价需为正整数')`.

- [ ] **Step 3: Mine tile**

In `MineView.vue` `links` array, insert after settings (or before achievements):

```typescript
{
  to: '/mall-admin',
  title: '商城管理',
  desc: '积分价 · 上下架',
  tone: 'workout',
  mark: '商',
},
```

- [ ] **Step 4: Build**

Run: `cd frontend && npm run build`

Expected: success (chunk size warning OK)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/MallAdminView.vue frontend/src/router/index.ts frontend/src/views/MineView.vue
git commit -m "feat: mall admin page under Mine"
```

---

### Task 6: Spec status + full verification

**Files:**
- Modify: `docs/superpowers/specs/2026-10-08-mall-admin-design.md` — `Status: implemented`

- [ ] **Step 1: Run backend rewards tests**

Run: `pytest backend/tests/test_rewards.py -v`

Expected: all PASS

- [ ] **Step 2: Frontend build**

Run: `cd frontend && npm run build`

Expected: success

- [ ] **Step 3: Mark spec implemented + commit**

```bash
git add docs/superpowers/specs/2026-10-08-mall-admin-design.md
git commit -m "docs: mark mall-admin design as implemented"
```

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Mine tile → `/mall-admin` | 5 |
| `scope=catalog` listed+archived | 1 |
| Either partner price-only PATCH | 2 |
| Archived price editable | 2 |
| Non-creator cannot patch title | 2 |
| Either partner archive | 3 |
| `relist` archived→listed, no review | 3 |
| Relist then redeemable | 3 |
| Frontend API + UI | 4, 5 |
| No create/delete in admin | 5 (UI omits) |
| Spec status | 6 |
