<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast } from 'vant'
import WaterPanel from '@/components/WaterPanel.vue'
import MealPanel from '@/components/MealPanel.vue'
import { useAuthStore } from '@/stores/auth'
import {
  fetchToday,
  formatDateLabel,
  formatDateLocal,
  type TodayResponse,
} from '@/api/today'
import { fetchWaterDay, type WaterDay } from '@/api/water'
import { formatWorkoutSummary } from '@/api/workouts'
import { fetchReport, type AiReport } from '@/api/reports'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
function dateFromRoute(): string {
  const q = route.query.date
  if (typeof q === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(q)) return q
  return formatDateLocal()
}

const date = ref(dateFromRoute())
const today = ref<TodayResponse | null>(null)
const waterDay = ref<WaterDay | null>(null)
const refreshing = ref(false)
const dailyReport = ref<AiReport | null>(null)
const reportExcerpt = computed(() => {
  const md = dailyReport.value?.content_md ?? ''
  if (!md) return ''
  const line = md.split('\n').find((l) => l.trim() && !l.startsWith('#'))
  return (line ?? md).slice(0, 120)
})

async function reload(withOverlay = false) {
  if (withOverlay) {
    showLoadingToast({ message: '加载中…', forbidClick: true, duration: 0 })
  }
  try {
    const [t, w] = await Promise.all([fetchToday(date.value), fetchWaterDay(date.value)])
    today.value = t
    waterDay.value = w
    try {
      dailyReport.value = await fetchReport('daily', date.value)
    } catch {
      dailyReport.value = null
    }
  } catch {
    showFailToast('加载今日数据失败')
  } finally {
    refreshing.value = false
    if (withOverlay) closeToast()
  }
}

watch(
  () => route.query.date,
  () => {
    const next = dateFromRoute()
    if (next !== date.value) {
      date.value = next
      void reload(true)
    }
  },
)

onMounted(() => {
  date.value = dateFromRoute()
  void reload(true)
})

function goWorkout() {
  router.push({ name: 'workout', query: { date: date.value } })
}

const mealKcal = computed(() =>
  (today.value?.me.meals ?? []).reduce((s, m) => s + (m.user_kcal || 0), 0),
)

const doneCount = computed(() => {
  const d = today.value?.me.done
  if (!d) return 0
  return Number(d.meal) + Number(d.water) + Number(d.workout)
})
</script>

