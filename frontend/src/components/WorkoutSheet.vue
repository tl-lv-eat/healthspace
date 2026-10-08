<script setup lang="ts">
import { ref, watch } from 'vue'
import {
  closeToast,
  showConfirmDialog,
  showFailToast,
  showLoadingToast,
  showSuccessToast,
} from 'vant'
import CardioForm from '@/components/CardioForm.vue'
import StrengthPicker from '@/components/StrengthPicker.vue'
import {
  CARDIO_TYPE_LABELS,
  type CardioType,
  deleteWorkout,
  fetchWorkouts,
  formatWorkoutSummary,
  patchWorkout,
  type Workout,
  type WorkoutPayloadCardio,
  type WorkoutPayloadStrength,
} from '@/api/workouts'

const props = defineProps<{
  show: boolean
  date: string
}>()

const emit = defineEmits<{
  'update:show': [boolean]
  changed: []
}>()

const workouts = ref<Workout[]>([])
const activeTab = ref(0)

const editVisible = ref(false)
const editing = ref<Workout | null>(null)
const editDuration = ref(30)
const editIntensity = ref('')
const editCardioType = ref<CardioType>('run')
const editExerciseName = ref('')
const editSetCount = ref(3)
const editReps = ref(10)

const CARDIO_TYPES = Object.keys(CARDIO_TYPE_LABELS) as CardioType[]

async function reload() {
  try {
    workouts.value = await fetchWorkouts(props.date)
  } catch {
    showFailToast('加载运动失败')
  }
}

watch(
  () => props.show,
  (v) => {
    if (v) void reload()
  },
)

function close() {
  emit('update:show', false)
}

async function onSaved() {
  await reload()
  emit('changed')
}

function openEdit(w: Workout) {
  editing.value = w
  if (w.kind === 'cardio') {
    const p = w.payload as WorkoutPayloadCardio
    editCardioType.value = p.cardio_type
    editDuration.value = p.duration_min
    editIntensity.value = p.intensity ?? ''
  } else {
    const p = w.payload as WorkoutPayloadStrength
    editExerciseName.value = p.exercise_name
    editDuration.value = (p.duration_min ?? 0) > 0 ? (p.duration_min as number) : 30
    editSetCount.value = p.sets?.length || 3
    editReps.value = p.sets?.[0]?.reps || 10
  }
  editVisible.value = true
}

async function saveEdit() {
  const w = editing.value
  if (!w) return
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    if (w.kind === 'cardio') {
      if (editDuration.value <= 0) {
        closeToast()
        showFailToast('时长无效')
        return
      }
      await patchWorkout(w.id, {
        cardio_type: editCardioType.value,
        duration_min: editDuration.value,
        intensity: editIntensity.value,
      })
    } else {
      if (
        !editExerciseName.value.trim() ||
        editSetCount.value <= 0 ||
        editReps.value <= 0 ||
        editDuration.value <= 0
      ) {
        closeToast()
        showFailToast('请填写完整')
        return
      }
      const sets = Array.from({ length: editSetCount.value }, () => ({ reps: editReps.value }))
      await patchWorkout(w.id, {
        exercise_name: editExerciseName.value.trim(),
        duration_min: editDuration.value,
        sets,
      })
    }
    closeToast()
    showSuccessToast('已更新')
    editVisible.value = false
    editing.value = null
    await reload()
    emit('changed')
  } catch {
    closeToast()
    showFailToast('更新失败')
  }
}

async function onDelete(w: Workout) {
  try {
    await showConfirmDialog({
      title: '删除这条运动？',
      message: formatWorkoutSummary(w),
    })
  } catch {
    return
  }
  showLoadingToast({ message: '删除中…', forbidClick: true, duration: 0 })
  try {
    await deleteWorkout(w.id)
    closeToast()
    showSuccessToast('已删除')
    await reload()
    emit('changed')
  } catch {
    closeToast()
    showFailToast('删除失败')
  }
}
</script>

