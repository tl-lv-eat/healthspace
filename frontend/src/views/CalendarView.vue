<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showFailToast } from 'vant'
import CoupleDayCell from '@/components/CoupleDayCell.vue'
import WeekPlanEditor from '@/components/WeekPlanEditor.vue'
import {
  fetchCalendarMonth,
  type CalendarDay,
  type WeekProgress,
} from '@/api/calendar'
import { listWeekPlans, type WeekPlan } from '@/api/weekPlans'
import { PERSONAS, type PersonaId } from '@/constants/personas'
import { formatDateLocal } from '@/api/today'

const router = useRouter()
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const days = ref<CalendarDay[]>([])
const weekProgress = ref<WeekProgress | null>(null)
const plans = ref<WeekPlan[]>([])
const showPlan = ref(false)
const editingPlan = ref<WeekPlan | null>(null)
const defaultStart = ref('')
const initialTargetUserId = ref<PersonaId | undefined>(undefined)

const dayMap = computed(() => new Map(days.value.map((d) => [d.date, d])))

function todayIso() {
  return formatDateLocal()
}

function padMonth(y: number, m: number) {
  const first = new Date(y, m - 1, 1)
  const last = new Date(y, m, 0)
  const cells: { date: string; inMonth: boolean }[] = []
  const startPad = first.getDay() === 0 ? 6 : first.getDay() - 1
  for (let i = startPad; i > 0; i--) {
    const d = new Date(y, m - 1, 1 - i)
    cells.push({ date: formatDateLocal(d), inMonth: false })
  }
  for (let d = 1; d <= last.getDate(); d++) {
    cells.push({ date: formatDateLocal(new Date(y, m - 1, d)), inMonth: true })
  }
  while (cells.length % 7 !== 0) {
    const extra = cells.length - startPad - last.getDate() + 1
    const d = new Date(y, m - 1, last.getDate() + extra)
    cells.push({ date: formatDateLocal(d), inMonth: false })
  }
  return cells
}

const grid = computed(() => padMonth(year.value, month.value))

const deficitPct = computed(() => {
  const p = weekProgress.value
  if (!p || !p.weekly_kcal_deficit_target) return 0
  return Math.min(100, Math.round((p.weekly_kcal_deficit_done / p.weekly_kcal_deficit_target) * 100))
})

const workoutPct = computed(() => {
  const p = weekProgress.value
  if (!p || !p.weekly_workout_sessions_target) return 0
  return Math.min(100, Math.round((p.weekly_workout_sessions_done / p.weekly_workout_sessions_target) * 100))
})

const progressLabel = computed(() => {
  const p = weekProgress.value
  if (!p?.start_date || !p?.end_date) return '当前计划联动'
  return `${p.start_date.slice(5)} → ${p.end_date.slice(5)}`
})

function monthQuery() {
  return `${year.value}-${String(month.value).padStart(2, '0')}`
}

function planCoversToday(p: WeekPlan) {
  const t = todayIso()
  const start = p.start_date || p.week_start
  const end = p.end_date || start
  return start <= t && t <= end
}

function planRange(p: WeekPlan) {
  const start = p.start_date || p.week_start
  const end = p.end_date || start
  return `${start.slice(5)} → ${end.slice(5)}`
}

function plansForPersona(id: PersonaId) {
  return plans.value
    .filter((p) => p.user_id === id)
    .sort((a, b) => (b.start_date || b.week_start).localeCompare(a.start_date || a.week_start))
}

const hasAnyPlans = computed(() => plans.value.length > 0)

async function loadPlans() {
  try {
    plans.value = await listWeekPlans(monthQuery())
  } catch {
    plans.value = []
  }
}

async function load() {
  try {
    const data = await fetchCalendarMonth(year.value, month.value)
    days.value = data.days
    weekProgress.value = data.my_week_progress ?? null
  } catch {
    showFailToast('加载日历失败')
  }
  await loadPlans()
}

function prevMonth() {
  if (month.value === 1) {
    month.value = 12
    year.value -= 1
  } else {
    month.value -= 1
  }
  void load()
}

function nextMonth() {
  if (month.value === 12) {
    month.value = 1
    year.value += 1
  } else {
    month.value += 1
  }
  void load()
}

function openDay(date: string) {
  void router.push({ name: 'calendar-day', params: { date } })
}

