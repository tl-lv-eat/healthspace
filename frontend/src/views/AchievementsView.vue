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
const adminOpen = ref<string[]>([])
const newSlug = ref('')
const newTitle = ref('')
const newTarget = ref(5)
const newPoints = ref(10)
const savingCatalog = ref(false)

const list = computed((): MineAchievementItem[] => {
  if (!data.value) return []
  return data.value[tab.value]
})

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
      metric: 'workout_sessions',
      target_value: Number(newTarget.value),
      points_reward: Number(newPoints.value),
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

function goBack() {
  router.back()
}

onMounted(() => {
  void load()
  void loadCatalog()
})
</script>

<template>
  <div class="ach-page">
    <van-nav-bar title="成就" left-arrow @click-left="goBack" />

    <van-tabs v-model:active="tab" shrink swipeable class="ach-page__tabs">
      <van-tab name="incomplete" :title="`进行中 (${data?.incomplete.length ?? 0})`" />
      <van-tab name="claimable" :title="`可领取 (${data?.claimable.length ?? 0})`" />
      <van-tab name="claimed" :title="`已领取 (${data?.claimed.length ?? 0})`" />
    </van-tabs>

    <div v-if="list.length" class="ach-page__list">
      <article v-for="item in list" :key="item.achievement.id" class="ach-card fit-card">
        <div class="ach-card__head">
          <h2>{{ item.achievement.title }}</h2>
          <span class="ach-card__badge">{{ scopeLabel(item.achievement.scope) }}</span>
        </div>
        <p class="ach-card__desc">{{ item.achievement.description }}</p>
        <p class="ach-card__progress">进度：{{ progressLabel(item) }}</p>
        <p class="ach-card__points">奖励 {{ item.achievement.points_reward }} 积分</p>
        <van-button
          v-if="item.status === 'claimable'"
          type="primary"
          block
          round
          :loading="claimingId === item.achievement.id"
          @click="onClaim(item)"
        >
          领取积分
        </van-button>
        <p v-else-if="item.status === 'claimed'" class="ach-card__claimed">
          已于 {{ item.claimed_at?.slice(0, 10) ?? '—' }} 领取
        </p>
      </article>
    </div>
    <van-empty v-else description="暂无成就" class="ach-page__empty" />

    <van-collapse v-model="adminOpen" class="ach-page__admin">
      <van-collapse-item title="目录管理（双人可编辑）" name="admin">
        <van-cell-group inset>
          <van-field v-model="newSlug" label="标识" placeholder="唯一 slug" />
          <van-field v-model="newTitle" label="标题" placeholder="成就名称" />
          <van-field v-model.number="newTarget" type="digit" label="目标次数" />
          <van-field v-model.number="newPoints" type="digit" label="奖励积分" />
          <van-button
            type="primary"
            block
            round
            :loading="savingCatalog"
            class="ach-page__admin-add"
            @click="onCreateCatalog"
          >
            添加（运动次数类）
          </van-button>
        </van-cell-group>
        <ul class="ach-admin-list">
          <li v-for="row in catalog" :key="row.id">
            <span>{{ row.title }} · {{ row.points_reward }}分</span>
            <van-button size="mini" type="danger" plain @click="onDeleteCatalog(row.id)">删</van-button>
          </li>
        </ul>
      </van-collapse-item>
    </van-collapse>
  </div>
</template>

<style scoped>
.ach-page {
  min-height: 100vh;
  background: var(--bg, #f6f7f9);
  padding-bottom: 32px;
}

.ach-page__tabs {
  margin-bottom: 8px;
}

.ach-page__list {
  padding: 0 16px;
}

.ach-card {
  padding: 18px 20px;
  margin-bottom: 14px;
}

.ach-card__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
}

.ach-card__head h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
}

.ach-card__badge {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
  background: var(--primary-soft);
  padding: 4px 8px;
  border-radius: 8px;
}

.ach-card__desc {
  margin: 8px 0 0;
  font-size: 14px;
  color: var(--muted);
  line-height: 1.45;
}

.ach-card__progress,
.ach-card__points {
  margin: 10px 0 0;
  font-size: 14px;
  font-weight: 700;
}

.ach-card__claimed {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--muted);
}

.ach-page__empty {
  margin-top: 48px;
}

.ach-page__admin {
  margin: 24px 16px 0;
}

.ach-page__admin-add {
  margin: 12px 16px 8px;
}

.ach-admin-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0 8px;
}

.ach-admin-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  font-size: 14px;
  border-bottom: 1px solid var(--line, #eee);
}
</style>
