<script setup lang="ts">
import { ref } from 'vue'
import { showConfirmDialog, showFailToast, showSuccessToast } from 'vant'
import { redeemReward, revealReward, type Reward } from '@/api/rewards'

defineProps<{ rewards: Reward[]; balance: number }>()

const emit = defineEmits<{ (e: 'redeemed'): void }>()

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
  if (r.is_private) return '（私密 · 点击查看说明）'
  return r.description ?? ''
}

async function onRedeem(r: Reward) {
  try {
    await showConfirmDialog({
      title: '兑换',
      message: `花费 ${r.points_price} 积分兑换「${r.title}」？`,
    })
    await redeemReward(r.id)
    showSuccessToast('已提交兑奖')
    emit('redeemed')
  } catch (e: unknown) {
    const err = e as { response?: { status?: number } }
    if (err.response?.status === 400) {
      showFailToast('积分不足')
    }
  }
}
</script>

<template>
  <van-cell-group v-for="r in rewards" :key="r.id" inset class="reward-item">
    <van-cell :title="r.title" :label="descriptionFor(r)">
      <template #icon>
        <van-icon v-if="r.is_private" name="lock" class="reward-item__lock" />
      </template>
      <template #value>
        <span class="reward-item__price">{{ r.points_price }} 分</span>
      </template>
    </van-cell>
    <van-cell>
      <div class="reward-item__actions">
        <van-button v-if="r.is_private && !revealed[r.id]" size="small" plain @click="onReveal(r)">
          查看
        </van-button>
        <van-button size="small" type="primary" :disabled="balance < r.points_price" @click="onRedeem(r)">
          兑换
        </van-button>
      </div>
    </van-cell>
  </van-cell-group>
  <van-empty v-if="!rewards.length" description="还没有奖励，先添加一个吧" />
</template>

<style scoped>
.reward-item {
  margin-bottom: 12px;
}

.reward-item__lock {
  margin-right: 6px;
  color: var(--van-orange);
}

.reward-item__price {
  font-weight: 600;
  color: var(--van-primary-color);
}

.reward-item__actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