function openNewPlan(forPersona?: PersonaId) {
  editingPlan.value = null
  defaultStart.value = todayIso()
  initialTargetUserId.value = forPersona
  showPlan.value = true
}

function openEditPlan(p: WeekPlan) {
  editingPlan.value = p
  defaultStart.value = p.start_date || p.week_start
  initialTargetUserId.value = undefined
  showPlan.value = true
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="cal">
    <header class="cal__bar">
      <button type="button" class="cal__nav" @click="prevMonth">‹</button>
      <h1>{{ year }}年{{ month }}月</h1>
      <button type="button" class="cal__nav" @click="nextMonth">›</button>
    </header>

    <section v-if="weekProgress" class="cal__progress">
      <div class="cal__progress-head">
        <p class="fit-section-label">{{ progressLabel }}</p>
        <span>饮水 {{ weekProgress.water_target_ml }} ml/日</span>
      </div>
      <div class="cal__meter">
        <div class="cal__meter-top">
          <strong>热量缺口</strong>
          <span>{{ weekProgress.weekly_kcal_deficit_done }} / {{ weekProgress.weekly_kcal_deficit_target }}</span>
        </div>
        <div class="cal__track"><i :style="{ width: `${deficitPct}%` }" /></div>
      </div>
      <div class="cal__meter">
        <div class="cal__meter-top">
          <strong>运动次数</strong>
          <span>{{ weekProgress.weekly_workout_sessions_done }} / {{ weekProgress.weekly_workout_sessions_target }} 天</span>
        </div>
        <div class="cal__track cal__track--wo"><i :style="{ width: `${workoutPct}%` }" /></div>
      </div>
      <p v-if="weekProgress.target_weight_kg" class="cal__weight">
        体重目标 {{ weekProgress.target_weight_kg }} kg
      </p>
    </section>

    <p class="cal__legend">
      上 🐉 / 下 🍃 ·
      <span class="lg full">饮水达标且未热量盈余</span>
      <span class="lg partial">一项未达标</span>
      <span class="lg none">两项未达标/未记</span>
    </p>

    <div class="cal__weekdays">
      <span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span>
    </div>

    <div class="cal__grid">
      <button
        v-for="cell in grid"
        :key="cell.date"
        type="button"
        class="cal__cell"
        :class="{ 'cal__cell--muted': !cell.inMonth }"
        @click="openDay(cell.date)"
      >
        <span class="cal__num">{{ Number(cell.date.slice(8)) }}</span>
        <CoupleDayCell
          v-if="dayMap.get(cell.date)"
          :dragon="dayMap.get(cell.date)!.dragon"
          :leaf="dayMap.get(cell.date)!.leaf"
        />
      </button>
    </div>

    <p v-if="!hasAnyPlans" class="cal__empty cal__empty--month">
      本月还没有计划。在下方按 🐉 / 🍃 新建一段，日历会按区间联动。
    </p>

    <section
      v-for="persona in PERSONAS"
      :key="persona.id"
      class="cal__plans"
      :class="`cal__plans--${persona.id}`"
    >
      <div class="cal__plans-head">
        <p class="cal__plans-title">
          <span class="cal__plans-emoji">{{ persona.emoji }}</span>
          {{ persona.label }} · 本月计划
        </p>
        <button type="button" class="cal__add" @click="openNewPlan(persona.id)">+ 新建</button>
      </div>
      <p v-if="!plansForPersona(persona.id).length" class="cal__empty cal__empty--persona">
        暂无 {{ persona.label }} 的计划。
      </p>
      <button
        v-for="p in plansForPersona(persona.id)"
        :key="p.id ?? `${p.user_id}-${p.start_date}`"
        type="button"
        class="cal__plan-card"
        :class="{ 'cal__plan-card--active': planCoversToday(p) }"
        @click="openEditPlan(p)"
      >
        <div class="cal__plan-top">
          <strong>{{ p.title?.trim() || '未命名计划' }}</strong>
          <span v-if="planCoversToday(p)" class="cal__badge">进行中</span>
          <span class="cal__days">{{ p.period_days || '—' }} 天</span>
        </div>
        <p class="cal__plan-range">{{ planRange(p) }}</p>
        <div class="cal__plan-meta">
          <span>饮水 {{ p.water_target_ml }} ml</span>
          <span>缺口 {{ p.weekly_kcal_deficit }} kcal</span>
          <span>
            上限
            {{
              p.daily_kcal_cap != null && p.daily_kcal_cap > 0 ? `${p.daily_kcal_cap} kcal/日` : '—'
            }}
          </span>
        </div>
      </button>
    </section>

    <WeekPlanEditor
      v-model:show="showPlan"
      :plan="editingPlan"
      :default-start="defaultStart"
      :initial-target-user-id="initialTargetUserId"
      @saved="load"
    />
  </div>
</template>

<style scoped>
.cal {
  padding: 12px 12px 32px;
}

.cal__bar {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}

.cal__bar h1 {
  flex: 1;
  margin: 0;
  font-size: 1.15rem;
  text-align: center;
  font-weight: 800;
}

.cal__nav {
  border: none;
  background: var(--card);
  width: 36px;
  height: 36px;
  border-radius: 12px;
  font-size: 1.35rem;
  cursor: pointer;
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}

.cal__progress {
  margin-bottom: 14px;
  padding: 14px 14px 12px;
  border-radius: 20px;
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--primary) 12%, var(--card)), var(--card));
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.cal__progress-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.cal__meter {
  margin-bottom: 10px;
}

