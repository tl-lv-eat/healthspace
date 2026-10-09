<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast } from 'vant'
import WaterPanel from '@/components/WaterPanel.vue'
import MealPanel from '@/components/MealPanel.vue'
import { personaById } from '@/constants/personas'
import { useAuthStore } from '@/stores/auth'
import {
  fetchToday,
  formatDateLabel,
  formatDateLocal,
  type DoneFlags,
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
  return (line ?? md).slice(0, 100)
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
const partnerMealKcal = computed(() =>
  (today.value?.partner.meals ?? []).reduce((s, m) => s + (m.user_kcal || 0), 0),
)

function doneScore(d?: DoneFlags) {
  if (!d) return 0
  return Number(d.meal) + Number(d.water) + Number(d.workout)
}

const meScore = computed(() => doneScore(today.value?.me.done))
const partnerScore = computed(() => doneScore(today.value?.partner.done))
const duoScore = computed(() => meScore.value + partnerScore.value)

const mePersona = computed(() => personaById(today.value?.me.user_id ?? auth.user?.id))
const partnerPersona = computed(() => personaById(today.value?.partner.user_id))

const items = [
  { key: 'meal' as const, label: '饮食', short: '吃' },
  { key: 'water' as const, label: '饮水', short: '水' },
  { key: 'workout' as const, label: '运动', short: '练' },
]

const hourHint = computed(() => {
  const h = new Date().getHours()
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const meEnergy = computed(() => today.value?.me.energy)

/** Plan-backed target; `/water` and `/today` should agree after reload on date change. */
const waterTargetMl = computed(
  () =>
    waterDay.value?.target_ml ??
    today.value?.me.water.target_ml ??
    today.value?.me.energy.water_target_ml ??
    null,
)

const energySurplusTip = computed(() => {
  const e = meEnergy.value
  if (!e) return '—'
  if (e.empty) return '未记录'
  if (!e.meals_complete) return '饮食未记齐'
  const s = e.surplus_kcal ?? 0
  if (s > 0) return `盈余 +${s}`
  if (s < 0) return `缺口 ${Math.abs(s)}`
  return '持平 0'
})

const deficitContribKcal = computed(() => {
  const e = meEnergy.value
  if (!e || e.empty || !e.meals_complete) return 0
  if (typeof e.deficit_contrib === 'number') return Math.max(0, e.deficit_contrib)
  return Math.max(0, -(e.surplus_kcal ?? 0))
})

const intakeOverCap = computed(() => {
  const e = meEnergy.value
  if (!e || e.daily_kcal_cap == null) return false
  return e.intake_kcal > e.daily_kcal_cap
})

const intakeOverCapBy = computed(() => {
  const e = meEnergy.value
  if (!e || e.daily_kcal_cap == null) return 0
  return Math.max(0, e.intake_kcal - e.daily_kcal_cap)
})
</script>

<template>
  <div class="today">
    <!-- Duo hero: both personas at a glance -->
    <section class="duo" :class="`duo--${auth.user?.id ?? 'leaf'}`">
      <div class="duo__glow" aria-hidden="true" />
      <header class="duo__head">
        <div>
          <p class="duo__greet">{{ hourHint }}，{{ auth.user?.display_name ?? '—' }}</p>
          <h1 class="duo__date">{{ formatDateLabel(date) }}</h1>
        </div>
        <div class="duo__ring" :style="{ '--p': `${(duoScore / 6) * 100}%` }">
          <span class="duo__ring-n">{{ duoScore }}</span>
          <span class="duo__ring-d">/6</span>
        </div>
      </header>

      <div v-if="today" class="duo__rails">
        <article class="rail" :class="`rail--${today.me.user_id}`">
          <div class="rail__who">
            <span class="rail__emoji">{{ mePersona?.emoji }}</span>
            <div>
              <p class="rail__name">{{ auth.user?.display_name }}</p>
              <p class="rail__tag">我 · {{ meScore }}/3</p>
            </div>
          </div>
          <ul class="rail__checks">
            <li
              v-for="it in items"
              :key="it.key"
              class="check"
              :class="{ 'check--on': today.me.done[it.key] }"
            >
              <span class="check__mark">{{ today.me.done[it.key] ? '✓' : '·' }}</span>
              <span class="check__label">{{ it.label }}</span>
            </li>
          </ul>
          <div class="rail__metrics">
            <div>
              <span class="rail__m-k">kcal</span>
              <strong>{{ mealKcal }}</strong>
            </div>
            <div>
              <span class="rail__m-k">水</span>
              <strong>{{ waterDay?.total_ml ?? today.me.water.total_ml }}</strong>
            </div>
            <div>
              <span class="rail__m-k">练</span>
              <strong>{{ today.me.workouts.length }}</strong>
            </div>
          </div>
        </article>

        <div class="duo__vs" aria-hidden="true">
          <span>双</span>
        </div>

        <article class="rail" :class="`rail--${today.partner.user_id}`">
          <div class="rail__who">
            <span class="rail__emoji">{{ partnerPersona?.emoji }}</span>
            <div>
              <p class="rail__name">{{ today.partner.display_name }}</p>
              <p class="rail__tag">对方 · {{ partnerScore }}/3</p>
            </div>
          </div>
          <ul class="rail__checks">
            <li
              v-for="it in items"
              :key="it.key"
              class="check"
              :class="{ 'check--on': today.partner.done[it.key] }"
            >
              <span class="check__mark">{{ today.partner.done[it.key] ? '✓' : '·' }}</span>
              <span class="check__label">{{ it.label }}</span>
            </li>
          </ul>
          <div class="rail__metrics">
            <div>
              <span class="rail__m-k">kcal</span>
              <strong>{{ partnerMealKcal }}</strong>
            </div>
            <div>
              <span class="rail__m-k">水</span>
              <strong>{{ today.partner.water.total_ml }}</strong>
            </div>
            <div>
              <span class="rail__m-k">练</span>
              <strong>{{ today.partner.workouts.length }}</strong>
            </div>
          </div>
        </article>
      </div>

      <p v-else class="duo__loading">同步今日进度…</p>
    </section>

    <router-link
      v-if="dailyReport"
      :to="{ name: 'report', query: { kind: 'daily', period: date } }"
      class="today__report"
    >
      <div>
        <p class="fit-section-label">今日报告</p>
        <p class="today__report-text">{{ reportExcerpt }}…</p>
      </div>
      <span class="today__report-go">→</span>
    </router-link>

    <div class="today__stats">
      <div class="stat">
        <p class="stat__k">我的摄入</p>
        <p class="stat__v cal">{{ mealKcal }}</p>
        <p class="stat__u">kcal</p>
      </div>
      <div class="stat">
        <p class="stat__k">我的饮水</p>
        <p class="stat__v water">{{ waterDay?.total_ml ?? today?.me.water.total_ml ?? 0 }}</p>
        <p class="stat__u">/ {{ waterTargetMl ?? '—' }} ml</p>
      </div>
      <div class="stat">
        <p class="stat__k">我的运动</p>
        <p class="stat__v work">{{ today?.me.workouts.length ?? 0 }}</p>
        <p class="stat__u">条记录</p>
      </div>
    </div>

    <details v-if="meEnergy" class="energy-ledger">
      <summary class="energy-ledger__sum">
        <span class="energy-ledger__title">能量账本</span>
        <span class="energy-ledger__badge">
          {{
            meEnergy.empty || !meEnergy.meals_complete
              ? energySurplusTip
              : `${energySurplusTip} kcal`
          }}
        </span>
      </summary>
      <div class="energy-ledger__body">
        <dl class="energy-ledger__grid">
          <div>
            <dt>摄入</dt>
            <dd :class="{ 'energy-ledger__warn': intakeOverCap }">{{ meEnergy.intake_kcal }}</dd>
          </div>
          <div>
            <dt>运动消耗</dt>
            <dd>{{ meEnergy.burn_kcal }}</dd>
          </div>
          <div>
            <dt>基础代谢</dt>
            <dd>{{ meEnergy.bmr }}</dd>
          </div>
          <div>
            <dt>净平衡</dt>
            <dd>{{ energySurplusTip }}</dd>
          </div>
        </dl>
        <p v-if="meEnergy.empty" class="energy-ledger__eq energy-ledger__soft">
          今天还没记餐/水/运动，缺口贡献按 0 计（不算进计划进度）
        </p>
        <p v-else-if="!meEnergy.meals_complete" class="energy-ledger__eq energy-ledger__soft">
          早午晚记齐后才计算热量缺口；当前缺口贡献 0
        </p>
        <p v-else class="energy-ledger__eq">
          {{ meEnergy.intake_kcal }} − {{ meEnergy.burn_kcal }} − {{ meEnergy.bmr }} =
          {{ energySurplusTip }} kcal
        </p>
        <ul class="energy-ledger__plan">
          <li>
            计划日均缺口
            <strong>{{ meEnergy.daily_deficit_target }}</strong>
            kcal；今日缺口贡献
            <strong>{{ deficitContribKcal }}</strong>
            kcal
            <span
              v-if="
                meEnergy.meals_complete &&
                meEnergy.daily_deficit_target > 0 &&
                deficitContribKcal < meEnergy.daily_deficit_target
              "
              class="energy-ledger__soft"
            >
              （还差 {{ meEnergy.daily_deficit_target - deficitContribKcal }}）
            </span>
          </li>
          <li v-if="meEnergy.daily_kcal_cap != null" :class="{ 'energy-ledger__warn-line': intakeOverCap }">
            日摄入上限 <strong>{{ meEnergy.daily_kcal_cap }}</strong> kcal
            <template v-if="intakeOverCap">
              — 已超 {{ intakeOverCapBy }} kcal
            </template>
            <template v-else> — 未超顶</template>
          </li>
          <li v-else class="energy-ledger__soft">未设置日摄入上限（仅按缺口目标参考）</li>
        </ul>
      </div>
    </details>

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
          <section class="workout-panel">
            <header class="workout-panel__head">
              <div>
                <p class="fit-section-label">Movement</p>
                <h2>今日运动</h2>
                <p class="workout-panel__sub">
                  {{ today.me.workouts.length ? `已记 ${today.me.workouts.length} 条` : '还没动起来' }}
                </p>
              </div>
              <button type="button" class="workout-panel__cta" @click="goWorkout">记录</button>
            </header>
            <ul v-if="today.me.workouts.length" class="workout-panel__list">
              <li v-for="w in today.me.workouts" :key="w.id">
                <span>{{ formatWorkoutSummary(w) }}</span>
                <time>{{ w.created_at.slice(11, 16) }}</time>
              </li>
            </ul>
            <p v-else class="empty">点右上角用弹窗快速记有氧 / 力量</p>
          </section>
        </template>
        <van-empty v-else description="暂无数据" />
      </van-pull-refresh>
    </main>
  </div>
</template>

<style scoped>
.today {
  min-height: 100%;
  padding: 8px 14px 28px;
}

.duo {
  position: relative;
  overflow: hidden;
  border-radius: 28px;
  padding: 20px 16px 18px;
  margin-bottom: 14px;
  color: var(--ink);
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--primary) 18%, var(--card)) 0%, var(--card) 48%),
    var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  animation: duo-in 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.duo__glow {
  position: absolute;
  width: 180px;
  height: 180px;
  right: -40px;
  top: -50px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--hero-glow), transparent 70%);
  pointer-events: none;
}