<template>
  <div class="today">
    <header class="today__top">
      <div>
        <p class="today__hello">Hi, {{ auth.user?.display_name ?? '—' }}</p>
        <h1 class="today__date">{{ formatDateLabel(date) }}</h1>
      </div>
      <div class="today__ring" :style="{ '--p': `${(doneCount / 3) * 100}%` }">
        <span>{{ doneCount }}/3</span>
      </div>
    </header>

    <router-link
      v-if="dailyReport"
      :to="{ name: 'report', query: { kind: 'daily', period: date } }"
      class="today__report fit-card"
    >
      <p class="fit-section-label">AI 日报告</p>
      <p class="today__report-text">{{ reportExcerpt }}…</p>
    </router-link>

    <div v-if="today" class="today__partner fit-card">
      <div class="today__partner-head">
        <span class="today__partner-name">{{ today.partner.display_name }}</span>
        <span class="today__partner-sub">对方今日</span>
      </div>
      <div class="today__dots">
        <span :class="{ on: today.partner.done.meal }">饮食</span>
        <span :class="{ on: today.partner.done.water }">饮水</span>
        <span :class="{ on: today.partner.done.workout }">运动</span>
      </div>
      <p class="today__partner-water">
        {{ today.partner.water_total_ml }} / {{ today.partner.water_target_ml }} ml
      </p>
    </div>

    <div class="today__stats">
      <div class="stat fit-card">
        <p class="stat__k">摄入</p>
        <p class="stat__v cal">{{ mealKcal }}</p>
        <p class="stat__u">kcal</p>
      </div>
      <div class="stat fit-card">
        <p class="stat__k">饮水</p>
        <p class="stat__v water">{{ waterDay?.total_ml ?? 0 }}</p>
        <p class="stat__u">ml</p>
      </div>
      <div class="stat fit-card">
        <p class="stat__k">运动</p>
        <p class="stat__v work">{{ today?.me.workouts.length ?? 0 }}</p>
        <p class="stat__u">条</p>
      </div>
    </div>

    <main class="today__body">
      <van-pull-refresh v-model="refreshing" @refresh="reload()">
        <template v-if="today && waterDay">
          <WaterPanel
            :date="date"
            :target-ml="waterDay.target_ml"
            :total-ml="waterDay.total_ml"
            :entries="waterDay.entries"
            @changed="reload()"
          />
          <MealPanel :date="date" :meals="today.me.meals" @changed="reload()" />
          <section class="workout-block fit-card fit-card-pad">
            <header class="workout-block__head">
              <div>
                <p class="fit-section-label">Workout</p>
                <h2>今日运动</h2>
              </div>
              <button type="button" class="workout-block__cta" @click="goWorkout">去记录</button>
            </header>
            <ul v-if="today.me.workouts.length" class="workout-block__list">
              <li v-for="w in today.me.workouts" :key="w.id">
                <span>{{ formatWorkoutSummary(w) }}</span>
                <time>{{ w.created_at.slice(11, 16) }}</time>
              </li>
            </ul>
            <p v-else class="empty">还没有运动 — 点右上角开始</p>
          </section>
        </template>
        <van-empty v-else description="暂无数据" />
      </van-pull-refresh>
    </main>
  </div>
</template>

<style scoped>
.today {
  min-height: 100vh;
  padding: 20px 16px 28px;
}

.today__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.today__hello {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
}

.today__date {
  margin: 4px 0 0;
  font-size: 1.65rem;
  font-weight: 800;
}

.today__ring {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 800;
  background:
    radial-gradient(circle at center, var(--bg) 58%, transparent 59%),
    conic-gradient(var(--primary) var(--p), var(--line) 0);
  color: var(--ink);
}

.today__report {
  display: block;
  padding: 14px 16px;
  margin-bottom: 14px;
  text-decoration: none;
  color: inherit;
}

.today__report-text {
  margin: 6px 0 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--muted);
  font-weight: 600;
}

.today__partner {
  padding: 14px 16px;
  margin-bottom: 14px;
}

.today__partner-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 10px;
}

.today__partner-name {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
}

.today__partner-sub {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.today__dots {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.today__dots span {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: var(--bg);
  color: var(--muted);
}

.today__dots span.on {
  background: var(--primary-soft);
  color: var(--primary-dark);
}

.today__partner-water {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--water);
  font-weight: 700;
}

.today__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 18px;
}

.stat {
  padding: 14px 10px;
  text-align: center;
}

.stat__k {
  margin: 0;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}

.stat__v {
  margin: 6px 0 0;
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 800;
  line-height: 1;
}

.stat__v.cal {
  color: var(--cal);
}
.stat__v.water {
  color: var(--water);
}
.stat__v.work {
  color: #e67700;
}

.stat__u {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
}

.today__body {
  padding-bottom: 8px;
}

.workout-block {
  margin-top: 4px;
}

.workout-block__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.workout-block__head h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 800;
}

.workout-block__cta {
  border: none;
  background: var(--workout-soft);
  color: #e67700;
  font-weight: 800;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 12px;
  cursor: pointer;
}

.workout-block__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.workout-block__list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--line);
  font-size: 14px;
  font-weight: 600;
}

.workout-block__list time {
  color: var(--muted);
  font-size: 12px;
  flex-shrink: 0;
}

.empty {
  margin: 0;
  font-size: 13px;
  color: var(--muted);
  font-weight: 500;
}
</style>
