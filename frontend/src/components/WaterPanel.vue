<script setup lang="ts">
import { computed, ref } from 'vue'
import { showConfirmDialog, showFailToast, showLoadingToast, closeToast } from 'vant'
import type { WaterEntry } from '@/api/water'
import { addWaterEntry, deleteWaterEntry, patchWaterEntry } from '@/api/water'

const props = defineProps<{
  date: string
  targetMl: number
  totalMl: number
  entries: WaterEntry[]
}>()

const emit = defineEmits<{ changed: [] }>()

const QUICK_AMOUNTS = [100, 200, 250, 500] as const

const editVisible = ref(false)
const editId = ref<number | null>(null)
const editAmount = ref('')

async function quickAdd(amount: number) {
  showLoadingToast({ message: '记录中…', forbidClick: true, duration: 0 })
  try {
    await addWaterEntry(props.date, amount)
    closeToast()
    emit('changed')
  } catch {
    closeToast()
    showFailToast('添加失败')
  }
}

function openEdit(entry: WaterEntry) {
  editId.value = entry.id
  editAmount.value = String(entry.amount_ml)
  editVisible.value = true
}

async function confirmEdit() {
  const id = editId.value
  const amount = parseInt(editAmount.value, 10)
  if (id == null || !Number.isFinite(amount) || amount <= 0) {
    showFailToast('请输入有效毫升数')
    return
  }
  editVisible.value = false
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await patchWaterEntry(id, amount)
    closeToast()
    emit('changed')
  } catch {
    closeToast()
    showFailToast('修改失败')
  }
}

async function onDelete(entry: WaterEntry) {
  try {
    await showConfirmDialog({
      title: '删除这条饮水记录？',
      message: `${entry.amount_ml} ml`,
    })
  } catch {
    return
  }
  showLoadingToast({ message: '删除中…', forbidClick: true, duration: 0 })
  try {
    await deleteWaterEntry(entry.id)
    closeToast()
    emit('changed')
  } catch {
    closeToast()
    showFailToast('删除失败')
  }
}

const progressPct = computed(() =>
  props.targetMl > 0 ? Math.min(100, Math.round((props.totalMl / props.targetMl) * 100)) : 0,
)
</script>

<template>
  <section class="water fit-card fit-card-pad">
    <header class="water__head">
      <div>
        <p class="fit-section-label">Hydration</p>
        <h2>饮水</h2>
      </div>
      <div class="water__ring" :style="{ '--p': `${progressPct}%` }">
        <strong>{{ progressPct }}%</strong>
      </div>
    </header>

    <p class="water__totals">
      <span class="water__now">{{ totalMl }}</span>
      <span class="water__sep">/</span>
      <span>{{ targetMl }} ml</span>
    </p>

    <div class="water__quick">
      <button
        v-for="amt in QUICK_AMOUNTS"
        :key="amt"
        type="button"
        class="water__chip"
        @click="quickAdd(amt)"
      >
        +{{ amt }}
      </button>
    </div>

    <ul v-if="entries.length" class="water__list">
      <li v-for="e in entries" :key="e.id">
        <button type="button" class="water__row" @click="openEdit(e)">
          <span>{{ e.amount_ml }} ml</span>
          <time>{{ e.created_at.slice(11, 16) }}</time>
        </button>
        <button type="button" class="water__del" @click="onDelete(e)">删</button>
      </li>
    </ul>
    <p v-else class="water__empty">点上方快速加水</p>

    <van-dialog
      v-model:show="editVisible"
      title="修改饮水量 (ml)"
      show-cancel-button
      @confirm="confirmEdit"
    >
      <van-field v-model="editAmount" type="digit" label="毫升" placeholder="例如 250" />
    </van-dialog>
  </section>
</template>

<style scoped>
.water {
  margin-bottom: 14px;
}

.water__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.water h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 800;
}

.water__ring {
  width: 54px;
  height: 54px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, var(--card) 58%, transparent 59%),
    conic-gradient(var(--water) var(--p), var(--water-soft) 0);
  font-size: 12px;
  color: var(--water);
}

.water__totals {
  margin: 12px 0 0;
  font-size: 14px;
  color: var(--muted);
  font-weight: 600;
}

.water__now {
  font-family: var(--font-display);
  font-size: 1.75rem;
  font-weight: 800;
  color: var(--water);
}

.water__sep {
  margin: 0 4px;
}

.water__quick {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0 8px;
}

.water__chip {
  border: none;
  background: var(--water-soft);
  color: #1c7ed6;
  font-weight: 800;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 12px;
  cursor: pointer;
}

.water__list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
}

.water__list li {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--line);
}

.water__row {
  flex: 1;
  display: flex;
  justify-content: space-between;
  padding: 12px 0;
  border: none;
  background: transparent;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  color: var(--ink);
}

.water__row time {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.water__del {
  border: none;
  background: var(--cal-soft);
  color: var(--cal);
  font-size: 12px;
  font-weight: 800;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.water__empty {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--muted);
}
</style>
