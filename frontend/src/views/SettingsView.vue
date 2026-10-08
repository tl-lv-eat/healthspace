<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showSuccessToast, showLoadingToast } from 'vant'
import { fetchCoupleSettings, patchCoupleSettings } from '@/api/coupleSettings'
import { personaById } from '@/constants/personas'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const name = ref(auth.user?.display_name ?? '')
const sex = ref<'male' | 'female' | ''>(
  auth.user?.sex === 'male' || auth.user?.sex === 'female' ? auth.user.sex : '',
)
const age = ref<number | ''>(auth.user?.age != null ? auth.user.age : '')
const saving = ref(false)

const pointsLoading = ref(true)
const savingPoints = ref(false)
const settleHour = ref(0)
const pointsDailyWater = ref(1)
const pointsDailyDeficit = ref(1)
const pointsDailyWorkout40 = ref(2)
const pointsPlanTierB = ref(5)
const pointsPlanTierA = ref(-2)
const pointsPlanTierFail = ref(-5)

onMounted(async () => {
  try {
    const s = await fetchCoupleSettings()
    settleHour.value = s.settle_hour
    pointsDailyWater.value = s.points_daily_water
    pointsDailyDeficit.value = s.points_daily_deficit
    pointsDailyWorkout40.value = s.points_daily_workout_40
    pointsPlanTierB.value = s.points_plan_tier_b
    pointsPlanTierA.value = s.points_plan_tier_a
    pointsPlanTierFail.value = s.points_plan_tier_fail
  } catch {
    showFailToast('加载积分规则失败')
  } finally {
    pointsLoading.value = false
  }
})

watch(
  () => auth.user,
  (u) => {
    if (u?.display_name != null) name.value = u.display_name
    if (u?.sex === 'male' || u?.sex === 'female') sex.value = u.sex
    else if (u) sex.value = ''
    age.value = u?.age != null ? u.age : ''
  },
  { deep: true },
)

async function save() {
  const trimmed = name.value.trim()
  if (!trimmed) {
    showFailToast('名字不能为空')
    return
  }
  if (trimmed.length > 32) {
    showFailToast('名字最多 32 字')
    return
  }
  if (!sex.value) {
    showFailToast('请选择性别（用于 BMR 计算）')
    return
  }
  const ageNum = age.value === '' ? NaN : Number(age.value)
  if (!Number.isInteger(ageNum) || ageNum < 10 || ageNum > 100) {
    showFailToast('年龄请填写 10–100 的整数')
    return
  }
  saving.value = true
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await auth.updateProfile({
      display_name: trimmed,
      sex: sex.value,
      age: ageNum,
    })
    closeToast()
    showSuccessToast('已保存')
  } catch {
    closeToast()
    showFailToast('保存失败')
  } finally {
    saving.value = false
  }
}

async function savePointsRules() {
  const hour = Number(settleHour.value)
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    showFailToast('日结时刻请填写 0–23 的整数')
    return
  }
  savingPoints.value = true
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    const s = await patchCoupleSettings({
      settle_hour: hour,
      points_daily_water: pointsDailyWater.value,
      points_daily_deficit: pointsDailyDeficit.value,
      points_daily_workout_40: pointsDailyWorkout40.value,
      points_plan_tier_b: pointsPlanTierB.value,
      points_plan_tier_a: pointsPlanTierA.value,
      points_plan_tier_fail: pointsPlanTierFail.value,
    })
    settleHour.value = s.settle_hour
    pointsDailyWater.value = s.points_daily_water
    pointsDailyDeficit.value = s.points_daily_deficit
    pointsDailyWorkout40.value = s.points_daily_workout_40
    pointsPlanTierB.value = s.points_plan_tier_b
    pointsPlanTierA.value = s.points_plan_tier_a
    pointsPlanTierFail.value = s.points_plan_tier_fail
    closeToast()
    showSuccessToast('积分规则已保存')
  } catch {
    closeToast()
    showFailToast('保存失败')
  } finally {
    savingPoints.value = false
  }
}
</script>

