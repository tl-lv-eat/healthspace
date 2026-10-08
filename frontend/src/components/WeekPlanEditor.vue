<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { showConfirmDialog, showFailToast, showSuccessToast } from 'vant'
import { deleteWeekPlan, fetchWeekPlan, saveWeekPlan, type WeekPlan } from '@/api/weekPlans'
import { PERSONAS, personaById, type PersonaId } from '@/constants/personas'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  show: boolean
  /** Prefill when creating / editing */
  plan?: WeekPlan | null
  /** Default start when creating */
  defaultStart?: string
  /** Prefill persona when creating (Task 8 calendar grouping) */
  initialTargetUserId?: PersonaId
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  saved: []
}>()

const auth = useAuthStore()

function todayIso() {
  const d = new Date()
  return d.toISOString().slice(0, 10)
}

function plusDays(iso: string, n: number) {
  const d = new Date(iso + 'T12:00:00')
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}

const planId = ref<number | null>(null)
const targetUserId = ref<PersonaId>('leaf')
const planTitle = ref('')
const planNote = ref('')
const dailyKcalCap = ref<string>('')
const startDate = ref(todayIso())
const endDate = ref(plusDays(todayIso(), 6))
const water = ref(2000)
const weeklyDeficit = ref(3500)
const weeklyWorkouts = ref(4)
const targetWeight = ref<string>('')
const loading = ref(false)

const isEdit = computed(() => planId.value != null)

const periodDays = computed(() => {
  const a = new Date(startDate.value + 'T12:00:00')
  const b = new Date(endDate.value + 'T12:00:00')
  const n = Math.round((b.getTime() - a.getTime()) / 86400000) + 1
  return Math.max(1, n)
})

const dailyDeficit = computed(() => Math.round(weeklyDeficit.value / periodDays.value))

const title = computed(() => (planId.value ? '编辑计划' : '新建计划'))

const ownerPersona = computed(() => personaById(targetUserId.value))

async function loadFromProps() {
  loading.value = true
  try {
    if (props.plan?.id) {
      planId.value = props.plan.id
      targetUserId.value = (props.plan.user_id as PersonaId) || 'leaf'
      planTitle.value = props.plan.title ?? ''
      planNote.value = props.plan.note ?? ''
      dailyKcalCap.value =
        props.plan.daily_kcal_cap != null && props.plan.daily_kcal_cap > 0
          ? String(props.plan.daily_kcal_cap)
          : ''
      startDate.value = props.plan.start_date || props.plan.week_start
      endDate.value = props.plan.end_date || plusDays(startDate.value, 6)
      water.value = props.plan.water_target_ml
      weeklyDeficit.value = props.plan.weekly_kcal_deficit ?? 3500
      weeklyWorkouts.value = props.plan.weekly_workout_sessions ?? 4
      targetWeight.value =
        props.plan.target_weight_kg != null && props.plan.target_weight_kg > 0
          ? String(props.plan.target_weight_kg)
          : ''
      return
    }
    planId.value = null
    const me = auth.user?.id as PersonaId | undefined
    targetUserId.value = props.initialTargetUserId ?? me ?? 'leaf'
    planTitle.value = ''
    planNote.value = ''
    dailyKcalCap.value = ''
    const start = props.defaultStart || todayIso()
    startDate.value = start
    endDate.value = plusDays(start, 6)
    water.value = 2000
    weeklyDeficit.value = 3500
    weeklyWorkouts.value = 4
    targetWeight.value = ''
    try {
      const covering = await fetchWeekPlan(start)
      if (covering.water_target_ml) water.value = covering.water_target_ml
    } catch {
      /* ignore */
    }
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.show, props.plan?.id, props.defaultStart, props.initialTargetUserId] as const,
  ([visible]) => {
    if (visible) void loadFromProps()
  },
)

function parseOptionalKcal(raw: string): number | null {
  const t = raw.trim()
  if (!t) return null
  const n = parseInt(t, 10)
  if (!Number.isFinite(n) || n <= 0) return NaN
  return n
}

async function onSave() {
  if (endDate.value < startDate.value) {
    showFailToast('结束日期不能早于开始')
    return
  }
  const cap = parseOptionalKcal(dailyKcalCap.value)
  if (Number.isNaN(cap)) {
    showFailToast('日摄入上限无效')
    return
  }
  const tw = targetWeight.value.trim()
  const twNum = tw ? parseFloat(tw) : null
  if (tw && (!Number.isFinite(twNum) || (twNum as number) <= 0)) {
    showFailToast('体重目标无效')
    return
  }
  const titleTrim = planTitle.value.trim()
  try {
    await saveWeekPlan({
      id: planId.value,
      target_user_id: targetUserId.value,
      start_date: startDate.value,
      end_date: endDate.value,
      week_start: startDate.value,
      title: titleTrim || null,
      note: planNote.value.trim(),
      daily_kcal_cap: cap,
      water_target_ml: water.value,
      weekly_kcal_deficit: weeklyDeficit.value,
      weekly_workout_sessions: weeklyWorkouts.value,
      target_weight_kg: twNum,
      meal_mode: 'three_main',
      workout_mode: 'any',
    })
    showSuccessToast('计划已保存')
    emit('saved')
    emit('update:show', false)
  } catch {
    showFailToast('保存失败')
  }
}

async function onDelete() {
  if (!planId.value) return
  try {
    await showConfirmDialog({ title: '删除计划', message: '确定删除这段计划？日历联动会失效。' })
  } catch {
    return
  }
  try {
    await deleteWeekPlan(planId.value)
    showSuccessToast('已删除')
    emit('saved')
    emit('update:show', false)
  } catch {
    showFailToast('删除失败')
  }
}
</script>

