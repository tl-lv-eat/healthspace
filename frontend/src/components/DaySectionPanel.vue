<script setup lang="ts">
import { computed } from 'vue'
import type { DayStatus } from '@/api/calendar'
import type { DaySection } from '@/api/today'
import { personaById } from '@/constants/personas'
import { formatWorkoutSummary } from '@/api/workouts'

const props = defineProps<{
  section: DaySection
  displayName: string
  status?: DayStatus
}>()

const doneItems = [
  { key: 'meal' as const, label: '饮食' },
  { key: 'water' as const, label: '饮水' },
  { key: 'workout' as const, label: '运动' },
]

function formatTime(iso: string) {
  return iso.length >= 16 ? iso.slice(11, 16) : iso
}

function levelLabel(st?: DayStatus) {
  if (!st) return ''
  if (st.level === 'full') return '达标'
  if (st.level === 'partial') return '部分'
  return '未达标'
}

const mealKcal = computed(() =>
  props.section.meals.reduce((s, m) => s + (m.user_kcal || 0), 0),
)

const energy = computed(() => props.section.energy)

const energySurplusTip = computed(() => {
  const e = energy.value
  if (!e) return '—'
  if (e.empty) return '未记录'
  if (!e.meals_complete) return '饮食未记齐'
  const s = e.surplus_kcal ?? 0
  if (s > 0) return `盈余 +${s}`
  if (s < 0) return `缺口 ${Math.abs(s)}`
  return '持平 0'
})

const deficitContribKcal = computed(() => {
  const e = energy.value
  if (!e || e.empty || !e.meals_complete) return 0
  if (typeof e.deficit_contrib === 'number') return Math.max(0, e.deficit_contrib)
  return Math.max(0, -(e.surplus_kcal ?? 0))
})

const intakeOverCap = computed(() => {
  const e = energy.value
  if (!e || e.daily_kcal_cap == null) return false
  return e.intake_kcal > e.daily_kcal_cap
})

const intakeOverCapBy = computed(() => {
  const e = energy.value
  if (!e || e.daily_kcal_cap == null) return 0
  return Math.max(0, e.intake_kcal - e.daily_kcal_cap)
})

const persona = computed(() => personaById(props.section.user_id))
</script>

<template>
  <article class="col" :class="`col--${section.user_id}`">
    <header class="col__head">
      <span class="col__emoji">{{ persona?.emoji }}</span>
      <div>
        <h2>{{ displayName }}</h2>
        <p v-if="status" class="col__level">{{ levelLabel(status) }}</p>
      </div>
    </header>

    <ul class="col__done">
      <li
        v-for="it in doneItems"
        :key="it.key"
        class="check"
        :class="{ 'check--on': section.done[it.key] }"
      >
        <span class="check__mark">{{ section.done[it.key] ? '✓' : '·' }}</span>
        <span>{{ it.label }}</span>
      </li>
    </ul>

    <section class="block">
      <h3 class="block__title">饮食</h3>
      <p class="block__meta">合计 {{ mealKcal }} kcal · {{ section.meals.length }} 条</p>
      <ul v-if="section.meals.length" class="block__list">
        <li v-for="m in section.meals" :key="m.id">
          <span class="block__main">{{ m.food_summary || '（无描述）' }}</span>
          <span class="block__side">{{ m.user_kcal }} kcal</span>
        </li>
      </ul>
      <p v-else class="block__empty">无记录</p>
    </section>

    <section class="block">
      <h3 class="block__title">饮水</h3>
      <p class="block__meta">
        {{ section.water.total_ml }} / {{ section.water.target_ml }} ml
      </p>
      <ul v-if="section.water.entries.length" class="block__list block__list--timeline">
        <li v-for="e in section.water.entries" :key="e.id">
          <time>{{ formatTime(e.created_at) }}</time>
          <span>+{{ e.amount_ml }} ml</span>
        </li>
      </ul>
      <p v-else class="block__empty">无明细</p>
    </section>

    <section class="block">
      <h3 class="block__title">运动</h3>
      <ul v-if="section.workouts.length" class="block__list">
        <li v-for="w in section.workouts" :key="w.id">
          <span class="block__main">{{ formatWorkoutSummary(w) }}</span>
          <time class="block__side">{{ formatTime(w.created_at) }}</time>
        </li>
      </ul>
      <p v-else class="block__empty">无记录</p>
    </section>

    <details v-if="energy" class="energy">
      <summary class="energy__sum">
        <span>能量账本</span>
        <span class="energy__badge">
          {{
            energy.empty || !energy.meals_complete
              ? energySurplusTip
              : `${energySurplusTip} kcal`
          }}
        </span>
      </summary>
      <div class="energy__body">
        <dl class="energy__grid">
          <div>
            <dt>摄入</dt>
            <dd :class="{ 'energy__warn': intakeOverCap }">{{ energy.intake_kcal }}</dd>
          </div>
          <div>
            <dt>运动消耗</dt>
            <dd>{{ energy.burn_kcal }}</dd>
          </div>
          <div>
            <dt>基础代谢</dt>
            <dd>{{ energy.bmr }}</dd>
          </div>
          <div>
            <dt>净平衡</dt>
            <dd>{{ energySurplusTip }}</dd>
          </div>
        </dl>
        <p v-if="energy.empty" class="energy__eq energy__soft">
          今天还没记餐/水/运动，缺口贡献按 0 计（不算进计划进度）
        </p>
        <p v-else-if="!energy.meals_complete" class="energy__eq energy__soft">
          早午晚记齐后才计算热量缺口；当前缺口贡献 0
        </p>
        <p v-else class="energy__eq">
          {{ energy.intake_kcal }} − {{ energy.burn_kcal }} − {{ energy.bmr }} =
          {{ energySurplusTip }} kcal
        </p>
        <ul class="energy__plan">
          <li>
            计划日均缺口
            <strong>{{ energy.daily_deficit_target }}</strong>
            kcal；今日缺口贡献
            <strong>{{ deficitContribKcal }}</strong>
            kcal
            <span
              v-if="
                energy.meals_complete &&
                energy.daily_deficit_target > 0 &&
                deficitContribKcal < energy.daily_deficit_target
              "
              class="energy__soft"
            >
              （还差 {{ energy.daily_deficit_target - deficitContribKcal }}）
            </span>
          </li>
          <li v-if="energy.daily_kcal_cap != null" :class="{ 'energy__warn-line': intakeOverCap }">
            日摄入上限 <strong>{{ energy.daily_kcal_cap }}</strong> kcal
            <template v-if="intakeOverCap"> — 已超 {{ intakeOverCapBy }} kcal</template>
            <template v-else> — 未超顶</template>
          </li>
          <li v-else class="energy__soft">未设置日摄入上限（仅按缺口目标参考）</li>
        </ul>
      </div>
    </details>
  </article>
