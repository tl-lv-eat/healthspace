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
const bmrKcal = ref<number | ''>(auth.user?.bmr_kcal != null ? auth.user.bmr_kcal : '')
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
    bmrKcal.value = u?.bmr_kcal != null ? u.bmr_kcal : ''
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
  const bmrNum = bmrKcal.value === '' ? NaN : Number(bmrKcal.value)
  if (!Number.isInteger(bmrNum) || bmrNum < 800 || bmrNum > 4000) {
    showFailToast('基础代谢请填写 800–4000 的整数')
    return
  }
  const ageNum = age.value === '' ? null : Number(age.value)
  if (ageNum != null && (!Number.isInteger(ageNum) || ageNum < 10 || ageNum > 100)) {
    showFailToast('年龄请填写 10–100 的整数')
    return
  }
  saving.value = true
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await auth.updateProfile({
      display_name: trimmed,
      sex: sex.value || null,
      age: ageNum,
      bmr_kcal: bmrNum,
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
    <header class="settings-hero">
      <div class="settings-hero__glow" aria-hidden="true" />
      <button type="button" class="settings-back" @click="router.back()">← 返回</button>
      <p class="fit-section-label">Settings</p>
      <h1>设置</h1>
      <p class="settings-hero__hint">
        {{ personaById(auth.user?.id)?.emoji }} 资料与双人积分规则
      </p>
    </header>

    <section class="settings-block">
      <div class="settings-block__head">
        <p class="fit-section-label">Profile</p>
        <h2>个人资料</h2>
        <p class="settings-block__hint">
          基础代谢自己填写，用于今日/日历热量缺口；性别年龄可选（成就等）。
        </p>
      </div>

      <label class="settings-field">
        <span>显示名称</span>
        <input v-model="name" maxlength="32" placeholder="例如：龙龙 / 孙孙" />
      </label>

      <label class="settings-field">
        <span>基础代谢 BMR（kcal/日）</span>
        <input
          v-model.number="bmrKcal"
          type="number"
          min="800"
          max="4000"
          placeholder="例如：1600"
        />
      </label>

      <div class="settings-field">
        <span>性别（可选）</span>
        <div class="settings-sex">
          <button
            type="button"
            class="settings-sex__btn"
            :class="{ 'settings-sex__btn--on': sex === 'male' }"
            @click="sex = 'male'"
          >
            男
          </button>
          <button
            type="button"
            class="settings-sex__btn"
            :class="{ 'settings-sex__btn--on': sex === 'female' }"
            @click="sex = 'female'"
          >
            女
          </button>
        </div>
      </div>

      <label class="settings-field">
        <span>年龄（可选）</span>
        <input v-model.number="age" type="number" min="10" max="100" placeholder="例如：28" />
      </label>

      <button type="button" class="settings-save" :disabled="saving" @click="save">
        {{ saving ? '保存中…' : '保存资料' }}
      </button>
      <button type="button" class="settings-link" @click="router.push('/body')">
        去身体数据录体重趋势 →
      </button>
    </section>

    <section class="settings-block settings-block--points">
      <div class="settings-block__head">
        <p class="fit-section-label">Points</p>
        <h2>积分结算</h2>
        <p class="settings-block__hint">
          双人共用。每天在设定整点结算「刚结束的那一天」；补结算可在积分与商城页操作。
        </p>
      </div>

      <div v-if="pointsLoading" class="settings-loading">加载中…</div>
      <template v-else>
        <label class="settings-field">
          <span>日结时刻（0–23 点）</span>
          <input v-model.number="settleHour" type="number" min="0" max="23" />
        </label>

        <p class="settings-sublabel">每日达标分</p>
        <div class="settings-grid">
          <label class="settings-chip">
            <span>饮水</span>
            <input v-model.number="pointsDailyWater" type="number" />
          </label>
          <label class="settings-chip">
            <span>热量缺口</span>
            <input v-model.number="pointsDailyDeficit" type="number" />
          </label>
          <label class="settings-chip">
            <span>运动≥40分</span>
            <input v-model.number="pointsDailyWorkout40" type="number" />
          </label>
        </div>

        <p class="settings-sublabel">计划结束档位</p>
        <div class="settings-grid">
          <label class="settings-chip settings-chip--b">
            <span>档 B</span>
            <input v-model.number="pointsPlanTierB" type="number" />
          </label>
          <label class="settings-chip settings-chip--a">
            <span>档 A</span>
            <input v-model.number="pointsPlanTierA" type="number" />
          </label>
          <label class="settings-chip settings-chip--fail">
            <span>未达标</span>
            <input v-model.number="pointsPlanTierFail" type="number" />
          </label>
        </div>

        <button
          type="button"
          class="settings-save"
          :disabled="savingPoints"
          @click="savePointsRules"
        >
          {{ savingPoints ? '保存中…' : '保存积分规则' }}
        </button>
      </template>
    </section>
  </div>
</template>

<style scoped>
.settings {
  padding: 12px 14px 40px;
}

.settings-hero {
  position: relative;
  overflow: hidden;
  padding: 14px 18px 20px;
  margin-bottom: 18px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--primary) 16%, var(--card)), var(--card) 55%);
  box-shadow: var(--shadow);
  animation: set-in 0.45s ease both;
}

