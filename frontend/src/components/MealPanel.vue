<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import {
  closeToast,
  showConfirmDialog,
  showFailToast,
  showLoadingToast,
  showSuccessToast,
} from 'vant'
import type { Meal, MealType } from '@/api/meals'
import {
  MEAL_TYPE_LABELS,
  MEAL_TYPES,
  createMeal,
  deleteMeal,
  estimateMeal,
  patchMeal,
  refineMealEstimate,
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
const reason = ref('')
const analyzing = ref(false)
const refineInput = ref('')
const refining = ref(false)
const chatLog = ref<{ role: 'ai' | 'user'; text: string }[]>([])
const chatBox = ref<HTMLElement | null>(null)

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

const totalKcal = computed(() => props.meals.reduce((s, m) => s + (m.user_kcal || 0), 0))

async function scrollChat() {
  await nextTick()
  if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
}

function resetCompose() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = null
  imagePath.value = null
  estimateFailed.value = false
  foodSummary.value = ''
  userKcal.value = ''
  aiKcal.value = null
  advice.value = ''
  reason.value = ''
  pendingMealType.value = null
  refineInput.value = ''
  analyzing.value = false
  refining.value = false
  chatLog.value = []
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

function pushAi(text: string) {
  chatLog.value.push({ role: 'ai', text })
  void scrollChat()
}

function applyEstimate(est: {
  food_summary: string
  kcal: number
  advice: string
  reason?: string
  estimate_failed?: boolean
}) {
  foodSummary.value = est.food_summary
  aiKcal.value = est.kcal
  userKcal.value = est.kcal > 0 ? String(est.kcal) : ''
  advice.value = est.advice
  reason.value = est.reason || ''
  estimateFailed.value = Boolean(est.estimate_failed)
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
  analyzing.value = true
  pushAi('正在看这顿饭…识别食材与份量中')

  try {
    const est = await estimateMeal(file)
    imagePath.value = est.image_path
    applyEstimate(est)
    analyzing.value = false
    if (est.estimate_failed) {
      pushAi('这次没看清，照片已留着。你可以手填热量，或跟我说一下吃了什么再让我估。')
      showFailToast('估卡失败，请手填或补充说明')
    } else {
      pushAi(
        `我看到大概是「${est.food_summary}」。\n\n` +
          `预估 ${est.kcal} kcal。\n\n` +
          `依据：${est.reason || '（未返回）'}\n\n` +
          `建议：${est.advice}\n\n` +
          `如果份量不对、还有饮料/酱料，直接跟我说，我帮你改到更准。确认好后点下方保存。`,
      )
    }
  } catch {
    analyzing.value = false
    estimateFailed.value = true
    pushAi('网络或模型出了点问题。你可以手填热量，或稍后再试。')
    showFailToast('上传或估卡失败')
  }
}

async function sendRefine() {
  const msg = refineInput.value.trim()
  if (refining.value || analyzing.value) return
  if (!msg) {
    showFailToast('先跟 AI 说一句，例如「份量更大」')
    return
  }
  refining.value = true
  chatLog.value.push({ role: 'user', text: msg })
  refineInput.value = ''
  void scrollChat()
  pushAi('收到，正在按你的补充重估…')
  try {
    const est = await refineMealEstimate({
      image_path: imagePath.value || undefined,
      food_summary: foodSummary.value || '未知餐食',
      kcal: parseInt(userKcal.value, 10) || aiKcal.value || 0,
      reason: reason.value,
      advice: advice.value,
      message: msg,
    })
    applyEstimate(est)
    pushAi(
      `已更新 → ${est.kcal} kcal\n` +
        `食物：${est.food_summary}\n\n` +
        `依据：${est.reason}\n\n` +
        `建议：${est.advice}`,
    )
  } catch (err: unknown) {
    const detail =
      err && typeof err === 'object' && 'response' in err
        ? String((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? '')
        : ''
    pushAi(
      detail
        ? `调整失败：${detail}。可再试一次，或直接改热量数字。`
        : '这次调整没成功，可再试一次，或直接改热量数字。',
    )
    showFailToast('AI 调整失败')
  } finally {
    refining.value = false
  }
}

function onRefineKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void sendRefine()
  }
}

