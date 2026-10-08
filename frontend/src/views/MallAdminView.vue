<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast, showSuccessToast } from 'vant'
import {
  archiveReward,
  fetchRewards,
  patchReward,
  relistReward,
  rewardCategoryLabel,
  type Reward,
} from '@/api/rewards'

const router = useRouter()
const items = ref<Reward[]>([])
const loading = ref(true)
const busyId = ref<number | null>(null)
const draftPrices = reactive<Record<number, number>>({})

const listed = computed(() => items.value.filter((r) => r.status === 'listed'))
const archived = computed(() => items.value.filter((r) => r.status === 'archived'))

function syncDrafts(list: Reward[]) {
  for (const r of list) {
    draftPrices[r.id] = r.points_price
  }
}

async function load() {
  loading.value = true
  try {
    const list = await fetchRewards({ scope: 'catalog' })
    items.value = list
    syncDrafts(list)
  } catch {
    showFailToast('加载商城目录失败')
  } finally {
    loading.value = false
  }
}

function validatePrice(id: number): number | null {
  const raw = draftPrices[id]
  const n = Number(raw)
  if (!Number.isInteger(n) || n <= 0) {
    showFailToast('积分价需为正整数')
    return null
  }
  return n
}

async function savePrice(r: Reward) {
  const price = validatePrice(r.id)
  if (price === null) return
  if (busyId.value !== null) return
  busyId.value = r.id
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await patchReward(r.id, { points_price: price })
    closeToast()
    showSuccessToast('已保存')
    await load()
  } catch {
    closeToast()
    showFailToast('保存失败')
  } finally {
    busyId.value = null
  }
}

async function onArchive(r: Reward) {
  if (busyId.value !== null) return
  busyId.value = r.id
  showLoadingToast({ message: '下架中…', forbidClick: true, duration: 0 })
  try {
    await archiveReward(r.id)
    closeToast()
    showSuccessToast('已下架')
    await load()
  } catch {
    closeToast()
    showFailToast('下架失败')
  } finally {
    busyId.value = null
  }
}

async function onRelist(r: Reward) {
  if (busyId.value !== null) return
  busyId.value = r.id
  showLoadingToast({ message: '上架中…', forbidClick: true, duration: 0 })
  try {
    await relistReward(r.id)
    closeToast()
    showSuccessToast('已重新上架')
    await load()
  } catch {
    closeToast()
    showFailToast('上架失败')
  } finally {
    busyId.value = null
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="ma">
    <header class="ma-hero">
      <div class="ma-hero__glow" aria-hidden="true" />
      <button type="button" class="ma-back" @click="router.back()">← 返回</button>
      <p class="fit-section-label">Mall Admin</p>
      <h1>商城管理</h1>
      <p class="ma-hero__hint">调整积分价 · 上下架（不改标题、不新建）</p>
    </header>

    <div v-if="loading" class="ma-loading">加载中…</div>
    <template v-else>
      <section class="ma-section">
        <p class="fit-section-label">Listed</p>
        <h2>上架中</h2>
        <div v-if="listed.length" class="ma-list">
          <article
            v-for="r in listed"
            :key="r.id"
            class="ma-card"
            :class="`ma-card--${r.category}`"
          >
            <div class="ma-card__head">
              <span class="ma-card__cat">{{ rewardCategoryLabel(r.category) }}</span>
              <h3>{{ r.title }}</h3>
            </div>
            <label class="ma-price">
              <span>积分价</span>
              <input v-model.number="draftPrices[r.id]" type="number" min="1" step="1" />
            </label>
            <div class="ma-card__actions">
              <button
                type="button"
                class="ma-btn ma-btn--primary"
                :disabled="busyId === r.id"
                @click="savePrice(r)"
              >
                保存
              </button>
              <button
                type="button"
                class="ma-btn"
                :disabled="busyId === r.id"
                @click="onArchive(r)"
              >
                下架
              </button>
            </div>
          </article>
        </div>
        <p v-else class="ma-empty">暂无上架商品</p>
      </section>

      <section class="ma-section">
        <p class="fit-section-label">Archived</p>
        <h2>已下架</h2>
        <div v-if="archived.length" class="ma-list">
          <article
            v-for="r in archived"
            :key="r.id"
            class="ma-card ma-card--archived"
            :class="`ma-card--${r.category}`"
          >
            <div class="ma-card__head">
              <span class="ma-card__cat">{{ rewardCategoryLabel(r.category) }}</span>
              <h3>{{ r.title }}</h3>
            </div>
            <label class="ma-price">
              <span>积分价</span>
              <input v-model.number="draftPrices[r.id]" type="number" min="1" step="1" />
            </label>
            <div class="ma-card__actions">
              <button
                type="button"
                class="ma-btn ma-btn--primary"
                :disabled="busyId === r.id"
                @click="savePrice(r)"
              >
                保存
              </button>
              <button
                type="button"
                class="ma-btn"
                :disabled="busyId === r.id"
                @click="onRelist(r)"
              >
                重新上架
              </button>
            </div>
          </article>
        </div>
        <p v-else class="ma-empty">暂无下架商品</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.ma {
  padding: 12px 14px 40px;
}

.ma-hero {
  position: relative;
  overflow: hidden;
  padding: 14px 18px 20px;
  margin-bottom: 18px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--workout) 16%, var(--card)), var(--card) 55%);
  box-shadow: var(--shadow);
  animation: ma-in 0.45s ease both;
}