<template>
  <van-popup
    :show="show"
    position="bottom"
    round
    :style="{ maxHeight: '92%' }"
    @update:show="emit('update:show', $event)"
  >
    <div class="editor">
      <h3>{{ title }}</h3>
      <p class="editor__hint">
        选起止日期与目标。日历亮色：饮水达标且当日无热量盈余。期间缺口按天数均摊；日摄入上限仅作对照提示，不拦记账。
      </p>

      <div v-if="isEdit" class="editor__owner">
        <span class="editor__owner-label">计划所属</span>
        <span class="editor__owner-chip" :class="`editor__owner-chip--${targetUserId}`">
          {{ ownerPersona?.emoji }} {{ ownerPersona?.label }}
        </span>
      </div>
      <fieldset v-else class="editor__personas">
        <legend>为谁建计划</legend>
        <div class="editor__persona-row">
          <button
            v-for="p in PERSONAS"
            :key="p.id"
            type="button"
            class="editor__persona"
            :class="[
              `editor__persona--${p.id}`,
              { 'editor__persona--on': targetUserId === p.id },
            ]"
            @click="targetUserId = p.id"
          >
            <span class="editor__persona-emoji">{{ p.emoji }}</span>
            <span>{{ p.label }}</span>
          </button>
        </div>
      </fieldset>

      <label class="editor__field">
        <span>标题（可选）</span>
        <input v-model="planTitle" type="text" maxlength="128" placeholder="例如：国庆冲刺" />
      </label>
      <label class="editor__field">
        <span>备注</span>
        <textarea v-model="planNote" rows="3" placeholder="饮食、作息或提醒…" />
      </label>

      <div class="editor__row">
        <label class="editor__field">
          <span>开始日期</span>
          <input v-model="startDate" type="date" />
        </label>
        <label class="editor__field">
          <span>结束日期</span>
          <input v-model="endDate" type="date" />
        </label>
      </div>
      <p class="editor__period">共 {{ periodDays }} 天</p>

      <label class="editor__field">
        <span>日饮水目标 (ml)</span>
        <input v-model.number="water" type="number" min="500" step="100" />
      </label>
      <label class="editor__field">
        <span>期间热量缺口 (kcal)</span>
        <input v-model.number="weeklyDeficit" type="number" min="0" step="100" />
        <small>约 {{ dailyDeficit }} kcal/天（÷ {{ periodDays }}）· 驱动日历「无盈余」判定</small>
      </label>
      <label class="editor__field">
        <span>日摄入上限 (kcal，可选)</span>
        <input
          v-model="dailyKcalCap"
          type="number"
          min="800"
          step="50"
          placeholder="例如 1600"
        />
        <small>今日页对照提示；与缺口独立，不设则不显示上限</small>
      </label>
      <label class="editor__field">
        <span>期间运动次数</span>
        <input v-model.number="weeklyWorkouts" type="number" min="0" :max="periodDays" step="1" />
        <small>这段日子打算练几天</small>
      </label>
      <label class="editor__field">
        <span>体重目标 (kg，可选)</span>
        <input v-model="targetWeight" type="number" min="30" step="0.1" placeholder="例如 58.0" />
      </label>

      <van-button block type="primary" round :loading="loading" @click="onSave">保存计划</van-button>
      <van-button
        v-if="planId"
        block
        plain
        hairline
        round
        type="danger"
        class="editor__del"
        @click="onDelete"
      >
        删除计划
      </van-button>
    </div>
  </van-popup>
</template>

<style scoped>
.editor {
  padding: 20px 16px calc(28px + env(safe-area-inset-bottom));
  background: var(--bg);
  color: var(--ink);
}

.editor h3 {
  margin: 0 0 8px;
  font-size: 1.2rem;
  font-weight: 800;
}

.editor__hint {
  margin: 0 0 16px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--muted);
}

.editor__personas {
  margin: 0 0 14px;
  padding: 0;
  border: none;
}

.editor__personas legend {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
  padding: 0;
}

.editor__persona-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.editor__persona {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 48px;
  padding: 10px 12px;
  border: 2px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  color: var(--ink);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.editor__persona--on.editor__persona--dragon {
  border-color: rgba(232, 196, 138, 0.75);
  box-shadow: 0 0 0 1px rgba(232, 196, 138, 0.35);
}

.editor__persona--on.editor__persona--leaf {
  border-color: rgba(232, 93, 142, 0.65);
  box-shadow: 0 0 0 1px rgba(232, 93, 142, 0.25);
}

.editor__persona-emoji {
  font-size: 1.35rem;
  line-height: 1;
}

.editor__owner {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.editor__owner-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
}

.editor__owner-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
}

.editor__owner-chip--dragon {
  background: #1a1c22;
  color: #f3efe8;
}

.editor__owner-chip--leaf {
  background: #fce4ee;
  color: #2a1820;
}

.editor__row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.editor__period {
  margin: -6px 0 14px;
  font-size: 12px;
  font-weight: 700;
  color: var(--primary);
}

.editor__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 14px;
}

.editor__field span {
  font-size: 13px;
  font-weight: 700;
}

.editor__field small {
  font-size: 11px;
  color: var(--muted);
  line-height: 1.45;
}

.editor__field input,
.editor__field textarea {
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  color: var(--ink);
  font: inherit;
  font-weight: 600;
  padding: 0 12px;
}

.editor__field input {
  height: 44px;
}

.editor__field textarea {
  padding: 10px 12px;
  min-height: 72px;
  resize: vertical;
  line-height: 1.45;
  font-weight: 500;
}

.editor__del {
  margin-top: 10px;
}
</style>