.cal__meter-top {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  margin-bottom: 4px;
}

.cal__meter-top strong {
  font-weight: 800;
}

.cal__track {
  height: 8px;
  border-radius: 999px;
  background: var(--line);
  overflow: hidden;
}

.cal__track i {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, var(--primary), color-mix(in srgb, var(--primary) 60%, #fff));
  border-radius: inherit;
}

.cal__track--wo i {
  background: linear-gradient(90deg, var(--workout), color-mix(in srgb, var(--workout) 55%, #fff));
}

.cal__weight {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.cal__legend {
  font-size: 11px;
  color: var(--muted);
  margin: 0 0 10px;
  line-height: 1.6;
}

.lg {
  display: inline-block;
  margin: 2px 4px 0 0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 700;
}

.lg.full {
  background: #2f9e6b;
  color: #fff;
}

.lg.partial {
  background: #e6a23c;
  color: #fff;
}

.lg.none {
  background: #d9d4cc;
  color: #444;
}

.cal__weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  margin-bottom: 4px;
}

.cal__grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 5px;
}

.cal__cell {
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 12px;
  padding: 5px;
  min-height: 58px;
  cursor: pointer;
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}

.cal__cell--muted {
  opacity: 0.4;
}

.cal__num {
  display: block;
  font-size: 11px;
  font-weight: 800;
  text-align: left;
  margin-bottom: 3px;
}

.cal__plans {
  margin-top: 18px;
}

.cal__plans--dragon {
  margin-top: 22px;
}

.cal__plans-title {
  margin: 0;
  font-size: 13px;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 6px;
}

.cal__plans-emoji {
  font-size: 1.1rem;
  line-height: 1;
}

.cal__plans-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.cal__empty--month {
  margin-top: 22px;
}

.cal__empty--persona {
  padding: 12px 14px;
  margin-bottom: 4px;
  font-size: 12px;
}

.cal__add {
  border: none;
  background: var(--primary);
  color: var(--on-primary, #fff);
  font-weight: 800;
  font-size: 12px;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
}

.cal__empty {
  margin: 0;
  padding: 16px;
  font-size: 13px;
  color: var(--muted);
  background: var(--card);
  border-radius: 16px;
  border: 1px dashed var(--line);
  line-height: 1.5;
}

.cal__plan-card {
  display: block;
  width: 100%;
  text-align: left;
  border: 1px solid var(--line);
  background: var(--card);
  border-radius: 16px;
  padding: 14px;
  margin-bottom: 10px;
  cursor: pointer;
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}

.cal__plan-card--active {
  border-color: color-mix(in srgb, var(--primary) 55%, var(--line));
  background: linear-gradient(
    155deg,
    color-mix(in srgb, var(--primary) 14%, var(--card)),
    var(--card)
  );
}

.cal__plan-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.cal__plan-top strong {
  font-size: 15px;
  font-weight: 800;
  flex: 1;
  min-width: 0;
  text-align: left;
}

.cal__plan-range {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
}

.cal__badge {
  font-size: 10px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--primary);
  color: var(--on-primary, #fff);
}

.cal__days {
  margin-left: auto;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.cal__plan-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}
</style>
