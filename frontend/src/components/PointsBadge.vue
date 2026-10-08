<script setup lang="ts">
import { ref } from 'vue'
import { fetchPointsBalance, fetchPointsLedger, type LedgerEntry } from '@/api/points'

defineProps<{ balance: number }>()

const emit = defineEmits<{ (e: 'refresh'): void }>()

const showLedger = ref(false)
const ledger = ref<LedgerEntry[]>([])
const loadingLedger = ref(false)

async function openLedger() {
  showLedger.value = true
  loadingLedger.value = true
  try {
    ledger.value = await fetchPointsLedger()
  } finally {
    loadingLedger.value = false
  }
}

async function reloadBalance() {
  emit('refresh')
  try {
    await fetchPointsBalance()
  } catch {
    /* parent handles */
  }
}
</script>

<template>
  <div class="points-badge fit-card" @click="openLedger">
    <span class="points-badge__label">积分</span>
    <strong class="points-badge__value">{{ balance }}</strong>
    <van-icon name="arrow" class="points-badge__arrow" />
  </div>

  <van-action-sheet v-model:show="showLedger" title="积分流水" @open="reloadBalance">
    <van-loading v-if="loadingLedger" vertical>加载中</van-loading>
    <van-cell-group v-else inset>
      <van-cell
        v-for="row in ledger"
        :key="row.id"
        :title="row.reason"
        :value="(row.delta > 0 ? '+' : '') + row.delta"
        :label="row.created_at.slice(0, 16)"
      />
      <van-empty v-if="!ledger.length" description="暂无流水" />
    </van-cell-group>
  </van-action-sheet>
</template>

<style scoped>
.points-badge {
  margin: 0 16px 16px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.points-badge__label {
  font-size: 13px;
  opacity: 0.7;
}

.points-badge__value {
  font-size: 1.75rem;
  flex: 1;
}

.points-badge__arrow {
  opacity: 0.4;
}
</style>