<template>
  <div class="settings">
    <header class="settings__top">
      <button type="button" class="settings__back" @click="router.back()">← 返回</button>
      <h1>设置</h1>
    </header>

    <section class="settings__card fit-card">
      <p class="fit-section-label">显示名称</p>
      <p class="settings__hint">
        当前身份 {{ personaById(auth.user?.id)?.emoji }} · 对方看到的也是这个名字
      </p>
      <van-field
        v-model="name"
        maxlength="32"
        placeholder="例如：龙龙 / 叶子"
        class="settings__field"
      />

      <p class="fit-section-label settings__label-gap">身体资料</p>
      <p class="settings__hint">用于 Mifflin-St Jeor 基础代谢（BMR）与今日热量上限</p>
      <van-field label="性别" class="settings__field settings__field--inline">
        <template #input>
          <van-radio-group v-model="sex" direction="horizontal" class="settings__sex">
            <van-radio name="male">男</van-radio>
            <van-radio name="female">女</van-radio>
          </van-radio-group>
        </template>
      </van-field>
      <van-field
        v-model.number="age"
        type="digit"
        label="年龄"
        placeholder="例如：28"
        class="settings__field"
      />

      <van-button type="primary" block :loading="saving" class="settings__save" @click="save">
        保存资料
      </van-button>
    </section>

    <section class="settings__card fit-card settings__card--gap">
      <p class="fit-section-label">积分结算</p>
      <p class="settings__hint">
        双人共用。每天在设定整点结算「刚结束的那一天」；补结算可在积分与商城页操作。
      </p>
      <van-loading v-if="pointsLoading" class="settings__points-load" />
      <template v-else>
        <van-field
          v-model.number="settleHour"
          type="digit"
          label="日结时刻"
          placeholder="0–23"
          class="settings__field"
        >
          <template #extra>
            <span class="settings__unit">点</span>
          </template>
        </van-field>
        <van-field
          v-model.number="pointsDailyWater"
          type="number"
          label="饮水达标"
          class="settings__field settings__field--points"
        />
        <van-field
          v-model.number="pointsDailyDeficit"
          type="number"
          label="热量缺口"
          class="settings__field settings__field--points"
        />
        <van-field
          v-model.number="pointsDailyWorkout40"
          type="number"
          label="运动≥40分"
          class="settings__field settings__field--points"
        />
        <p class="fit-section-label settings__label-gap">计划结束档位</p>
        <van-field
          v-model.number="pointsPlanTierB"
          type="number"
          label="档 B"
          class="settings__field settings__field--points"
        />
        <van-field
          v-model.number="pointsPlanTierA"
          type="number"
          label="档 A"
          class="settings__field settings__field--points"
        />
        <van-field
          v-model.number="pointsPlanTierFail"
          type="number"
          label="未达标"
          class="settings__field settings__field--points"
        />
        <van-button
          type="primary"
          block
          :loading="savingPoints"
          class="settings__save"
          @click="savePointsRules"
        >
          保存积分规则
        </van-button>
      </template>
    </section>
  </div>
</template>

<style scoped>
.settings {
  min-height: 100vh;
  padding: 12px 16px 40px;
}

.settings__top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.settings__top h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
}

.settings__back {
  border: none;
  background: transparent;
  font: inherit;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
  padding: 0;
}

.settings__card {
  padding: 22px 18px;
}

.settings__card--gap {
  margin-top: 16px;
}

.settings__points-load {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}

.settings__unit {
  font-size: 13px;
  color: var(--muted);
  padding-left: 4px;
}

.settings__field--points :deep(.van-field__label) {
  width: 6.2em;
}

.settings__hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--muted);
}

.settings__label-gap {
  margin-top: 8px;
}

.settings__field {
  margin-bottom: 16px;
  padding: 4px 12px;
  background: var(--bg);
  border-radius: 14px;
}

.settings__field--inline :deep(.van-field__body) {
  align-items: center;
}

.settings__field :deep(.van-cell) {
  background: transparent;
  padding: 8px 0;
}

.settings__sex {
  gap: 16px;
}

.settings__save {
  height: 44px !important;
  font-weight: 800 !important;
  border-radius: 14px !important;
}
</style>
