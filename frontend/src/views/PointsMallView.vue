<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { showFailToast, showSuccessToast } from 'vant'
import PointsBadge from '@/components/PointsBadge.vue'
import RewardList from '@/components/RewardList.vue'
import RewardForm from '@/components/RewardForm.vue'
import {
  fetchRewards,
  fetchCoupleRedemptions,
  rejectReward,
  patchRedemption,
  REWARD_CATEGORY_OPTIONS,
  type Reward,
  type RewardCategory,
  type Redemption,
} from '@/api/rewards'
import { fetchPointsBalance } from '@/api/points'
import { settleDaily } from '@/api/coupleSettings'
import { useAuthStore } from '@/stores/auth'
import { personaById } from '@/constants/personas'

const auth = useAuthStore()
const balance = ref(0)
const mallCategory = ref<RewardCategory>('food')
const listedRewards = ref<Reward[]>([])
const pendingReview = ref<Reward[]>([])
const myDrafts = ref<Reward[]>([])
const coupleRedemptions = ref<Redemption[]>([])
const rewardFormRef = ref<InstanceType<typeof RewardForm> | null>(null)
const settling = ref(false)

const showRejectPopup = ref(false)
const rejectTarget = ref<Reward | null>(null)
const rejectReason = ref('')

const myId = computed(() => auth.user?.id ?? '')

const mallFiltered = computed(() =>
  listedRewards.value.filter((r) => r.category === mallCategory.value),
)

const myPendingRedemptions = computed(() =>
  coupleRedemptions.value.filter((r) => r.redeemer_user_id === myId.value && r.status === 'pending'),
)

const myFulfilledRedemptions = computed(() =>
  coupleRedemptions.value.filter((r) => r.redeemer_user_id === myId.value && r.status === 'fulfilled'),
)

const partnerRedemptions = computed(() =>
  coupleRedemptions.value.filter((r) => r.redeemer_user_id !== myId.value),
)

function personaLabel(userId: string): string {
  const p = personaById(userId)
  return p ? `${p.emoji}${p.label}` : userId
}

function redemptionStatusLabel(status: Redemption['status']): string {
  if (status === 'pending') return '待使用'
  if (status === 'fulfilled') return '已使用'
  return status
}

function yesterdayIso(): string {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().slice(0, 10)
}

async function loadBalance() {
  balance.value = await fetchPointsBalance()
}

async function loadAll() {
  try {
    await loadBalance()
    const [listed, review, mine, redemptions] = await Promise.all([
      fetchRewards({ scope: 'listed' }),
      fetchRewards({ scope: 'pending_review_for_me' }),
      fetchRewards({ scope: 'mine' }),
      fetchCoupleRedemptions(),
    ])
    listedRewards.value = listed
    pendingReview.value = review
    myDrafts.value = mine
    coupleRedemptions.value = redemptions
  } catch {
    showFailToast('加载积分与商城失败')
  }
}

async function onSettleYesterday() {
  settling.value = true
  try {
    await settleDaily(yesterdayIso())
    await loadAll()
    showSuccessToast('已结算昨天')
  } catch {
    showFailToast('结算失败')
  } finally {
    settling.value = false
  }
}

function openReject(r: Reward) {
  rejectTarget.value = r
  rejectReason.value = ''
  showRejectPopup.value = true
}

async function confirmReject() {
  if (!rejectTarget.value) return
  if (!rejectReason.value.trim()) {
    showFailToast('请填写打回原因')
    return
  }
  try {
    await rejectReward(rejectTarget.value.id, rejectReason.value.trim())
    showRejectPopup.value = false
    rejectTarget.value = null
    showSuccessToast('已打回')
    await loadAll()
  } catch {
    showFailToast('打回失败')
  }
}

async function onMarkFulfilled(r: Redemption) {
  try {
    await patchRedemption(r.id, 'fulfilled')
    await loadAll()
    showSuccessToast('已标记使用')
  } catch {
    showFailToast('操作失败')
  }
}

function onEditReward(r: Reward) {
  rewardFormRef.value?.open(r)
}

onMounted(() => {
  void loadAll()
})
</script>

