<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast, showSuccessToast } from 'vant'
import {
  claimAchievement,
  createAchievement,
  deleteAchievement,
  fetchAchievementCatalog,
  fetchMineAchievements,
  type Achievement,
  type MineAchievementItem,
  type MineAchievementsResponse,
} from '@/api/achievements'

const router = useRouter()
const tab = ref<'incomplete' | 'claimable' | 'claimed'>('claimable')
const data = ref<MineAchievementsResponse | null>(null)
const claimingId = ref<number | null>(null)
const catalog = ref<Achievement[]>([])
const adminOpen = ref(false)
const newSlug = ref('')
const newTitle = ref('')
const newTarget = ref(5)
const newPoints = ref(10)
const savingCatalog = ref(false)

const list = computed((): MineAchievementItem[] => {
  if (!data.value) return []
  return data.value[tab.value]
})

const tabs = computed(() => [
  { key: 'claimable' as const, label: '可领取', count: data.value?.claimable.length ?? 0 },
  { key: 'incomplete' as const, label: '进行中', count: data.value?.incomplete.length ?? 0 },
  { key: 'claimed' as const, label: '已领取', count: data.value?.claimed.length ?? 0 },
])

async function loadCatalog() {
  try {
    catalog.value = await fetchAchievementCatalog()
  } catch {
    showFailToast('加载目录失败')
  }
}

async function load() {
  try {
    data.value = await fetchMineAchievements()
    if (data.value.claimable.length && tab.value === 'incomplete' && !data.value.incomplete.length) {
      tab.value = 'claimable'
    }
  } catch {
    showFailToast('加载成就失败')
  }
}

async function onClaim(item: MineAchievementItem) {
  if (claimingId.value !== null) return
  claimingId.value = item.achievement.id
  showLoadingToast({ message: '领取中…', forbidClick: true, duration: 0 })
  try {
    await claimAchievement(item.achievement.id)
    showSuccessToast(`+${item.achievement.points_reward} 积分`)
    await load()
  } catch {
    showFailToast('领取失败')
  } finally {
    closeToast()
    claimingId.value = null
  }
}

function progressLabel(item: MineAchievementItem): string {
  if (item.achievement.metric === 'bmi_in_range' || item.achievement.metric === 'body_fat_max') {
    return item.progress >= 1 ? '已达标' : '未达标'
  }
  return `${item.progress} / ${item.target}`
}

function progressPct(item: MineAchievementItem): number {
  if (item.achievement.metric === 'bmi_in_range' || item.achievement.metric === 'body_fat_max') {
    return item.progress >= 1 ? 100 : 0
  }
  if (!item.target) return 0
  return Math.min(100, Math.round((item.progress / item.target) * 100))
}

function scopeLabel(scope: string): string {
  return scope === 'shared' ? '通用' : '独立'
}

async function onCreateCatalog() {
  if (!newSlug.value.trim() || !newTitle.value.trim()) {
    showFailToast('请填写标识与标题')
    return
  }
  savingCatalog.value = true
  try {
    await createAchievement({
      slug: newSlug.value.trim(),
      title: newTitle.value.trim(),
      description: '',
      scope: 'shared',
      metric: 'workout_sessions',
      target_value: newTarget.value,
      points_reward: newPoints.value,
    })
    newSlug.value = ''
    newTitle.value = ''
    showSuccessToast('已添加')
    await loadCatalog()
    await load()
  } catch {
    showFailToast('添加失败')
  } finally {
    savingCatalog.value = false
  }
}

async function onDeleteCatalog(id: number) {
  try {
    await deleteAchievement(id)
    showSuccessToast('已删除')
    await loadCatalog()
    await load()
  } catch {
    showFailToast('删除失败')
  }
}

onMounted(() => {
  void load()
  void loadCatalog()
})
</script>