.ma-hero__glow {
  position: absolute;
  width: 180px;
  height: 180px;
  right: -40px;
  top: -50px;
  border-radius: 50%;
  background: radial-gradient(
    circle,
    color-mix(in srgb, var(--workout) 35%, transparent),
    transparent 70%
  );
  pointer-events: none;
}

.ma-back {
  position: relative;
  border: none;
  background: transparent;
  padding: 0;
  margin-bottom: 10px;
  font: inherit;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
}

.ma-hero h1 {
  position: relative;
  margin: 0;
  font-size: 1.7rem;
  font-weight: 800;
}

.ma-hero__hint {
  position: relative;
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.ma-loading {
  padding: 24px 8px;
  text-align: center;
  font-weight: 700;
  color: var(--muted);
}

.ma-section {
  margin-bottom: 22px;
  animation: ma-in 0.5s ease both;
}

.ma-section h2 {
  margin: 4px 0 12px;
  font-size: 1.15rem;
  font-weight: 800;
}

.ma-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ma-card {
  position: relative;
  overflow: hidden;
  padding: 14px 14px 12px;
  border-radius: 18px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.ma-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--primary);
}

.ma-card--food::before {
  background: var(--cal);
}
.ma-card--fun::before {
  background: var(--workout);
}
.ma-card--intimacy::before {
  background: var(--primary);
}
.ma-card--adult::before {
  background: color-mix(in srgb, var(--ink) 55%, var(--primary));
}

.ma-card--archived {
  opacity: 0.92;
}

.ma-card__head {
  margin-bottom: 12px;
  padding-left: 4px;
}

.ma-card__cat {
  display: inline-block;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 4px;
  font-family: var(--font-display);
}

.ma-card h3 {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 800;
}

.ma-price {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--line) 40%, transparent);
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
}

.ma-price input {
  width: 100px;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px 10px;
  font: inherit;
  font-weight: 800;
  color: var(--ink);
  background: var(--card);
  text-align: right;
}

.ma-card__actions {
  display: flex;
  gap: 8px;
}

.ma-btn {
  flex: 1;
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  font: inherit;
  font-size: 13px;
  font-weight: 800;
  background: var(--card);
  color: var(--ink);
  cursor: pointer;
}

.ma-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.ma-btn--primary {
  border-color: color-mix(in srgb, var(--primary) 45%, var(--line));
  background: color-mix(in srgb, var(--primary) 14%, var(--card));
  color: var(--primary);
}

.ma-empty {
  margin: 0;
  padding: 18px 12px;
  text-align: center;
  font-weight: 700;
  color: var(--muted);
  border-radius: 16px;
  border: 1px dashed var(--line);
}

@keyframes ma-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
</style>