<template>
  <div class="points-mall-page">
    <header class="points-mall-page__hero fit-card">
      <p class="fit-section-label">Points</p>
      <h1>积分与商城</h1>
    </header>

    <PointsBadge :balance="balance" @refresh="loadBalance" />

    <div class="points-mall-page__settle">
      <van-button size="small" plain :loading="settling" @click="onSettleYesterday">
        补结算昨天
      </van-button>
    </div>

    <section class="points-mall-section">
      <div class="points-mall-section__head">
        <h2>商城</h2>
        <van-button size="small" type="primary" plain @click="rewardFormRef?.open()">新建</van-button>
      </div>
      <van-tabs v-model:active="mallCategory" shrink swipeable class="points-mall-tabs">
        <van-tab
          v-for="opt in REWARD_CATEGORY_OPTIONS"
          :key="opt.value"
          :name="opt.value"
          :title="opt.label"
        />
      </van-tabs>
      <RewardList
        :rewards="mallFiltered"
        :balance="balance"
        mode="mall"
        @changed="loadAll"
      />
    </section>

    <section v-if="pendingReview.length" class="points-mall-section">
      <h2>待我审核</h2>
      <RewardList
        :rewards="pendingReview"
        mode="review"
        @changed="loadAll"
        @reject="openReject"
      />
    </section>

    <section v-if="myDrafts.length" class="points-mall-section">
      <h2>我的待审 / 打回</h2>
      <RewardList
        :rewards="myDrafts"
        mode="mine"
        @changed="loadAll"
        @edit="onEditReward"
      />
    </section>

    <section class="points-mall-section">
      <h2>我的待使用</h2>
      <van-cell-group v-for="r in myPendingRedemptions" :key="r.id" inset class="redemption-row">
        <van-cell
          :title="r.reward_title ?? `#${r.reward_id}`"
          :label="`${r.points_spent} 分 · ${redemptionStatusLabel(r.status)} · ${r.created_at.slice(0, 16)}`"
        />
        <van-cell>
          <van-button size="small" type="success" plain @click="onMarkFulfilled(r)">已使用</van-button>
        </van-cell>
      </van-cell-group>
      <van-empty v-if="!myPendingRedemptions.length" description="暂无待使用奖励" />
    </section>

    <section class="points-mall-section">
      <h2>我的已使用</h2>
      <van-cell-group v-for="r in myFulfilledRedemptions" :key="r.id" inset class="redemption-row">
        <van-cell
          :title="r.reward_title ?? `#${r.reward_id}`"
          :label="`${r.points_spent} 分 · ${r.fulfilled_at?.slice(0, 16) ?? ''}`"
        />
      </van-cell-group>
      <van-empty v-if="!myFulfilledRedemptions.length" description="暂无记录" />
    </section>

    <section class="points-mall-section">
      <h2>对方奖励（只读）</h2>
      <p class="points-mall-section__sub">待使用 / 已使用</p>
      <van-cell-group v-for="r in partnerRedemptions" :key="r.id" inset class="redemption-row">
        <van-cell
          :title="r.reward_title ?? `#${r.reward_id}`"
          :label="`${personaLabel(r.redeemer_user_id)} · ${r.points_spent} 分 · ${redemptionStatusLabel(r.status)}`"
        />
      </van-cell-group>
      <van-empty v-if="!partnerRedemptions.length" description="对方暂无兑换" />
    </section>

    <RewardForm ref="rewardFormRef" @saved="loadAll" />

    <van-popup v-model:show="showRejectPopup" position="bottom" round>
      <div class="reject-form">
        <h3>打回「{{ rejectTarget?.title }}」</h3>
        <van-field v-model="rejectReason" rows="2" autosize type="textarea" label="原因" placeholder="必填" />
        <van-button type="danger" block @click="confirmReject">确认打回</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.points-mall-page {
  padding: 20px 0 32px;
}

.points-mall-page__hero {
  margin: 0 16px 16px;
  padding: 24px 20px;
}

.points-mall-page__hero h1 {
  margin: 0;
  font-size: 1.5rem;
}

.points-mall-page__settle {
  padding: 0 16px 12px;
  display: flex;
  justify-content: flex-end;
}

.points-mall-section {
  margin-bottom: 24px;
}

.points-mall-section__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px 8px;
}

.points-mall-section__head h2,
.points-mall-section > h2 {
  margin: 0 0 8px;
  padding: 0 16px;
  font-size: 1.1rem;
}

.points-mall-section__head h2 {
  padding: 0;
}

.points-mall-section__sub {
  padding: 0 16px 8px;
  margin: 0;
  font-size: 13px;
  opacity: 0.6;
}

.points-mall-tabs {
  margin-bottom: 8px;
}

.redemption-row {
  margin-bottom: 8px;
}

.reject-form {
  padding: 20px 16px 32px;
}

.reject-form h3 {
  margin: 0 0 12px;
  text-align: center;
  font-size: 1rem;
}
</style>
