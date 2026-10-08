<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { showFailToast, showSuccessToast } from 'vant'
import PointsBadge from '@/components/PointsBadge.vue'
import GoalCard from '@/components/GoalCard.vue'
import RewardList from '@/components/RewardList.vue'
import RewardForm from '@/components/RewardForm.vue'
import { fetchGoals, createGoal, refreshGoal, type Goal } from '@/api/goals'
import { fetchRewards, fetchMyRedemptions, patchRedemption, type Redemption } from '@/api/rewards'
import { fetchPointsBalance } from '@/api/points'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const balance = ref(0)
const goals = ref<Goal[]>([])
const rewards = ref<Awaited<ReturnType<typeof fetchRewards>>>([])
const redemptions = ref<Redemption[]>([])
const rewardFormRef = ref<InstanceType<typeof RewardForm> | null>(null)
const showGoalForm = ref(false)
const goalTitle = ref('')
const goalKind = ref<'short' | 'long'>('short')
const goalMetric = ref<'weight_kg' | 'workout_days' | 'custom'>('weight_kg')
const goalTarget = ref(68)
const goalStart = ref(new Date().toISOString().slice(0, 10))

const myId = computed(() => auth.user?.id ?? '')

const shortGoals = computed(() => goals.value.filter((g) => g.kind === 'short'))
const longGoals = computed(() => goals.value.filter((g) => g.kind === 'long'))

async function loadBalance() {
  balance.value = await fetchPointsBalance()
}

async function loadAll() {
  try {
    await loadBalance()
    goals.value = await fetchGoals('all')
    rewards.value = await fetchRewards()
    redemptions.value = await fetchMyRedemptions()
  } catch {
    showFailToast('加载目标页失败')
  }
}

async function onRefreshGoal(id: number) {
  try {
    const updated = await refreshGoal(id)
    goals.value = goals.value.map((g) => (g.id === id ? updated : g))
    showSuccessToast('已刷新')
  } catch {
    showFailToast('刷新失败')
  }
}

async function submitGoal() {
  if (!goalTitle.value.trim()) {
    showFailToast('请填写标题')
    return
  }
  try {
    await createGoal({
      kind: goalKind.value,
      title: goalTitle.value.trim(),
      metric: goalMetric.value,
      target_value: goalTarget.value,
      unit: goalMetric.value === 'weight_kg' ? 'kg' : goalMetric.value === 'workout_days' ? '天' : '',
      start_date: goalStart.value,
    })
    showGoalForm.value = false
    goalTitle.value = ''
    await loadAll()
    showSuccessToast('目标已创建')
  } catch {
    showFailToast('创建失败')
  }
}

async function onRedemptionAction(r: Redemption, status: 'fulfilled' | 'cancelled') {
  try {
    await patchRedemption(r.id, status)
    await loadAll()
    showSuccessToast(status === 'fulfilled' ? '已兑现' : '已取消并退分')
  } catch {
    showFailToast('操作失败')
  }
}

onMounted(() => {
  void loadAll()
})
</script>

<template>
  <div class="goals-page">
    <header class="goals-page__hero fit-card">
      <p class="fit-section-label">Goals</p>
      <h1>目标与奖励</h1>
    </header>

    <PointsBadge :balance="balance" @refresh="loadBalance" />

    <section class="goals-section">
      <div class="goals-section__head">
        <h2>目标</h2>
        <van-button size="small" type="primary" plain @click="showGoalForm = true">新建</van-button>
      </div>
      <p class="goals-section__sub">短期</p>
      <GoalCard
        v-for="g in shortGoals"
        :key="g.id"
        :goal="g"
        :mine="g.user_id === myId"
        @refresh="onRefreshGoal"
      />
      <p class="goals-section__sub">长期</p>
      <GoalCard
        v-for="g in longGoals"
        :key="g.id"
        :goal="g"
        :mine="g.user_id === myId"
        @refresh="onRefreshGoal"
      />
    </section>

    <section class="goals-section">
      <div class="goals-section__head">
        <h2>奖励</h2>
        <van-button size="small" type="primary" plain @click="rewardFormRef?.open()">添加</van-button>
      </div>
      <RewardList :rewards="rewards" :balance="balance" @redeemed="loadAll" />
    </section>

    <section class="goals-section">
      <h2>我的兑奖</h2>
      <van-cell-group v-for="r in redemptions" :key="r.id" inset class="redemption-row">
        <van-cell
          :title="r.reward_title ?? `#${r.reward_id}`"
          :label="`${r.points_spent} 分 · ${r.status}`"
        />
        <van-cell v-if="r.status === 'pending'">
          <van-button size="small" type="success" plain @click="onRedemptionAction(r, 'fulfilled')">
            兑现
          </van-button>
          <van-button size="small" plain class="redemption-row__cancel" @click="onRedemptionAction(r, 'cancelled')">
            取消退分
          </van-button>
        </van-cell>
      </van-cell-group>
      <van-empty v-if="!redemptions.length" description="暂无兑奖记录" />
    </section>

    <RewardForm ref="rewardFormRef" @created="loadAll" />

    <van-popup v-model:show="showGoalForm" position="bottom" round>
      <div class="goal-form">
        <h3>新建目标</h3>
        <van-field v-model="goalTitle" label="标题" />
        <van-field label="类型">
          <template #input>
            <van-radio-group v-model="goalKind" direction="horizontal">
              <van-radio name="short">短期</van-radio>
              <van-radio name="long">长期</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field label="指标">
          <template #input>
            <van-radio-group v-model="goalMetric" direction="horizontal">
              <van-radio name="weight_kg">体重</van-radio>
              <van-radio name="workout_days">运动天</van-radio>
              <van-radio name="custom">自定义</van-radio>
            </van-radio-group>
          </template>
        </van-field>
        <van-field v-model.number="goalTarget" type="number" label="目标值" />
        <van-field v-model="goalStart" label="开始日" />
        <van-button type="primary" block @click="submitGoal">保存</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.goals-page {
  padding: 20px 0 32px;
}

.goals-page__hero {
  margin: 0 16px 16px;
  padding: 24px 20px;
}

.goals-page__hero h1 {
  margin: 0;
  font-size: 1.5rem;
}

.goals-section {
  margin-bottom: 24px;
}

.goals-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px 8px;
}

.goals-section__head h2 {
  margin: 0;
  font-size: 1.1rem;
}

.goals-section__sub {
  padding: 0 16px 8px;
  margin: 0;
  font-size: 13px;
  opacity: 0.6;
}

.goals-section > h2 {
  padding: 0 16px 8px;
  margin: 0 0 8px;
  font-size: 1.1rem;
}

.goal-form {
  padding: 20px 16px 32px;
}

.goal-form h3 {
  text-align: center;
  margin: 0 0 12px;
}

.redemption-row {
  margin-bottom: 8px;
}

.redemption-row__cancel {
  margin-left: 8px;
}
</style>
