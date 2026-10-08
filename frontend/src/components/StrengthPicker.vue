<script setup lang="ts">
import { ref, watch } from 'vue'
import { closeToast, showFailToast, showLoadingToast, showSuccessToast } from 'vant'
import type { Exercise } from '@/api/exercises'
import { fetchExercises } from '@/api/exercises'
import { BODY_PART_LABELS, createWorkout } from '@/api/workouts'

const props = defineProps<{ date: string }>()
const emit = defineEmits<{ saved: [] }>()

const BODY_PARTS = Object.keys(BODY_PART_LABELS)

type Step = 'part' | 'exercises' | 'sets'

const step = ref<Step>('part')
const bodyPart = ref<string | null>(null)
const exercises = ref<Exercise[]>([])
const loadingExercises = ref(false)
const selected = ref<Exercise | null>(null)
const setCount = ref(3)
const repsPerSet = ref(10)
const durationMin = ref(30)
const brokenGifs = ref<Record<number, boolean>>({})

function onGifError(id: number) {
  brokenGifs.value = { ...brokenGifs.value, [id]: true }
}

watch(bodyPart, async (part) => {
  if (!part) return
  loadingExercises.value = true
  try {
    exercises.value = await fetchExercises(part)
  } catch {
    exercises.value = []
    showFailToast('加载动作失败')
  } finally {
    loadingExercises.value = false
  }
})

function pickPart(part: string) {
  bodyPart.value = part
  step.value = 'exercises'
}

function backToParts() {
  step.value = 'part'
  bodyPart.value = null
  exercises.value = []
}

function pickExercise(ex: Exercise) {
  selected.value = ex
  setCount.value = 3
  repsPerSet.value = 10
  durationMin.value = 30
  step.value = 'sets'
}

function backToExercises() {
  step.value = 'exercises'
  selected.value = null
}

async function save() {
  const ex = selected.value
  const part = bodyPart.value
  if (
    !ex ||
    !part ||
    setCount.value <= 0 ||
    repsPerSet.value <= 0 ||
    durationMin.value <= 0
  ) {
    showFailToast('请填写有效时长、组数与次数')
    return
  }
  const sets = Array.from({ length: setCount.value }, () => ({ reps: repsPerSet.value }))
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await createWorkout({
      date: props.date,
      kind: 'strength',
      body_part: part,
      exercise_id: ex.id,
      exercise_name: ex.name_zh,
      duration_min: durationMin.value,
      sets,
    })
    closeToast()
    showSuccessToast('已记录力量')
    backToExercises()
    emit('saved')
  } catch {
    closeToast()
    showFailToast('保存失败')
  }
}
</script>

<template>
  <div class="strength-picker">
    <template v-if="step === 'part'">
      <p class="hint">选择分类（含自重 / 壶铃）</p>
      <div class="type-grid">
        <button
          v-for="part in BODY_PARTS"
          :key="part"
          type="button"
          class="type-card"
          :class="{
            'type-card--hot': part === 'bodyweight' || part === 'kettlebell',
          }"
          @click="pickPart(part)"
        >
          {{ BODY_PART_LABELS[part] }}
        </button>
      </div>
    </template>

    <template v-else-if="step === 'exercises' && bodyPart">
      <van-cell
        :title="BODY_PART_LABELS[bodyPart] ?? bodyPart"
        is-link
        label="更换部位"
        @click="backToParts"
      />
      <van-loading v-if="loadingExercises" class="load-center" />
      <div v-else-if="exercises.length" class="exercise-list">
        <button
          v-for="ex in exercises"
          :key="ex.id"
          type="button"
          class="exercise-card"
          @click="pickExercise(ex)"
        >
          <img
            v-if="ex.gif_url && !brokenGifs[ex.id]"
            :src="ex.gif_url"
            :alt="ex.name_zh"
            class="exercise-gif"
            loading="lazy"
            referrerpolicy="no-referrer"
            @error="onGifError(ex.id)"
          />
          <div v-else class="exercise-gif placeholder">{{ ex.name_zh.slice(0, 2) }}</div>
          <div class="exercise-meta">
            <strong>{{ ex.name_zh }}</strong>
            <p v-if="ex.instructions_zh">{{ ex.instructions_zh }}</p>
          </div>
        </button>
      </div>
      <van-empty v-else description="该部位暂无动作" />
    </template>

    <template v-else-if="step === 'sets' && selected">
      <van-cell :title="selected.name_zh" is-link label="换动作" @click="backToExercises" />
      <van-cell title="时长（分钟）">
        <template #value>
          <van-stepper v-model="durationMin" min="1" max="180" step="5" />
        </template>
      </van-cell>
      <p class="hint">必填，与有氧合计 ≥40 分钟可获日结运动分</p>
      <van-cell title="组数">
        <template #value>
          <van-stepper v-model="setCount" min="1" max="20" />
        </template>
      </van-cell>
      <van-cell title="每组次数">
        <template #value>
          <van-stepper v-model="repsPerSet" min="1" max="100" />
        </template>
      </van-cell>
      <van-button type="primary" block round class="save-btn" @click="save">保存本动作</van-button>
      <p class="hint center">保存后可继续选其他动作</p>
    </template>
  </div>
</template>

<style scoped>
.strength-picker {
  padding: 4px 0 16px;
}

.hint {
  margin: 0 4px 12px;
  font-size: 13px;
  color: #969799;
}

.hint.center {
  text-align: center;
  margin-top: 12px;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.type-card {
  padding: 18px 8px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
  color: var(--ink);
}

.type-card--hot {
  background: var(--workout-soft);
  color: var(--workout);
}

.load-center {
  display: flex;
  justify-content: center;
  padding: 24px;
}

.exercise-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.exercise-card {
  display: flex;
  gap: 12px;
  padding: 12px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  text-align: left;
  cursor: pointer;
}

.exercise-gif {
  width: 88px;
  height: 88px;
  object-fit: cover;
  border-radius: 14px;
  flex-shrink: 0;
  background: var(--bg);
}

.exercise-gif.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  color: var(--muted);
}

.exercise-meta {
  flex: 1;
  min-width: 0;
}

.exercise-meta strong {
  display: block;
  font-size: 15px;
  font-weight: 800;
  margin-bottom: 4px;
  font-family: var(--font-display);
}

.exercise-meta p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--muted);
}

.save-btn {
  margin-top: 20px;
}
</style>