.duo__head {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 18px;
}

.duo__greet {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.duo__date {
  margin: 6px 0 0;
  font-size: clamp(1.35rem, 5.5vw, 1.7rem);
  font-weight: 700;
  letter-spacing: -0.03em;
}

.duo__ring {
  flex-shrink: 0;
  width: 62px;
  height: 62px;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  background:
    radial-gradient(circle at center, var(--card) 56%, transparent 57%),
    conic-gradient(var(--primary) var(--p), var(--line) 0);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--primary) 25%, transparent);
}

.duo__ring-n {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 700;
  line-height: 1;
}

.duo__ring-d {
  font-size: 10px;
  color: var(--muted);
  font-weight: 600;
}

.duo__rails {
  position: relative;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.duo__vs {
  position: absolute;
  left: 50%;
  top: 42%;
  transform: translate(-50%, -50%);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  background: var(--card);
  border: 1px solid var(--line);
  color: var(--primary);
  z-index: 2;
  box-shadow: var(--shadow-sm);
}

.rail {
  position: relative;
  padding: 12px 10px 12px;
  border-radius: 18px;
  background: color-mix(in srgb, var(--bg) 65%, transparent);
  border: 1px solid var(--line);
  animation: rail-in 0.5s ease both;
}

.rail:nth-child(3) {
  animation-delay: 0.08s;
}

.rail--dragon {
  background: linear-gradient(160deg, rgba(24, 26, 31, 0.92), rgba(30, 26, 22, 0.88));
  border-color: rgba(232, 196, 138, 0.22);
  color: #f3efe8;
}

.rail--dragon .rail__tag,
.rail--dragon .rail__m-k,
.rail--dragon .check:not(.check--on) .check__label {
  color: #9a948a;
}

.rail--dragon .check {
  background: rgba(255, 255, 255, 0.04);
}

.rail--dragon .check--on {
  background: rgba(232, 196, 138, 0.16);
  color: #e8c48a;
}

.rail--leaf {
  background: linear-gradient(160deg, rgba(255, 240, 246, 0.95), rgba(255, 250, 251, 0.9));
  border-color: rgba(232, 93, 142, 0.22);
  color: #2a1820;
}

.rail--leaf .check--on {
  background: rgba(232, 93, 142, 0.14);
  color: #c94474;
}

html[data-persona='dragon'] .rail--leaf {
  background: linear-gradient(160deg, rgba(60, 30, 42, 0.55), rgba(40, 24, 32, 0.7));
  border-color: rgba(232, 93, 142, 0.28);
  color: #fce8f0;
}

html[data-persona='dragon'] .rail--leaf .rail__tag,
html[data-persona='dragon'] .rail--leaf .rail__m-k {
  color: #c9a0b0;
}

html[data-persona='leaf'] .rail--dragon {
  background: linear-gradient(160deg, #1a1c22, #14151a);
  border-color: rgba(232, 196, 138, 0.28);
}

.rail__who {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.rail__emoji {
  font-size: 1.35rem;
  line-height: 1;
}

.rail__name {
  margin: 0;
  font-size: 14px;
  font-weight: 800;
  line-height: 1.2;
}

.rail__tag {
  margin: 2px 0 0;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
}

.rail__checks {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
  display: grid;
  gap: 5px;
}

.check {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: color-mix(in srgb, var(--line) 55%, transparent);
  color: var(--muted);
}

.check--on {
  background: var(--primary-soft);
  color: var(--primary-dark);
}

.check__mark {
  width: 12px;
  text-align: center;
  font-family: var(--font-display);
}

.rail__metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 4px;
  padding-top: 8px;
  border-top: 1px dashed color-mix(in srgb, currentColor 18%, transparent);
}

.rail__metrics > div {
  text-align: center;
}

.rail__m-k {
  display: block;
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 2px;
}

.rail__metrics strong {
  font-family: var(--font-display);
  font-size: 13px;
  font-weight: 700;
}

.duo__loading {
  margin: 12px 0 0;
  font-size: 13px;
  color: var(--muted);
}

.today__report {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
  text-decoration: none;
  color: inherit;
  border-radius: var(--radius);
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.today__report-text {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 1.45;
  color: var(--muted);
  font-weight: 600;
}

.today__report-go {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--primary-soft);
  color: var(--primary-dark);
  font-weight: 800;
}

.today__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.stat {
  padding: 14px 8px;
  text-align: center;
  border-radius: 18px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.stat__k {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--muted);
}

.stat__v {
  margin: 6px 0 0;
  font-family: var(--font-display);
  font-size: 1.25rem;
  font-weight: 700;
  line-height: 1;
}

.stat__v.cal {
  color: var(--cal);
}
.stat__v.water {
  color: var(--water);
}
.stat__v.work {
  color: var(--workout);
}

.stat__u {
  margin: 4px 0 0;
  font-size: 10px;
  color: var(--muted);
  font-weight: 600;
}

.energy-ledger {
  margin-bottom: 16px;
  border-radius: 20px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.energy-ledger__sum {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 14px 16px;
  cursor: pointer;
  list-style: none;
  font-weight: 700;
}

.energy-ledger__sum::-webkit-details-marker {
  display: none;
}

.energy-ledger__title {
  font-size: 14px;
}

.energy-ledger__badge {
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary-dark);
}

.energy-ledger__body {
  padding: 0 16px 16px;
  border-top: 1px solid var(--line);
}

.energy-ledger__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px 12px;
  margin: 14px 0 0;
  padding: 0;
}

.energy-ledger__grid > div {
  margin: 0;
}

.energy-ledger__grid dt {
  margin: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--muted);
}

