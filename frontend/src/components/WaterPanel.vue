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

const remain = computed(() => Math.max(0, props.targetMl - props.totalMl))
</script>

<template>
  <section class="panel">
    <header class="panel__head">
      <div>
        <p class="fit-section-label">Hydration</p>
        <h2>饮水</h2>
        <p class="panel__sub">
          {{ remain > 0 ? `还差 ${remain} ml` : '今日目标已达成' }}
        </p>
      </div>
      <div class="panel__ring" :style="{ '--p': `${progressPct}%` }">
        <strong>{{ progressPct }}%</strong>
      </div>
    </header>

    <p class="panel__totals">
      <span class="panel__now">{{ totalMl }}</span>
      <span class="panel__sep">/</span>
      <span>{{ targetMl }} ml</span>
    </p>

    <div class="panel__track" aria-hidden="true">
      <div class="panel__fill" :style="{ width: `${progressPct}%` }" />
    </div>

    <div class="panel__quick">
      <button
        v-for="amt in QUICK_AMOUNTS"
        :key="amt"
        type="button"
        class="panel__chip"
        @click="quickAdd(amt)"
      >
        +{{ amt }}
      </button>
    </div>

    <ul v-if="entries.length" class="panel__list">
      <li v-for="e in entries" :key="e.id">
        <button type="button" class="panel__row" @click="openEdit(e)">
          <span>{{ e.amount_ml }} ml</span>
          <time>{{ e.created_at.slice(11, 16) }}</time>
        </button>
        <button type="button" class="panel__del" @click="onDelete(e)">删</button>
      </li>
    </ul>
    <p v-else class="panel__empty">轻点上方快捷加水</p>

    <van-popup v-model:show="editVisible" position="bottom" round :style="{ padding: '8px 0 24px' }">
      <div class="edit-sheet">
        <h3>修改饮水量</h3>
        <van-field v-model="editAmount" type="digit" label="毫升" placeholder="例如 250" />
        <div class="edit-sheet__actions">
          <van-button block @click="editVisible = false">取消</van-button>
          <van-button type="primary" block @click="confirmEdit">保存</van-button>
        </div>
      </div>
    </van-popup>
  </section>
</template>

<style scoped>
.panel {
  margin-bottom: 14px;
  padding: 18px 16px;
  border-radius: 24px;
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--water) 14%, var(--card)), var(--card) 52%);
  border: 1px solid var(--line);
  box-shadow: var(--shadow);
}

.panel__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.panel__head h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 700;
}

.panel__sub {
  margin: 6px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
}

.panel__ring {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at center, var(--card) 56%, transparent 57%),
    conic-gradient(var(--water) var(--p), var(--line) 0);
  font-size: 12px;
  color: var(--water);
  font-family: var(--font-display);
}

.panel__totals {
  margin: 14px 0 0;
  font-size: 14px;
  color: var(--muted);
  font-weight: 600;
}

.panel__now {
  font-family: var(--font-display);
  font-size: 1.85rem;
  font-weight: 700;
  color: var(--water);
}

.panel__sep {
  margin: 0 4px;
}

.panel__track {
  margin-top: 12px;
  height: 8px;
  border-radius: 999px;
  background: var(--line);
  overflow: hidden;
}

.panel__fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--water), color-mix(in srgb, var(--water) 60%, #fff));
  transition: width 0.4s ease;
}

.panel__quick {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 16px 0 8px;
}

.panel__chip {
  border: none;
  background: var(--water-soft);
  color: var(--water);
  font-weight: 800;
  font-size: 13px;
  padding: 10px 14px;
  border-radius: 999px;
  cursor: pointer;
}

.panel__list {
  list-style: none;
  margin: 8px 0 0;
  padding: 0;
}

.panel__list li {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--line);
}

.panel__row {
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

.panel__row time {
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.panel__del {
  border: none;
  background: var(--cal-soft);
  color: var(--cal);
  font-size: 12px;
  font-weight: 800;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}

.panel__empty {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--muted);
}

.edit-sheet {
  padding: 16px;
}

.edit-sheet h3 {
  margin: 0 0 8px;
  font-size: 1.1rem;
  font-weight: 800;
}

.edit-sheet__actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 12px;
}
</style>