</template>

<style scoped>
.col {
  padding: 14px 12px 16px;
  border-radius: 20px;
  border: 1px solid var(--line);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  min-width: 0;
}

.col--dragon {
  background: linear-gradient(160deg, rgba(24, 26, 31, 0.92), var(--card));
  border-color: rgba(232, 196, 138, 0.22);
}

.col--leaf {
  background: linear-gradient(160deg, rgba(252, 228, 238, 0.7), var(--card));
  border-color: rgba(232, 93, 142, 0.22);
}

.col__head {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}

.col__emoji {
  font-size: 1.5rem;
  line-height: 1;
}

.col__head h2 {
  margin: 0;
  font-size: 1rem;
  font-weight: 800;
}

.col__level {
  margin: 2px 0 0;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
}

.col__done {
  list-style: none;
  margin: 0 0 14px;
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

.block {
  margin-bottom: 12px;
}

.block__title {
  margin: 0;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.03em;
}

.block__meta {
  margin: 4px 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--muted);
}

.block__list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.block__list li {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px solid var(--line);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.35;
}

.block__main {
  flex: 1;
  min-width: 0;
}

.block__side {
  flex-shrink: 0;
  color: var(--muted);
  font-size: 11px;
}

.block__list--timeline li {
  justify-content: flex-start;
  gap: 10px;
}

.block__list--timeline time {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  color: var(--water);
  min-width: 36px;
}

.block__empty {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  font-weight: 500;
}

.energy {
  margin-top: 4px;
  border-radius: 16px;
  background: color-mix(in srgb, var(--bg) 40%, var(--card));
  border: 1px solid var(--line);
  overflow: hidden;
}

.energy__sum {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  list-style: none;
  font-size: 12px;
  font-weight: 800;
}

.energy__sum::-webkit-details-marker {
  display: none;
}

.energy__badge {
  font-family: var(--font-display);
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary-dark);
}

.energy__body {
  padding: 0 12px 12px;
  border-top: 1px solid var(--line);
}

.energy__grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px 10px;
  margin: 10px 0 0;
  padding: 0;
}

.energy__grid dt {
  margin: 0;
  font-size: 9px;
  font-weight: 700;
  color: var(--muted);
}

.energy__grid dd {
  margin: 3px 0 0;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 700;
}

.energy__eq {
  margin: 10px 0 0;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.45;
  color: var(--muted);
}

.energy__plan {
  list-style: none;
  margin: 10px 0 0;
  padding: 10px 0 0;
  border-top: 1px dashed var(--line);
  display: grid;
  gap: 6px;
  font-size: 11px;
  font-weight: 600;
  line-height: 1.45;
}

.energy__soft {
  color: var(--muted);
}

.energy__warn,
.energy__warn-line {
  color: var(--cal);
}
</style>