.energy-ledger__grid dd {
  margin: 4px 0 0;
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 700;
}

.energy-ledger__eq {
  margin: 12px 0 0;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.45;
  color: var(--muted);
}

.energy-ledger__plan {
  list-style: none;
  margin: 12px 0 0;
  padding: 12px 0 0;
  border-top: 1px dashed var(--line);
  display: grid;
  gap: 8px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.45;
}

.energy-ledger__plan strong {
  font-family: var(--font-display);
  font-weight: 700;
}

.energy-ledger__soft {
  color: var(--muted);
  font-weight: 600;
}

.energy-ledger__warn,
.energy-ledger__warn-line {
  color: var(--cal);
}

.energy-ledger__warn-line strong {
  color: var(--cal);
}

.workout-panel {
  margin-bottom: 14px;
  padding: 18px 16px;
  border-radius: 24px;
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--workout) 14%, var(--card)), var(--card) 52%);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.workout-panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}

.workout-panel__head h2 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 700;
}

.workout-panel__sub {
  margin: 6px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

.workout-panel__cta {
  border: none;
  background: var(--workout-soft);
  color: var(--workout);
  font-weight: 800;
  font-size: 13px;
  padding: 10px 16px;
  border-radius: 999px;
  cursor: pointer;
}

.workout-panel__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.workout-panel__list li {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 0;
  border-top: 1px solid var(--line);
  font-size: 14px;
  font-weight: 600;
}

.workout-panel__list time {
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

@keyframes duo-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes rail-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
</style>
