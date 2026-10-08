<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { showFailToast } from 'vant'
import CoupleDayCell from '@/components/CoupleDayCell.vue'
import WeekPlanEditor from '@/components/WeekPlanEditor.vue'
import { fetchCalendarMonth, type CalendarDay } from '@/api/calendar'
const router = useRouter()
const now = new Date()
const year = ref(now.getFullYear())
const month = ref(now.getMonth() + 1)
const days = ref<CalendarDay[]>([])
const showPlan = ref(false)

const weekStart = computed(() => {
  const d = new Date(year.value, month.value - 1, 1)
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  return d.toISOString().slice(0, 10)
})

const dayMap = computed(() => new Map(days.value.map((d) => [d.date, d])))

function padMonth(y: number, m: number) {
  const first = new Date(y, m - 1, 1)
  const last = new Date(y, m, 0)
  const cells: { date: string; inMonth: boolean }[] = []
  const startPad = first.getDay() === 0 ? 6 : first.getDay() - 1
  for (let i = startPad; i > 0; i--) {
    const d = new Date(y, m - 1, 1 - i)
    cells.push({ date: d.toISOString().slice(0, 10), inMonth: false })
  }
  for (let d = 1; d <= last.getDate(); d++) {
    const iso = new Date(y, m - 1, d).toISOString().slice(0, 10)
    cells.push({ date: iso, inMonth: true })
  }
  while (cells.length % 7 !== 0) {
    const d = new Date(y, m - 1, last.getDate() + (cells.length - startPad - last.getDate()) + 1)
    cells.push({ date: d.toISOString().slice(0, 10), inMonth: false })
  }
  return cells
}

const grid = computed(() => padMonth(year.value, month.value))

async function load() {
  try {
    const data = await fetchCalendarMonth(year.value, month.value)
    days.value = data.days
  } catch {
    showFailToast('加载日历失败')
  }
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

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="calendar-page">
    <header class="calendar-page__bar">
      <button type="button" @click="prevMonth">‹</button>
      <h1>{{ year }}年{{ month }}月</h1>
      <button type="button" @click="nextMonth">›</button>
      <van-button size="small" type="primary" @click="showPlan = true">周计划</van-button>
    </header>

    <p class="calendar-page__legend">
      上半 🐉 / 下半 🍃 ·
      <span class="lg full">全达成</span>
      <span class="lg partial">部分</span>
      <span class="lg none">未完成</span>
    </p>

    <div class="calendar-page__weekdays">
      <span v-for="w in ['一', '二', '三', '四', '五', '六', '日']" :key="w">{{ w }}</span>
    </div>

    <div class="calendar-page__grid">
      <button
        v-for="cell in grid"
        :key="cell.date"
        type="button"
        class="calendar-page__cell"
        :class="{ 'calendar-page__cell--muted': !cell.inMonth }"
        @click="openDay(cell.date)"
      >
        <span class="calendar-page__num">{{ cell.date.slice(8) }}</span>
        <CoupleDayCell
          v-if="dayMap.get(cell.date)"
          :dragon="dayMap.get(cell.date)!.dragon"
          :leaf="dayMap.get(cell.date)!.leaf"
        />
      </button>
    </div>

    <WeekPlanEditor v-model:show="showPlan" :week-start="weekStart" @saved="load" />
  </div>
</template>

<style scoped>
.calendar-page {
  padding: 16px 12px 32px;
}

.calendar-page__bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.calendar-page__bar h1 {
  flex: 1;
  margin: 0;
  font-size: 1.1rem;
  text-align: center;
}

.calendar-page__bar button {
  border: none;
  background: transparent;
  font-size: 1.5rem;
  cursor: pointer;
}

.calendar-page__legend {
  font-size: 12px;
  color: var(--muted);
  margin: 0 0 12px;
}

.lg {
  margin-left: 8px;
  padding: 2px 6px;
  border-radius: 4px;
}

.lg.full {
  background: #3d8b6e;
  color: #fff;
}

.lg.partial {
  background: #d4a017;
  color: #fff;
}

.lg.none {
  background: #e8e4de;
}

.calendar-page__weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
  margin-bottom: 4px;
}

.calendar-page__grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.calendar-page__cell {
  border: none;
  background: var(--card);
  border-radius: 8px;
  padding: 4px;
  min-height: 56px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

.calendar-page__cell--muted {
  opacity: 0.45;
}

.calendar-page__num {
  display: block;
  font-size: 11px;
  font-weight: 700;
  text-align: left;
}
</style>
