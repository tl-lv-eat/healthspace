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
import { formatDateLocal } from '@/api/today'
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
const inventoryTab = ref<'pending' | 'done' | 'partner'>('pending')

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

const reviewBadge = computed(() => pendingReview.value.length)

function personaLabel(userId: string): string {
  const p = personaById(userId)
  return p ? `${p.emoji} ${p.label}` : userId
}

function redemptionStatusLabel(status: Redemption['status']): string {
  if (status === 'pending') return '待使用'
  if (status === 'fulfilled') return '已使用'
  return status
}

function yesterdayIso(): string {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return formatDateLocal(d)
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
  <div class="pm">
    <section class="pm-hero" :class="`pm-hero--${auth.user?.id ?? 'leaf'}`">
      <div class="pm-hero__glow" aria-hidden="true" />
      <header class="pm-hero__head">
        <div>
          <p class="fit-section-label">Rewards</p>
          <h1>积分与商城</h1>
          <p class="pm-hero__hint">日结自动入账 · 兑换需对方兑现</p>
        </div>
        <button type="button" class="pm-hero__settle" :disabled="settling" @click="onSettleYesterday">
          {{ settling ? '结算中…' : '补结昨天' }}
        </button>
      </header>
      <PointsBadge :balance="balance" @refresh="loadBalance" />
    </section>

    <section class="pm-block" :class="{ 'pm-block--alert': pendingReview.length }">
      <div class="pm-block__head">
        <div>
          <p class="fit-section-label">Review</p>
          <h2>
            待我审核
            <span v-if="reviewBadge" class="pm-pill">{{ reviewBadge }}</span>
          </h2>
          <p class="pm-block__hint">对方提交的提案会出现在这里，通过后才上架商城</p>
        </div>
      </div>
      <RewardList
        :rewards="pendingReview"
        mode="review"
        @changed="loadAll"
        @reject="openReject"
      />
    </section>

    <section class="pm-block">
      <div class="pm-block__head">
        <div>
          <p class="fit-section-label">Mall</p>
          <h2>奖励商城</h2>
        </div>
        <button type="button" class="pm-btn pm-btn--primary" @click="rewardFormRef?.open()">
          + 新建
        </button>
      </div>

      <div class="pm-cats" role="tablist">
        <button
          v-for="opt in REWARD_CATEGORY_OPTIONS"
          :key="opt.value"
          type="button"
          class="pm-cat"
          :class="{ 'pm-cat--on': mallCategory === opt.value }"
          @click="mallCategory = opt.value"
        >
          {{ opt.label }}
        </button>
      </div>

      <RewardList
        :rewards="mallFiltered"
        :balance="balance"
        mode="mall"
        @changed="loadAll"
      />
    </section>

    <section class="pm-block">
      <div class="pm-block__head">
        <div>
          <p class="fit-section-label">Mine</p>
          <h2>我的提案</h2>
          <p class="pm-block__hint">你提交、待审或被打回的奖励</p>
        </div>
      </div>
      <RewardList
        :rewards="myDrafts"
        mode="mine"
        @changed="loadAll"
        @edit="onEditReward"
      />
    </section>

    <section class="pm-block">
      <div class="pm-block__head">
        <div>
          <p class="fit-section-label">Inventory</p>
          <h2>奖励柜</h2>
        </div>
      </div>
      <div class="pm-inv-tabs">
        <button
          type="button"
          class="pm-inv-tab"
          :class="{ 'pm-inv-tab--on': inventoryTab === 'pending' }"
          @click="inventoryTab = 'pending'"
        >
          待用 {{ myPendingRedemptions.length }}
        </button>
        <button
          type="button"
          class="pm-inv-tab"
          :class="{ 'pm-inv-tab--on': inventoryTab === 'done' }"
          @click="inventoryTab = 'done'"
        >
          已用 {{ myFulfilledRedemptions.length }}
        </button>
        <button
          type="button"
          class="pm-inv-tab"
          :class="{ 'pm-inv-tab--on': inventoryTab === 'partner' }"
          @click="inventoryTab = 'partner'"
        >
          对方
        </button>
      </div>

      <template v-if="inventoryTab === 'pending'">
        <article v-for="r in myPendingRedemptions" :key="r.id" class="pm-redemption">
          <div>
            <strong>{{ r.reward_title ?? `#${r.reward_id}` }}</strong>
            <p>{{ r.points_spent }} 分 · {{ r.created_at.slice(0, 16) }}</p>
          </div>
          <button type="button" class="pm-btn pm-btn--soft" @click="onMarkFulfilled(r)">已使用</button>
        </article>
        <p v-if="!myPendingRedemptions.length" class="pm-empty">还没有待使用的奖励</p>
      </template>

      <template v-else-if="inventoryTab === 'done'">
        <article v-for="r in myFulfilledRedemptions" :key="r.id" class="pm-redemption pm-redemption--done">
          <div>
            <strong>{{ r.reward_title ?? `#${r.reward_id}` }}</strong>
            <p>{{ r.points_spent }} 分 · {{ r.fulfilled_at?.slice(0, 16) ?? '' }}</p>
          </div>
          <span class="pm-stamp">已兑</span>
        </article>
        <p v-if="!myFulfilledRedemptions.length" class="pm-empty">暂无已使用记录</p>
      </template>

      <template v-else>
        <article v-for="r in partnerRedemptions" :key="r.id" class="pm-redemption">
          <div>
            <strong>{{ r.reward_title ?? `#${r.reward_id}` }}</strong>
            <p>
              {{ personaLabel(r.redeemer_user_id) }} · {{ r.points_spent }} 分 ·
              {{ redemptionStatusLabel(r.status) }}
            </p>
          </div>
        </article>
        <p v-if="!partnerRedemptions.length" class="pm-empty">对方暂无兑换</p>
      </template>
    </section>

    <RewardForm ref="rewardFormRef" @saved="loadAll" />

    <van-popup v-model:show="showRejectPopup" position="bottom" round>
      <div class="reject-form">
        <h3>打回「{{ rejectTarget?.title }}」</h3>
        <van-field v-model="rejectReason" rows="2" autosize type="textarea" label="原因" placeholder="必填" />
        <van-button type="danger" block round @click="confirmReject">确认打回</van-button>
      </div>
    </van-popup>
  </div>
</template>

<style scoped>
.pm {
  padding: 12px 14px 36px;
}

.pm-hero {
  position: relative;
  overflow: hidden;
  border-radius: 28px;
  padding: 18px 16px 8px;
  margin-bottom: 18px;
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--primary) 16%, var(--card)), var(--card) 58%);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
  animation: pm-in 0.45s ease both;
}

