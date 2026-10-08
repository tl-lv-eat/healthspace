<script setup lang="ts">
import { ref } from 'vue'
import { closeToast, showFailToast, showLoadingToast, showSuccessToast } from 'vant'
import {
  CARDIO_TYPE_LABELS,
  createWorkout,
  type CardioType,
} from '@/api/workouts'

const props = defineProps<{ date: string }>()
const emit = defineEmits<{ saved: [] }>()

const CARDIO_TYPES = Object.keys(CARDIO_TYPE_LABELS) as CardioType[]

const step = ref<'pick' | 'duration'>('pick')
const selectedType = ref<CardioType | null>(null)
const durationMin = ref(30)
const intensity = ref<string>('')

function pickType(t: CardioType) {
  selectedType.value = t
  durationMin.value = 30
  intensity.value = ''
  step.value = 'duration'
}

function backToPick() {
  step.value = 'pick'
  selectedType.value = null
}

async function save() {
  const t = selectedType.value
  if (!t || durationMin.value <= 0) {
    showFailToast('请填写有效时长')
    return
  }
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await createWorkout({
      date: props.date,
      kind: 'cardio',
      cardio_type: t,
      duration_min: durationMin.value,
      intensity: intensity.value || undefined,
    })
    closeToast()
    showSuccessToast('已记录有氧')
    backToPick()
    emit('saved')
  } catch {
    closeToast()
    showFailToast('保存失败')
  }
}
</script>

<template>
  <div class="cardio-form">
    <template v-if="step === 'pick'">
      <p class="hint">选择有氧类型</p>
      <div class="type-grid">
        <button
          v-for="t in CARDIO_TYPES"
          :key="t"
          type="button"
          class="type-card"
          @click="pickType(t)"
        >
          {{ CARDIO_TYPE_LABELS[t] }}
        </button>
      </div>
    </template>

    <template v-else-if="selectedType">
      <van-cell
        :title="CARDIO_TYPE_LABELS[selectedType]"
        is-link
        label="点击更换类型"
        @click="backToPick"
      />
      <van-cell title="时长（分钟）">
        <template #value>
          <van-stepper v-model="durationMin" min="5" max="180" step="5" />
        </template>
      </van-cell>
      <van-field v-model="intensity" label="强度" placeholder="可选，如 轻松 / 中等" />
      <van-button type="primary" block round class="save-btn" @click="save">保存有氧</van-button>
    </template>
  </div>
</template>

<style scoped>
.cardio-form {
  padding: 4px 0 16px;
}

.hint {
  margin: 0 4px 12px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.type-card {
  padding: 20px 8px;
  border: none;
  border-radius: var(--radius-sm);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  font-size: 14px;
  font-weight: 800;
  color: var(--ink);
  cursor: pointer;
}

.type-card:active {
  background: var(--workout-soft);
  color: #e67700;
}

.save-btn {
  margin-top: 20px;
}
</style>
