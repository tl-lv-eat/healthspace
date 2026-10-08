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
  if (r.is_private) return '（私密 · 点击查看说明）'
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
  <van-cell-group v-for="r in rewards" :key="r.id" inset class="reward-item">
    <van-cell
      :title="r.title"
      :label="descriptionFor(r)"
    >
      <template #icon>
        <van-icon v-if="r.is_private" name="lock" class="reward-item__lock" />
      </template>
      <template #value>
        <div class="reward-item__meta">
          <span v-if="mode !== 'mall'" class="reward-item__tag">{{ statusLabel(r.status) }}</span>
          <span class="reward-item__price">{{ r.points_price }} 分</span>
        </div>
      </template>
    </van-cell>
    <van-cell
      v-if="mode === 'mall'"
      :title="rewardCategoryLabel(r.category)"
      title-class="reward-item__cat"
    />
    <van-cell v-if="r.reject_reason && mode === 'mine'" title="打回原因" :label="r.reject_reason" />
    <van-cell>
      <div class="reward-item__actions">
        <van-button
          v-if="mode === 'mall' && r.is_private && !revealed[r.id]"
          size="small"
          plain
          @click="onReveal(r)"
        >
          查看
        </van-button>
        <van-button
          v-if="mode === 'mall'"
          size="small"
          type="primary"
          :disabled="(balance ?? 0) < r.points_price"
          @click="onRedeem(r)"
        >
          兑换
        </van-button>
        <template v-if="mode === 'review'">
          <van-button size="small" type="primary" plain @click="onApprove(r)">通过</van-button>
          <van-button size="small" type="danger" plain @click="onReject(r)">打回</van-button>
        </template>
        <template v-if="mode === 'mine'">
          <van-button
            v-if="r.status === 'rejected' || r.status === 'pending_review'"
            size="small"
            plain
            @click="emit('edit', r)"
          >
            编辑
          </van-button>
          <van-button v-if="r.status === 'rejected'" size="small" type="primary" plain @click="onResubmit(r)">
            重新提交
          </van-button>
          <van-button v-if="r.status === 'listed'" size="small" plain @click="onArchive(r)">下架</van-button>
        </template>
      </div>
    </van-cell>
  </van-cell-group>
  <van-empty v-if="!rewards.length" :description="mode === 'review' ? '暂无待审核' : '暂无奖励'" />
</template>

<style scoped>
.reward-item {
  margin-bottom: 12px;
}

.reward-item__lock {
  margin-right: 6px;
  color: var(--van-orange);
}

.reward-item__meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.reward-item__tag {
  font-size: 11px;
  opacity: 0.65;
}

.reward-item__price {
  font-weight: 600;
  color: var(--van-primary-color);
}

.reward-item__cat {
  font-size: 12px;
  opacity: 0.7;
}

.reward-item__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: flex-end;
}
</style>