function storedAdvice(): string {
  const r = reason.value.trim()
  const a = advice.value.trim()
  if (r && a) return `【估卡依据】${r}\n\n【建议】${a}`
  return a || r
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
      advice: storedAdvice(),
      image_path: imagePath.value,
    })
    closeToast()
    showSuccessToast('已保存')
    resetCompose()
    emit('changed')
  } catch {
    closeToast()
    showFailToast('保存失败')
    composeVisible.value = true
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

async function onDelete(meal: Meal) {
  try {
    await showConfirmDialog({
      title: '删除这条饮食？',
      message: `${meal.food_summary} · ${meal.user_kcal} kcal`,
    })
  } catch {
    return
  }
  showLoadingToast({ message: '删除中…', forbidClick: true, duration: 0 })
  try {
    await deleteMeal(meal.id)
    closeToast()
    showSuccessToast('已删除')
    emit('changed')
  } catch {
    closeToast()
    showFailToast('删除失败')
  }
}

function onComposeClosed() {
  if (!composeVisible.value) resetCompose()
}
</script>

<template>
  <section class="panel">
    <header class="panel__head">
      <div>
        <p class="fit-section-label">Nutrition · AI</p>
        <h2>饮食</h2>
      </div>
      <div class="panel__badge">
        <span class="panel__badge-n">{{ totalKcal }}</span>
        <span class="panel__badge-u">kcal</span>
      </div>
    </header>

    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      class="hidden-file"
      @change="onFileSelected"
    />

    <div class="meal-grid">
      <div v-for="mt in MEAL_TYPES" :key="mt" class="meal-slot">
        <div class="meal-slot__head">
          <span class="meal-slot__label">{{ MEAL_TYPE_LABELS[mt] }}</span>
          <div class="meal-slot__actions">
            <button type="button" class="chip chip--ai" @click="openMealActions(mt)">AI 估卡</button>
            <button type="button" class="chip" @click="startManual(mt)">手填</button>
          </div>
        </div>
        <ul v-if="mealsByType[mt].length" class="meal-items">
          <li v-for="m in mealsByType[mt]" :key="m.id">
            <button type="button" class="meal-items__main" @click="openEdit(m)">
              <span class="summary">{{ m.food_summary }}</span>
              <span class="kcal">{{ m.user_kcal }} kcal</span>
            </button>
            <button type="button" class="meal-items__del" @click="onDelete(m)">删</button>
          </li>
        </ul>
        <p v-else class="meal-empty">拍照让 AI 帮你估</p>
      </div>
    </div>

    <van-popup
      v-model:show="composeVisible"
      position="bottom"
      round
      :style="{ height: '92%' }"
      class="ai-sheet-popup"
      @closed="onComposeClosed"
    >
      <div class="ai-sheet">
        <header class="ai-sheet__bar">
          <div>
            <p class="ai-sheet__eye">AI 估卡</p>
            <h3>{{ pendingMealType ? MEAL_TYPE_LABELS[pendingMealType] : '' }}</h3>
          </div>
          <button type="button" class="ai-sheet__close" @click="composeVisible = false">关闭</button>
        </header>

        <div class="ai-sheet__scroll">
          <div v-if="previewUrl" class="ai-sheet__photo-wrap">
            <img :src="previewUrl" alt="餐食" class="ai-sheet__photo" />
            <span v-if="analyzing" class="ai-sheet__pulse">分析中</span>
          </div>

          <div v-if="composeMode === 'ai'" ref="chatBox" class="ai-sheet__chat">
            <div
              v-for="(c, i) in chatLog"
              :key="i"
              class="bubble"
              :class="c.role === 'ai' ? 'bubble--ai' : 'bubble--user'"
            >
              <p class="bubble__role">{{ c.role === 'ai' ? '健康space AI' : '我' }}</p>
              <p class="bubble__text">{{ c.text }}</p>
            </div>
          </div>
        </div>

        <div class="ai-sheet__dock">
          <div class="ai-sheet__confirm">
            <p class="ai-sheet__confirm-label">确认结果（可改）</p>
            <label class="ai-sheet__field">
              <span>食物</span>
              <textarea
                v-model="foodSummary"
                rows="2"
                placeholder="只写食物内容，如：米饭、鸡腿、青菜"
              />
            </label>
            <label class="ai-sheet__field ai-sheet__field--kcal">
              <span>热量</span>
              <input v-model="userKcal" inputmode="numeric" placeholder="0" />
              <em>kcal</em>
            </label>
          </div>

          <div v-if="composeMode === 'ai'" class="ai-sheet__refine">
            <input
              v-model="refineInput"
              class="ai-sheet__refine-input"
              type="text"
              placeholder="跟 AI 说：份量更大 / 有奶茶…"
              :disabled="analyzing || refining"
              @keydown="onRefineKeydown"
            />
            <button
              type="button"
              class="ai-sheet__refine-btn"
              :disabled="analyzing || refining"
              @click="sendRefine"
            >
              {{ refining ? '改估中…' : '让 AI 改' }}
            </button>
          </div>

          <button
            type="button"
            class="ai-sheet__save"
            :disabled="analyzing || refining"
            @click="saveCompose"
          >
            确认并保存
          </button>
        </div>
      </div>
    </van-popup>

    <van-popup v-model:show="editVisible" position="bottom" round :style="{ padding: '8px 0 24px' }">
      <div class="edit-sheet">
        <h3>修改饮食</h3>
        <van-field v-model="editSummary" label="食物" type="textarea" rows="2" autosize />
        <van-field v-model="editKcal" label="热量" type="digit" />
        <div class="edit-sheet__actions">
          <van-button block @click="editVisible = false">取消</van-button>
          <van-button type="primary" block @click="confirmEdit">保存</van-button>
        </div>
      </div>
    </van-popup>
  </section>
</template>

<style scoped>
.panel {
  margin-bottom: 14px;
  padding: 18px 16px;
  border-radius: 24px;
  background:
    linear-gradient(160deg, color-mix(in srgb, var(--cal) 10%, var(--card)), var(--card) 50%);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}

.panel__head h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
}

