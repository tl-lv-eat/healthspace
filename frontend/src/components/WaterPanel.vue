<script setup lang="ts">
import { ref } from 'vue'
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

const progressPct = () =>
  props.targetMl > 0 ? Math.min(100, Math.round((props.totalMl / props.targetMl) * 100)) : 0
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <h2>饮水</h2>
      <span class="totals">{{ totalMl }} / {{ targetMl }} ml</span>
    </header>
    <van-progress :percentage="progressPct()" stroke-width="8" />

    <div class="quick-row">
      <van-button
        v-for="amt in QUICK_AMOUNTS"
        :key="amt"
        size="small"
        type="primary"
        plain
        round
        @click="quickAdd(amt)"
      >
        +{{ amt }}
      </van-button>
    </div>

    <van-cell-group v-if="entries.length" inset class="entry-list">
      <van-swipe-cell v-for="e in entries" :key="e.id">
        <van-cell :title="`${e.amount_ml} ml`" :label="e.created_at.slice(11, 16)" is-link @click="openEdit(e)" />
        <template #right>
          <van-button square type="danger" text="删除" class="swipe-btn" @click="onDelete(e)" />
        </template>
      </van-swipe-cell>
    </van-cell-group>
    <p v-else class="empty-hint">点上方按钮快速加水</p>

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
.panel {
  margin-bottom: 20px;
}

.panel-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.panel-head h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}

.totals {
  font-size: 14px;
  color: #646566;
}

.quick-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 14px 0 12px;
}

.entry-list {
  margin: 0 !important;
}

.swipe-btn {
  height: 100%;
}

.empty-hint {
  margin: 8px 4px 0;
  font-size: 13px;
  color: #969799;
}
</style>
