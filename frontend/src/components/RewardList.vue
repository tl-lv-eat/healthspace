<script setup lang="ts">
import { ref } from 'vue'
import { showConfirmDialog, showFailToast, showSuccessToast } from 'vant'
import {
  redeemReward,
  revealReward,
  approveReward,
  resubmitReward,
  archiveReward,
  rewardCategoryLabel,
  type Reward,
} from '@/api/rewards'

const props = defineProps<{
  rewards: Reward[]
  balance?: number
  mode: 'mall' | 'review' | 'mine'
}>()

const emit = defineEmits<{
  (e: 'changed'): void
  (e: 'reject', reward: Reward): void
  (e: 'edit', reward: Reward): void
}>()

const revealed = ref<Record<number, string>>({})

async function onReveal(r: Reward) {
  try {
    await showConfirmDialog({ title: '查看私密说明', message: '确认查看完整奖励说明？' })
    const desc = await revealReward(r.id)
    revealed.value[r.id] = desc
  } catch {
    /* cancelled */
  }
}

function descriptionFor(r: Reward): string {
  if (revealed.value[r.id]) return revealed.value[r.id]
  if (props.mode === 'mine' || !r.is_private) return r.description ?? ''
  if (r.is_private) return '私密奖励 · 点查看可解锁说明'
  return r.description ?? ''
}

function statusLabel(status: Reward['status']): string {
  const map: Record<Reward['status'], string> = {
    pending_review: '待审核',
    listed: '已上架',
    rejected: '已打回',
    archived: '已下架',
  }
  return map[status] ?? status
}

async function onRedeem(r: Reward) {
  const bal = props.balance ?? 0
  try {
    await showConfirmDialog({
      title: '兑换',
      message: `花费 ${r.points_price} 积分兑换「${r.title}」？`,
    })
    await redeemReward(r.id)
    showSuccessToast('已兑换，待使用')
    emit('changed')
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 400) {
      showFailToast(bal < r.points_price ? '积分不足' : '无法兑换')
    }
  }
}

async function onApprove(r: Reward) {
  try {
    await showConfirmDialog({ title: '通过上架', message: `通过「${r.title}」？` })
    await approveReward(r.id)
    showSuccessToast('已通过')
    emit('changed')
  } catch {
    /* cancelled or error */
  }
}

function onReject(r: Reward) {
  emit('reject', r)
}

async function onResubmit(r: Reward) {
  try {
    await resubmitReward(r.id)
    showSuccessToast('已重新提交审核')
    emit('changed')
  } catch {
    showFailToast('提交失败')
  }
}

async function onArchive(r: Reward) {
  try {
    await showConfirmDialog({ title: '下架', message: `下架「${r.title}」？` })
    await archiveReward(r.id)
    showSuccessToast('已下架')
    emit('changed')
  } catch {
    /* cancelled */
  }
}
</script>

<template>
  <div class="rl">
    <article v-for="r in rewards" :key="r.id" class="rl-card" :class="`rl-card--${r.category}`">
      <header class="rl-card__top">
        <div class="rl-card__titles">
          <span class="rl-card__cat">{{ rewardCategoryLabel(r.category) }}</span>
          <h3>
            <van-icon v-if="r.is_private" name="lock" class="rl-card__lock" />
            {{ r.title }}
          </h3>
          <p>{{ descriptionFor(r) || '暂无说明' }}</p>
        </div>
        <div class="rl-card__price">
          <strong>{{ r.points_price }}</strong>
          <span>分</span>
        </div>
      </header>

      <p v-if="mode !== 'mall'" class="rl-card__status">{{ statusLabel(r.status) }}</p>
      <p v-if="r.reject_reason && mode === 'mine'" class="rl-card__reject">打回：{{ r.reject_reason }}</p>

      <footer class="rl-card__actions">
        <button
          v-if="mode === 'mall' && r.is_private && !revealed[r.id]"
          type="button"
          class="rl-btn"
          @click="onReveal(r)"
        >
          查看
        </button>
        <button
          v-if="mode === 'mall'"
          type="button"
          class="rl-btn rl-btn--primary"
          :disabled="(balance ?? 0) < r.points_price"
          @click="onRedeem(r)"
        >
          兑换
        </button>
        <template v-if="mode === 'review'">
          <button type="button" class="rl-btn rl-btn--primary" @click="onApprove(r)">通过</button>
          <button type="button" class="rl-btn rl-btn--danger" @click="onReject(r)">打回</button>
        </template>
        <template v-if="mode === 'mine'">
          <button
            v-if="r.status === 'rejected' || r.status === 'pending_review'"
            type="button"
            class="rl-btn"
            @click="emit('edit', r)"
          >
            编辑
          </button>
          <button
            v-if="r.status === 'rejected'"
            type="button"
            class="rl-btn rl-btn--primary"
            @click="onResubmit(r)"
          >
            重新提交
          </button>
          <button v-if="r.status === 'listed'" type="button" class="rl-btn" @click="onArchive(r)">
            下架
          </button>
        </template>
      </footer>
    </article>

    <p v-if="!rewards.length" class="rl-empty">
      {{ mode === 'review' ? '暂无待审核' : mode === 'mine' ? '暂无提案' : '该分类暂无奖励' }}
    </p>
  </div>
</template>

<style scoped>
.rl {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rl-card {
  padding: 14px 14px 12px;
  border-radius: 18px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}

.rl-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--primary);
}

.rl-card--food::before {
  background: var(--cal);
}
.rl-card--fun::before {
  background: var(--workout);
}
.rl-card--intimacy::before {
  background: var(--primary);
}
.rl-card--adult::before {
  background: color-mix(in srgb, var(--ink) 55%, var(--primary));
}

.rl-card__top {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.rl-card__titles {
  flex: 1;
  min-width: 0;
}

.rl-card__cat {
  display: inline-block;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 4px;
  font-family: var(--font-display);
}

.rl-card h3 {
  margin: 0;
  font-size: 1.02rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  gap: 4px;
}

.rl-card__lock {
  color: var(--workout);
}

.rl-card p {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--muted);
  font-weight: 600;
}

.rl-card__price {
  text-align: right;
  flex-shrink: 0;
}

.rl-card__price strong {
  display: block;
  font-size: 1.35rem;
  font-weight: 800;
  font-family: var(--font-display);
  color: var(--primary-dark);
  line-height: 1;
}

.rl-card__price span {
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
}

.rl-card__status {
  margin-top: 8px !important;
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary) 12%, var(--card));
  color: var(--primary-dark) !important;
  font-size: 11px !important;
}

.rl-card__reject {
  color: var(--cal) !important;
}

.rl-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
  margin-top: 12px;
}

.rl-btn {
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
  font-size: 12px;
  font-weight: 800;
  padding: 7px 12px;
  border-radius: 999px;
  cursor: pointer;
}

.rl-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.rl-btn--primary {
  background: var(--primary);
  border-color: transparent;
  color: var(--on-primary, #fff);
}

.rl-btn--danger {
  border-color: color-mix(in srgb, var(--cal) 40%, var(--line));
  color: var(--cal);
  background: color-mix(in srgb, var(--cal) 10%, var(--card));
}

.rl-empty {
  margin: 0;
  padding: 22px;
  text-align: center;
  font-size: 13px;
  color: var(--muted);
  border: 1px dashed var(--line);
  border-radius: 16px;
  background: color-mix(in srgb, var(--card) 65%, transparent);
}
</style>