<template>
  <div class="ach">
    <header class="ach-hero">
      <div class="ach-hero__glow" aria-hidden="true" />
      <button type="button" class="ach-back" @click="router.back()">← 返回</button>
      <p class="fit-section-label">Achievements</p>
      <h1>成就</h1>
      <p class="ach-hero__hint">完成挑战 · 领取积分进账</p>
    </header>

    <div class="ach-tabs" role="tablist">
      <button
        v-for="t in tabs"
        :key="t.key"
        type="button"
        class="ach-tab"
        :class="{ 'ach-tab--on': tab === t.key }"
        @click="tab = t.key"
      >
        {{ t.label }}
        <span>{{ t.count }}</span>
      </button>
    </div>

    <div v-if="list.length" class="ach-list">
      <article
        v-for="item in list"
        :key="item.achievement.id"
        class="ach-card"
        :class="{
          'ach-card--claimable': item.status === 'claimable',
          'ach-card--claimed': item.status === 'claimed',
        }"
      >
        <div class="ach-card__head">
          <div>
            <span class="ach-card__scope">{{ scopeLabel(item.achievement.scope) }}</span>
            <h2>{{ item.achievement.title }}</h2>
          </div>
          <div class="ach-card__pts">
            <strong>+{{ item.achievement.points_reward }}</strong>
            <span>积分</span>
          </div>
        </div>
        <p v-if="item.achievement.description" class="ach-card__desc">
          {{ item.achievement.description }}
        </p>
        <div class="ach-card__meter">
          <div class="ach-card__meter-top">
            <span>进度</span>
            <strong>{{ progressLabel(item) }}</strong>
          </div>
          <div class="ach-card__track">
            <i :style="{ width: `${progressPct(item)}%` }" />
          </div>
        </div>
        <button
          v-if="item.status === 'claimable'"
          type="button"
          class="ach-claim"
          :disabled="claimingId === item.achievement.id"
          @click="onClaim(item)"
        >
          {{ claimingId === item.achievement.id ? '领取中…' : '领取积分' }}
        </button>
        <p v-else-if="item.status === 'claimed'" class="ach-card__done">
          已于 {{ item.claimed_at?.slice(0, 10) ?? '—' }} 领取
        </p>
      </article>
    </div>
    <p v-else class="ach-empty">暂无成就</p>

    <section class="ach-admin">
      <button type="button" class="ach-admin__toggle" @click="adminOpen = !adminOpen">
        <span>
          <p class="fit-section-label">Catalog</p>
          <strong>目录管理</strong>
        </span>
        <span class="ach-admin__chev">{{ adminOpen ? '收起' : '展开' }}</span>
      </button>
      <div v-if="adminOpen" class="ach-admin__body">
        <p class="ach-admin__hint">双人可编辑 · 运动次数类成就</p>
        <div class="ach-admin__fields">
          <input v-model="newSlug" class="ach-input" placeholder="唯一标识 slug" />
          <input v-model="newTitle" class="ach-input" placeholder="成就名称" />
          <div class="ach-admin__row">
            <label>
              目标次数
              <input v-model.number="newTarget" class="ach-input" type="number" min="1" />
            </label>
            <label>
              奖励积分
              <input v-model.number="newPoints" class="ach-input" type="number" min="1" />
            </label>
          </div>
          <button
            type="button"
            class="ach-claim"
            :disabled="savingCatalog"
            @click="onCreateCatalog"
          >
            {{ savingCatalog ? '添加中…' : '添加成就' }}
          </button>
        </div>
        <ul class="ach-admin__list">
          <li v-for="row in catalog" :key="row.id">
            <span>{{ row.title }} · {{ row.points_reward }} 分</span>
            <button type="button" class="ach-del" @click="onDeleteCatalog(row.id)">删</button>
          </li>
          <li v-if="!catalog.length" class="ach-admin__empty">目录为空</li>
        </ul>
      </div>
    </section>
  </div>
</template>

<style scoped>
.ach {
  padding: 12px 14px 40px;
}

.ach-hero {
  position: relative;
  overflow: hidden;
  padding: 14px 18px 20px;
  margin-bottom: 16px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--workout) 16%, var(--card)), var(--card) 55%);
  box-shadow: var(--shadow);
  animation: ach-in 0.45s ease both;
}

.ach-hero__glow {
  position: absolute;
  width: 180px;
  height: 180px;
  right: -40px;
  top: -50px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--workout) 35%, transparent), transparent 70%);
  pointer-events: none;
}

