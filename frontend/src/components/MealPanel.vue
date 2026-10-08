<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  closeToast,
  showFailToast,
  showLoadingToast,
  showSuccessToast,
} from 'vant'
import type { Meal, MealType } from '@/api/meals'
import {
  MEAL_TYPE_LABELS,
  MEAL_TYPES,
  createMeal,
  estimateMeal,
  patchMeal,
} from '@/api/meals'

const props = defineProps<{
  date: string
  meals: Meal[]
}>()

const emit = defineEmits<{ changed: [] }>()

const fileInput = ref<HTMLInputElement | null>(null)
const pendingMealType = ref<MealType | null>(null)

const composeVisible = ref(false)
const composeMode = ref<'ai' | 'manual'>('ai')
const previewUrl = ref<string | null>(null)
const imagePath = ref<string | null>(null)
const estimateFailed = ref(false)
const foodSummary = ref('')
const userKcal = ref('')
const aiKcal = ref<number | null>(null)
const advice = ref('')

const editVisible = ref(false)
const editMealId = ref<number | null>(null)
const editSummary = ref('')
const editKcal = ref('')

const mealsByType = computed(() => {
  const map: Record<MealType, Meal[]> = {
    breakfast: [],
    lunch: [],
    dinner: [],
    snack: [],
  }
  for (const m of props.meals) {
    map[m.meal_type]?.push(m)
  }
  return map
})

function resetCompose() {
  if (previewUrl.value) {
    URL.revokeObjectURL(previewUrl.value)
  }
  previewUrl.value = null
  imagePath.value = null
  estimateFailed.value = false
  foodSummary.value = ''
  userKcal.value = ''
  aiKcal.value = null
  advice.value = ''
  pendingMealType.value = null
}

function openMealActions(mealType: MealType) {
  pendingMealType.value = mealType
  fileInput.value?.click()
}

function startManual(mealType: MealType) {
  resetCompose()
  pendingMealType.value = mealType
  composeMode.value = 'manual'
  composeVisible.value = true
}

async function onFileSelected(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  const mealType = pendingMealType.value
  if (!file || !mealType) return

  resetCompose()
  pendingMealType.value = mealType
  previewUrl.value = URL.createObjectURL(file)
  composeMode.value = 'ai'
  composeVisible.value = true

  showLoadingToast({ message: 'AI 估卡中…', forbidClick: true, duration: 0 })
  try {
    const est = await estimateMeal(file)
    closeToast()
    imagePath.value = est.image_path
    foodSummary.value = est.food_summary
    aiKcal.value = est.kcal
    userKcal.value = est.kcal > 0 ? String(est.kcal) : ''
    advice.value = est.advice
    estimateFailed.value = Boolean(est.estimate_failed)
    if (est.estimate_failed) {
      showFailToast('估卡失败，请手填热量')
    }
  } catch {
    closeToast()
    estimateFailed.value = true
    showFailToast('上传或估卡失败，请手填热量')
  }
}

async function saveCompose() {
  const mealType = pendingMealType.value
  const kcal = parseInt(userKcal.value, 10)
  if (!mealType) return
  if (!foodSummary.value.trim()) {
    showFailToast('请填写食物描述')
    return
  }
  if (!Number.isFinite(kcal) || kcal < 0) {
    showFailToast('请填写有效热量 (kcal)')
    return
  }

  composeVisible.value = false
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await createMeal({
      date: props.date,
      meal_type: mealType,
      food_summary: foodSummary.value.trim(),
      ai_kcal: aiKcal.value,
      user_kcal: kcal,
      advice: advice.value,
      image_path: imagePath.value,
    })
    closeToast()
    showSuccessToast('已保存')
    resetCompose()
    emit('changed')
  } catch {
    closeToast()
    showFailToast('保存失败')
  }
}

function openEdit(meal: Meal) {
  editMealId.value = meal.id
  editSummary.value = meal.food_summary
  editKcal.value = String(meal.user_kcal)
  editVisible.value = true
}

