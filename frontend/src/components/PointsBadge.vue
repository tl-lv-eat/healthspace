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
  <button type="button" class="pb" @click="openLedger">
    <div class="pb__ring" aria-hidden="true">
      <span class="pb__ring-glow" />
    </div>
    <div class="pb__body">
      <span class="pb__label">可用积分</span>
      <strong class="pb__value">{{ balance }}</strong>
      <span class="pb__cta">查看流水 ›</span>
    </div>
  </button>

  <van-action-sheet v-model:show="showLedger" title="积分流水" @open="reloadBalance">
    <div class="pb-sheet">
      <van-loading v-if="loadingLedger" vertical>加载中</van-loading>
      <ul v-else class="pb-ledger">
        <li v-for="row in ledger" :key="row.id" class="pb-ledger__row">
          <div>
            <strong>{{ row.reason }}</strong>
            <p>{{ row.created_at.slice(0, 16) }}</p>
          </div>
          <span :class="row.delta >= 0 ? 'up' : 'down'">
            {{ row.delta > 0 ? '+' : '' }}{{ row.delta }}
          </span>
        </li>
        <li v-if="!ledger.length" class="pb-ledger__empty">暂无流水</li>
      </ul>
    </div>
  </van-action-sheet>
</template>

<style scoped>
.pb {
  position: relative;
  display: flex;
  width: 100%;
  align-items: center;
  gap: 14px;
  margin: 8px 0 12px;
  padding: 16px 18px;
  border: 1px solid color-mix(in srgb, var(--primary) 28%, var(--line));
  border-radius: 20px;
  background:
    linear-gradient(120deg, color-mix(in srgb, var(--primary) 14%, transparent), transparent 55%),
    var(--surface-elevated);
  color: var(--ink);
  text-align: left;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(10px);
}

.pb__ring {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  background:
    conic-gradient(from 210deg, var(--primary), color-mix(in srgb, var(--accent) 70%, #fff), var(--primary));
  display: grid;
  place-items: center;
  flex-shrink: 0;
}

.pb__ring::after {
  content: '';
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: var(--card);
}

.pb__ring-glow {
  display: none;
}

.pb__body {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.pb__label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  font-family: var(--font-display);
}

.pb__value {
  font-size: 2rem;
  font-weight: 800;
  line-height: 1.1;
  font-family: var(--font-display);
  letter-spacing: -0.04em;
}

.pb__cta {
  font-size: 12px;
  font-weight: 700;
  color: var(--primary-dark);
}

.pb-sheet {
  padding: 8px 16px 28px;
  max-height: 55vh;
  overflow: auto;
  background: var(--bg);
  color: var(--ink);
}

.pb-ledger {
  list-style: none;
  margin: 0;
  padding: 0;
}

.pb-ledger__row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid var(--line);
}

.pb-ledger__row strong {
  display: block;
  font-size: 14px;
  font-weight: 800;
}

.pb-ledger__row p {
  margin: 4px 0 0;
  font-size: 11px;
  color: var(--muted);
}

.pb-ledger__row .up {
  font-weight: 800;
  color: #2f9e6b;
}

.pb-ledger__row .down {
  font-weight: 800;
  color: var(--cal);
}

.pb-ledger__empty {
  padding: 28px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}
</style>