.settings-hero__glow {
  position: absolute;
  width: 180px;
  height: 180px;
  right: -40px;
  top: -50px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--hero-glow), transparent 70%);
  pointer-events: none;
}

.settings-back {
  position: relative;
  border: none;
  background: transparent;
  padding: 0;
  margin-bottom: 10px;
  font: inherit;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
}

.settings-hero h1 {
  position: relative;
  margin: 0;
  font-size: 1.7rem;
  font-weight: 800;
}

.settings-hero__hint {
  position: relative;
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.settings-block {
  padding: 18px 16px;
  margin-bottom: 14px;
  border-radius: 22px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
  animation: set-in 0.5s ease both;
}

.settings-block--points {
  background:
    linear-gradient(165deg, color-mix(in srgb, var(--primary) 8%, var(--card)), var(--card));
}

.settings-block__head {
  margin-bottom: 14px;
}

.settings-block__head .fit-section-label {
  margin-bottom: 4px;
}

.settings-block__head h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
}

.settings-block__hint {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--muted);
  font-weight: 600;
}

.settings-link {
  width: 100%;
  margin-top: 10px;
  height: 42px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: transparent;
  color: var(--ink);
  font-weight: 800;
  font-size: 13px;
  cursor: pointer;
}

.settings-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 12px;
  font-weight: 800;
  color: var(--muted);
}

.settings-field input {
  height: 44px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: color-mix(in srgb, var(--bg) 75%, var(--card));
  color: var(--ink);
  font: inherit;
  font-weight: 700;
  font-size: 15px;
}

.settings-sex {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.settings-sex__btn {
  height: 44px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: color-mix(in srgb, var(--bg) 75%, var(--card));
  color: var(--muted);
  font-weight: 800;
  cursor: pointer;
}

.settings-sex__btn--on {
  background: var(--primary);
  border-color: transparent;
  color: var(--on-primary, #fff);
}

.settings-sublabel {
  margin: 8px 0 10px;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-display);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 14px;
}

.settings-chip {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 10px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: color-mix(in srgb, var(--bg) 60%, var(--card));
  font-size: 11px;
  font-weight: 800;
  color: var(--muted);
}

.settings-chip input {
  width: 100%;
  box-sizing: border-box;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--ink);
  font: inherit;
  font-size: 1.15rem;
  font-weight: 800;
  font-family: var(--font-display);
  padding: 0;
}

.settings-chip--b {
  border-color: color-mix(in srgb, var(--water) 35%, var(--line));
  background: color-mix(in srgb, var(--water) 10%, var(--card));
}

.settings-chip--a {
  border-color: color-mix(in srgb, var(--workout) 35%, var(--line));
  background: color-mix(in srgb, var(--workout) 10%, var(--card));
}

.settings-chip--fail {
  border-color: color-mix(in srgb, var(--cal) 35%, var(--line));
  background: color-mix(in srgb, var(--cal) 10%, var(--card));
}

.settings-save {
  width: 100%;
  height: 46px;
  margin-top: 4px;
  border: none;
  border-radius: 14px;
  background: var(--primary);
  color: var(--on-primary, #fff);
  font-weight: 800;
  font-size: 14px;
  cursor: pointer;
}

.settings-save:disabled {
  opacity: 0.55;
}

.settings-loading {
  padding: 28px;
  text-align: center;
  color: var(--muted);
  font-weight: 600;
}

@keyframes set-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}

@media (max-width: 360px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}
</style>