.ach-back {
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

.ach-hero h1 {
  position: relative;
  margin: 0;
  font-size: 1.7rem;
  font-weight: 800;
}

.ach-hero__hint {
  position: relative;
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.ach-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-bottom: 14px;
  padding: 4px;
  border-radius: 16px;
  background: color-mix(in srgb, var(--line) 55%, transparent);
}

.ach-tab {
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  padding: 10px 4px;
  border-radius: 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.ach-tab span {
  font-size: 11px;
  opacity: 0.85;
}

.ach-tab--on {
  background: var(--card);
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}

.ach-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ach-card {
  padding: 16px 16px 14px;
  border-radius: 20px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
  animation: ach-in 0.5s ease both;
}

.ach-card--claimable {
  background:
    linear-gradient(160deg, color-mix(in srgb, var(--primary) 12%, var(--card)), var(--card));
  border-color: color-mix(in srgb, var(--primary) 30%, var(--line));
}

.ach-card--claimed {
  opacity: 0.88;
}

.ach-card__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.ach-card__scope {
  display: inline-block;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-display);
  margin-bottom: 4px;
}

.ach-card h2 {
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
}

.ach-card__pts {
  text-align: right;
  flex-shrink: 0;
}

.ach-card__pts strong {
  display: block;
  font-size: 1.25rem;
  font-weight: 800;
  font-family: var(--font-display);
  color: var(--primary-dark);
  line-height: 1;
}

.ach-card__pts span {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
}

.ach-card__desc {
  margin: 8px 0 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--muted);
  font-weight: 600;
}

.ach-card__meter {
  margin-top: 14px;
}

.ach-card__meter-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  font-weight: 700;
  margin-bottom: 6px;
  color: var(--muted);
}

.ach-card__meter-top strong {
  color: var(--ink);
}

.ach-card__track {
  height: 8px;
  border-radius: 999px;
  background: var(--line);
  overflow: hidden;
}

.ach-card__track i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--primary), color-mix(in srgb, var(--workout) 70%, var(--primary)));
  transition: width 0.35s ease;
}

.ach-claim {
  margin-top: 14px;
  width: 100%;
  height: 44px;
  border: none;
  border-radius: 14px;
  background: var(--primary);
  color: var(--on-primary, #fff);
  font-weight: 800;
  font-size: 14px;
  cursor: pointer;
}

.ach-claim:disabled {
  opacity: 0.55;
}

.ach-card__done {
  margin: 12px 0 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.ach-empty {
  margin: 0;
  padding: 36px 16px;
  text-align: center;
  font-size: 13px;
  color: var(--muted);
  border: 1px dashed var(--line);
  border-radius: 18px;
  background: color-mix(in srgb, var(--card) 70%, transparent);
}

.ach-admin {
  margin-top: 22px;
  border-radius: 20px;
  border: 1px solid var(--line);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.ach-admin__toggle {
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  padding: 16px 16px 14px;
  border: none;
  background: transparent;
  color: var(--ink);
  text-align: left;
  cursor: pointer;
}

.ach-admin__toggle .fit-section-label {
  margin-bottom: 4px;
}

.ach-admin__toggle strong {
  font-size: 1.05rem;
  font-weight: 800;
}

.ach-admin__chev {
  font-size: 12px;
  font-weight: 800;
  color: var(--muted);
  padding-bottom: 2px;
}

.ach-admin__body {
  padding: 0 16px 16px;
  border-top: 1px solid var(--line);
}

.ach-admin__hint {
  margin: 12px 0;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.ach-admin__fields {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ach-admin__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.ach-admin__row label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  color: var(--muted);
}

.ach-input {
  width: 100%;
  box-sizing: border-box;
  height: 42px;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: color-mix(in srgb, var(--bg) 80%, var(--card));
  color: var(--ink);
  font: inherit;
  font-weight: 600;
}

.ach-admin__list {
  list-style: none;
  margin: 14px 0 0;
  padding: 0;
}

.ach-admin__list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 0;
  font-size: 13px;
  font-weight: 700;
  border-bottom: 1px solid var(--line);
}

.ach-admin__empty {
  justify-content: center !important;
  color: var(--muted);
  font-weight: 600 !important;
  border-bottom: none !important;
}

.ach-del {
  border: 1px solid color-mix(in srgb, var(--cal) 35%, var(--line));
  background: color-mix(in srgb, var(--cal) 10%, var(--card));
  color: var(--cal);
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 999px;
  cursor: pointer;
}

@keyframes ach-in {
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