.panel__badge {
  min-width: 64px;
  padding: 8px 10px;
  border-radius: 16px;
  text-align: center;
  background: var(--cal-soft);
  color: var(--cal);
}

.panel__badge-n {
  display: block;
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 700;
  line-height: 1;
}

.panel__badge-u {
  font-size: 10px;
  font-weight: 700;
}

.hidden-file {
  display: none;
}

.meal-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.meal-slot {
  padding: 12px;
  border-radius: 16px;
  background: color-mix(in srgb, var(--bg) 70%, transparent);
  border: 1px solid var(--line);
}

.meal-slot__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.meal-slot__label {
  font-weight: 800;
  font-size: 14px;
}

.meal-slot__actions {
  display: flex;
  gap: 6px;
}

.chip {
  border: none;
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  padding: 7px 10px;
  border-radius: 999px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
}

.chip--ai {
  background: var(--primary-soft);
  color: var(--primary-dark);
}

.meal-items {
  list-style: none;
  margin: 0;
  padding: 0;
}

.meal-items li {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--line);
  padding: 4px 0;
}

.meal-items li:first-child {
  border-top: none;
}

.meal-items__main {
  flex: 1;
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border: none;
  background: transparent;
  font: inherit;
  cursor: pointer;
  text-align: left;
  color: var(--ink);
}

.summary {
  flex: 1;
  font-weight: 600;
  font-size: 13px;
}

.kcal {
  color: var(--cal);
  font-weight: 800;
  white-space: nowrap;
  font-size: 13px;
}

.meal-items__del {
  border: none;
  background: var(--cal-soft);
  color: var(--cal);
  font-size: 12px;
  font-weight: 800;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.meal-empty {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
}

.ai-sheet {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg);
  color: var(--ink);
}

.ai-sheet__bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px 10px;
  border-bottom: 1px solid var(--line);
  background: var(--card);
}

.ai-sheet__eye {
  margin: 0;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--primary);
  font-family: var(--font-display);
}

.ai-sheet__bar h3 {
  margin: 4px 0 0;
  font-size: 1.15rem;
  font-weight: 700;
}

.ai-sheet__close {
  border: none;
  background: var(--bg);
  color: var(--muted);
  font-weight: 700;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
}