.pm-hero__glow {
  position: absolute;
  width: 180px;
  height: 180px;
  right: -40px;
  top: -50px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--hero-glow), transparent 68%);
  pointer-events: none;
}

.pm-hero__head {
  position: relative;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.pm-hero h1 {
  margin: 0;
  font-size: 1.55rem;
  font-weight: 800;
  letter-spacing: -0.03em;
}

.pm-hero__hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.pm-hero__settle {
  flex-shrink: 0;
  border: 1px solid var(--line);
  background: var(--surface-elevated);
  color: var(--ink);
  font-size: 12px;
  font-weight: 800;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
  backdrop-filter: blur(8px);
}

.pm-hero__settle:disabled {
  opacity: 0.55;
}

.pm-block {
  margin-bottom: 22px;
  animation: pm-in 0.5s ease both;
  animation-delay: 0.06s;
}

.pm-block--alert {
  padding: 14px 12px 8px;
  border-radius: var(--radius);
  background: color-mix(in srgb, var(--workout) 10%, var(--card));
  border: 1px solid color-mix(in srgb, var(--workout) 35%, var(--line));
}

.pm-block__head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.pm-block__head h2 {
  margin: 0;
  font-size: 1.15rem;
  font-weight: 800;
}

.pm-block__hint {
  margin: 6px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  line-height: 1.4;
}

.pm-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  margin-left: 4px;
  border-radius: 999px;
  background: var(--primary);
  color: var(--on-primary, #fff);
  font-size: 11px;
  font-weight: 800;
  vertical-align: middle;
}

.pm-cats {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 10px;
  margin-bottom: 4px;
  scrollbar-width: none;
}

.pm-cats::-webkit-scrollbar {
  display: none;
}

.pm-cat {
  flex-shrink: 0;
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  padding: 8px 14px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.2s, color 0.2s, border-color 0.2s, transform 0.15s;
}

.pm-cat--on {
  background: var(--primary);
  border-color: transparent;
  color: var(--on-primary, #fff);
  transform: translateY(-1px);
}

.pm-btn {
  border: none;
  border-radius: 999px;
  font-weight: 800;
  font-size: 12px;
  padding: 8px 14px;
  cursor: pointer;
}

.pm-btn--primary {
  background: var(--primary);
  color: var(--on-primary, #fff);
}

.pm-btn--soft {
  background: color-mix(in srgb, var(--primary) 16%, var(--card));
  color: var(--primary-dark);
  border: 1px solid color-mix(in srgb, var(--primary) 30%, var(--line));
}

.pm-inv-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-bottom: 12px;
  padding: 4px;
  border-radius: 16px;
  background: color-mix(in srgb, var(--line) 55%, transparent);
}

.pm-inv-tab {
  border: none;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 800;
  padding: 10px 6px;
  border-radius: 12px;
  cursor: pointer;
}

.pm-inv-tab--on {
  background: var(--card);
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}

.pm-redemption {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  margin-bottom: 10px;
  border-radius: 18px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.pm-redemption strong {
  display: block;
  font-size: 15px;
  font-weight: 800;
  margin-bottom: 4px;
}

.pm-redemption p {
  margin: 0;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.pm-redemption--done {
  opacity: 0.85;
}

.pm-stamp {
  font-size: 11px;
  font-weight: 800;
  color: var(--muted);
  border: 1px dashed var(--line);
  padding: 4px 8px;
  border-radius: 8px;
}

.pm-empty {
  margin: 8px 0 0;
  padding: 20px;
  text-align: center;
  font-size: 13px;
  color: var(--muted);
  border: 1px dashed var(--line);
  border-radius: 16px;
  background: color-mix(in srgb, var(--card) 70%, transparent);
}

.reject-form {
  padding: 20px 16px calc(28px + env(safe-area-inset-bottom));
  background: var(--bg);
  color: var(--ink);
}

.reject-form h3 {
  margin: 0 0 12px;
  text-align: center;
  font-size: 1.05rem;
  font-weight: 800;
}

@keyframes pm-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
</style>
