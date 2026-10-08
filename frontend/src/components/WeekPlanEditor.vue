<script setup lang="ts">
import { ref, watch } from 'vue'
import { showFailToast, showSuccessToast } from 'vant'
import { fetchWeekPlan, saveWeekPlan, type WeekPlan } from '@/api/weekPlans'

const props = defineProps<{
  show: boolean
  weekStart: string
}>()

const emit = defineEmits<{
  'update:show': [value: boolean]
  saved: []
}>()

const water = ref(2000)
const mealMode = ref('three_main')
const workoutMode = ref('any')
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const plan: WeekPlan = await fetchWeekPlan(props.weekStart)
    water.value = plan.water_target_ml
    mealMode.value = plan.meal_mode
    workoutMode.value = plan.workout_mode
  } catch {
    showFailToast('加载周计划失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => [props.show, props.weekStart] as const,
  ([visible]) => {
    if (visible) void load()
  },
)

async function onSave() {
  try {
    await saveWeekPlan({
      week_start: props.weekStart,
      water_target_ml: water.value,
      meal_mode: mealMode.value,
      workout_mode: workoutMode.value,
    })
    showSuccessToast('已保存')
    emit('saved')
    emit('update:show', false)
  } catch {
    showFailToast('保存失败')
  }
}
</script>

<template>
  <van-popup :show="show" position="bottom" round @update:show="emit('update:show', $event)">
    <div class="editor">
      <h3>本周计划</h3>
      <van-field v-model.number="water" type="digit" label="饮水目标 ml" />
      <van-cell title="饮食规则">
        <template #value>
          <van-radio-group v-model="mealMode" direction="horizontal">
            <van-radio name="three_main">三餐</van-radio>
            <van-radio name="any">任意一餐</van-radio>
          </van-radio-group>
        </template>
      </van-cell>
      <van-cell title="运动规则">
        <template #value>
          <van-radio-group v-model="workoutMode" direction="horizontal">
            <van-radio name="any">任意记录</van-radio>
            <van-radio name="cardio_min">有氧时长</van-radio>
          </van-radio-group>
        </template>
      </van-cell>
      <van-button block type="primary" :loading="loading" @click="onSave">保存</van-button>
    </div>
  </van-popup>
</template>

<style scoped>
.editor {
  padding: 20px 16px 32px;
}

.editor h3 {
  margin: 0 0 16px;
  font-size: 1.1rem;
}
</style>