.ai-sheet__scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  -webkit-overflow-scrolling: touch;
}

.ai-sheet__photo-wrap {
  position: relative;
  flex-shrink: 0;
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid var(--line);
}

.ai-sheet__photo {
  display: block;
  width: 100%;
  max-height: 140px;
  object-fit: cover;
}

.ai-sheet__pulse {
  position: absolute;
  right: 10px;
  bottom: 10px;
  padding: 6px 10px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary) 90%, #000);
  color: var(--on-primary, #fff);
  font-size: 11px;
  font-weight: 800;
  animation: pulse 1.2s ease infinite;
}

.ai-sheet__chat {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 2px 0 8px;
}

.bubble {
  max-width: 92%;
  padding: 10px 12px;
  border-radius: 16px;
  animation: bubble-in 0.35s ease both;
}

.bubble--ai {
  align-self: flex-start;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.bubble--user {
  align-self: flex-end;
  background: var(--primary-soft);
  border: 1px solid color-mix(in srgb, var(--primary) 25%, transparent);
}

.bubble__role {
  margin: 0 0 4px;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  color: var(--primary);
  text-transform: uppercase;
}

.bubble--user .bubble__role {
  color: var(--primary-dark);
  text-align: right;
}

.bubble__text {
  margin: 0;
  font-size: 13px;
  line-height: 1.55;
  white-space: pre-wrap;
  font-weight: 500;
}

.ai-sheet__dock {
  flex-shrink: 0;
  padding: 10px 14px calc(12px + env(safe-area-inset-bottom));
  background: var(--card);
  border-top: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 -8px 24px color-mix(in srgb, var(--ink) 6%, transparent);
}

.ai-sheet__confirm {
  border-radius: 16px;
  background: var(--bg);
  border: 1px solid var(--line);
  padding: 10px 12px 12px;
}

.ai-sheet__confirm-label {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 800;
  color: var(--muted);
  letter-spacing: 0.06em;
}

.ai-sheet__field {
  display: grid;
  grid-template-columns: 48px 1fr;
  gap: 8px;
  align-items: start;
  margin-bottom: 8px;
}

.ai-sheet__field span {
  padding-top: 10px;
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
}

.ai-sheet__field textarea,
.ai-sheet__field input {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: var(--card);
  color: var(--ink);
  font: inherit;
  font-size: 14px;
  font-weight: 600;
  padding: 10px 12px;
  resize: vertical;
  min-height: 44px;
  box-sizing: border-box;
}

.ai-sheet__field--kcal {
  margin-bottom: 0;
  grid-template-columns: 48px 1fr auto;
  align-items: center;
}

.ai-sheet__field--kcal input {
  min-height: 44px;
}

.ai-sheet__field--kcal em {
  font-style: normal;
  font-size: 12px;
  font-weight: 700;
  color: var(--muted);
}

.ai-sheet__refine {
  display: flex;
  gap: 8px;
  align-items: center;
}

.ai-sheet__refine-input {
  flex: 1;
  min-width: 0;
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--bg);
  color: var(--ink);
  font: inherit;
  font-size: 13px;
  font-weight: 600;
  padding: 0 14px;
}

.ai-sheet__refine-btn {
  flex-shrink: 0;
  height: 42px;
  padding: 0 14px;
  border: none;
  border-radius: 999px;
  background: var(--primary);
  color: var(--on-primary, #fff);
  font-weight: 800;
  font-size: 13px;
  cursor: pointer;
}

.ai-sheet__refine-btn:disabled,
.ai-sheet__save:disabled {
  opacity: 0.55;
  cursor: wait;
}

.ai-sheet__save {
  height: 46px;
  border: none;
  border-radius: 999px;
  background: var(--primary);
  color: var(--on-primary, #fff);
  font-weight: 800;
  font-size: 15px;
  cursor: pointer;
}

.edit-sheet {
  padding: 16px 16px 8px;
}

.edit-sheet h3 {
  margin: 0 0 8px;
  font-size: 1.1rem;
  font-weight: 800;
}

.edit-sheet__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 12px;
  padding: 0 4px;
}

@keyframes pulse {
  50% {
    opacity: 0.55;
  }
}

@keyframes bubble-in {
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