async function confirmEdit() {
  const id = editMealId.value
  const kcal = parseInt(editKcal.value, 10)
  if (id == null || !editSummary.value.trim()) {
    showFailToast('请填写完整')
    return
  }
  if (!Number.isFinite(kcal) || kcal < 0) {
    showFailToast('热量无效')
    return
  }
  editVisible.value = false
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await patchMeal(id, { food_summary: editSummary.value.trim(), user_kcal: kcal })
    closeToast()
    showSuccessToast('已更新')
    emit('changed')
  } catch {
    closeToast()
    showFailToast('更新失败')
  }
}

function onComposeClosed() {
  if (!composeVisible.value) {
    resetCompose()
  }
}
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <h2>饮食</h2>
    </header>

    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      class="hidden-file"
      @change="onFileSelected"
    />

    <div class="meal-grid">
      <div v-for="mt in MEAL_TYPES" :key="mt" class="meal-card">
        <div class="meal-card-head">
          <span class="meal-label">{{ MEAL_TYPE_LABELS[mt] }}</span>
          <div class="meal-actions">
            <van-button size="mini" plain type="primary" @click="openMealActions(mt)">选图</van-button>
            <van-button size="mini" plain @click="startManual(mt)">手填</van-button>
          </div>
        </div>
        <ul v-if="mealsByType[mt].length" class="meal-items">
          <li v-for="m in mealsByType[mt]" :key="m.id" @click="openEdit(m)">
            <span class="summary">{{ m.food_summary }}</span>
            <span class="kcal">{{ m.user_kcal }} kcal</span>
          </li>
        </ul>
        <p v-else class="meal-empty">未记录</p>
      </div>
    </div>

    <van-popup
      v-model:show="composeVisible"
      position="bottom"
      round
      :style="{ maxHeight: '85vh' }"
      @closed="onComposeClosed"
    >
      <div class="compose">
        <h3>{{ pendingMealType ? MEAL_TYPE_LABELS[pendingMealType] : '' }} · {{ composeMode === 'ai' ? '估卡' : '手填' }}</h3>
        <img v-if="previewUrl" :src="previewUrl" alt="餐食" class="preview" />
        <van-notice-bar
          v-if="estimateFailed"
          left-icon="info-o"
          text="AI 估卡失败，照片已保存，请手填热量后保存"
        />
        <van-field v-model="foodSummary" label="食物" type="textarea" rows="2" autosize placeholder="简述吃了什么" />
        <van-field v-model="userKcal" label="热量" type="digit" placeholder="kcal" />
        <van-field v-if="advice && !estimateFailed" v-model="advice" label="建议" type="textarea" rows="2" readonly />
        <van-button type="primary" block round @click="saveCompose">保存</van-button>
      </div>
    </van-popup>

    <van-dialog
      v-model:show="editVisible"
      title="修改记录"
      show-cancel-button
      @confirm="confirmEdit"
    >
      <van-field v-model="editSummary" label="食物" type="textarea" rows="2" autosize />
      <van-field v-model="editKcal" label="热量" type="digit" />
    </van-dialog>
  </section>
</template>

<style scoped>
.panel {
  margin-bottom: 24px;
}

.panel-head h2 {
  margin: 0 0 12px;
  font-size: 17px;
  font-weight: 600;
}

.hidden-file {
  display: none;
}

.meal-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.meal-card {
  padding: 12px 14px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #ebedf0;
}

.meal-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.meal-label {
  font-weight: 600;
  font-size: 15px;
}

.meal-actions {
  display: flex;
  gap: 6px;
}

.meal-items {
  list-style: none;
  margin: 0;
  padding: 0;
}

.meal-items li {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-top: 1px solid #f2f3f5;
  font-size: 14px;
  cursor: pointer;
}

.meal-items li:first-child {
  border-top: none;
  padding-top: 0;
}

.summary {
  flex: 1;
  color: #323233;
}

.kcal {
  color: #1989fa;
  white-space: nowrap;
}

.meal-empty {
  margin: 0;
  font-size: 13px;
  color: #969799;
}

.compose {
  padding: 16px 16px 24px;
}

.compose h3 {
  margin: 0 0 12px;
  font-size: 16px;
}

.preview {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 12px;
}
</style>