<template>
  <van-popup
    :show="show"
    position="bottom"
    round
    :style="{ height: '88%' }"
    @update:show="emit('update:show', $event)"
  >
    <div class="ws">
      <header class="ws__bar">
        <div>
          <p class="ws__eye">Movement</p>
          <h3>记录运动</h3>
        </div>
        <button type="button" class="ws__close" @click="close">完成</button>
      </header>

      <div class="ws__body">
        <section v-if="workouts.length" class="ws__logged">
          <p class="ws__logged-title">今日已记</p>
          <div v-for="w in workouts" :key="w.id" class="ws__row">
            <div class="ws__row-main">
              <span>{{ formatWorkoutSummary(w) }}</span>
              <time>{{ w.created_at.slice(11, 16) }}</time>
            </div>
            <div class="ws__row-actions">
              <button type="button" class="ws__btn" @click="openEdit(w)">改</button>
              <button type="button" class="ws__btn ws__btn--del" @click="onDelete(w)">删</button>
            </div>
          </div>
        </section>

        <van-tabs v-model:active="activeTab" shrink>
          <van-tab title="有氧">
            <CardioForm :date="date" @saved="onSaved" />
          </van-tab>
          <van-tab title="力量">
            <StrengthPicker :date="date" @saved="onSaved" />
          </van-tab>
        </van-tabs>
      </div>
    </div>
  </van-popup>

  <van-popup v-model:show="editVisible" position="bottom" round :style="{ padding: '8px 0 20px' }">
    <div class="edit-sheet">
      <h3>修改运动</h3>
      <template v-if="editing?.kind === 'cardio'">
        <p class="edit-sheet__label">类型</p>
        <div class="edit-sheet__chips">
          <button
            v-for="t in CARDIO_TYPES"
            :key="t"
            type="button"
            class="edit-sheet__chip"
            :class="{ on: editCardioType === t }"
            @click="editCardioType = t"
          >
            {{ CARDIO_TYPE_LABELS[t] }}
          </button>
        </div>
        <van-cell title="时长（分钟）">
          <template #value>
            <van-stepper v-model="editDuration" min="5" max="180" step="5" />
          </template>
        </van-cell>
        <van-field v-model="editIntensity" label="强度" placeholder="可选" />
      </template>
      <template v-else>
        <van-field v-model="editExerciseName" label="动作" />
        <van-cell title="时长（分钟）">
          <template #value>
            <van-stepper v-model="editDuration" min="1" max="180" step="5" />
          </template>
        </van-cell>
        <van-cell title="组数">
          <template #value>
            <van-stepper v-model="editSetCount" min="1" max="20" />
          </template>
        </van-cell>
        <van-cell title="每组次数">
          <template #value>
            <van-stepper v-model="editReps" min="1" max="100" />
          </template>
        </van-cell>
      </template>
      <div class="edit-sheet__actions">
        <van-button block @click="editVisible = false">取消</van-button>
        <van-button type="primary" block @click="saveEdit">保存</van-button>
      </div>
    </div>
  </van-popup>
</template>

<style scoped>
.ws {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--ink);
}

.ws__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 12px;
  background: var(--card);
  border-bottom: 1px solid var(--line);
}

.ws__eye {
  margin: 0;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--workout);
  font-family: var(--font-display);
}

.ws__bar h3 {
  margin: 4px 0 0;
  font-size: 1.15rem;
  font-weight: 700;
}

.ws__close {
  border: none;
  background: var(--workout-soft);
  color: var(--workout);
  font-weight: 800;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
}

.ws__body {
  flex: 1;
  overflow: auto;
  padding: 12px 14px 24px;
}

.ws__logged {
  margin-bottom: 14px;
}

.ws__logged-title {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 800;
  color: var(--muted);
  letter-spacing: 0.06em;
}

.ws__row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  margin-bottom: 8px;
}

.ws__row-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  font-weight: 600;
}

.ws__row-main time {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.ws__row-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}

.ws__btn {
  border: none;
  background: var(--bg);
  color: var(--ink);
  font-size: 12px;
  font-weight: 800;
  padding: 7px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.ws__btn--del {
  background: var(--cal-soft);
  color: var(--cal);
}

.edit-sheet {
  padding: 16px;
}

.edit-sheet h3 {
  margin: 0 0 12px;
  font-size: 1.1rem;
  font-weight: 800;
}

.edit-sheet__label {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.edit-sheet__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.edit-sheet__chip {
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--ink);
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.edit-sheet__chip.on {
  background: var(--workout-soft);
  border-color: var(--workout);
  color: var(--workout);
}

.edit-sheet__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 16px;
}

:deep(.van-tabs__wrap) {
  border-radius: 14px;
  overflow: hidden;
  background: var(--card);
  border: 1px solid var(--line);
}

:deep(.van-tabs__content) {
  padding-top: 12px;
}

:deep(.van-tab) {
  color: var(--muted);
}

:deep(.van-tab--active) {
  color: var(--workout);
}
</style>
