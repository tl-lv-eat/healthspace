<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { showFailToast } from 'vant'
import { fetchJournal, type JournalItem } from '@/api/journal'

const filter = ref<'all' | 'dragon' | 'leaf'>('all')
const items = ref<JournalItem[]>([])

const range = computed(() => {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 30)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  return { from: fmt(start), to: fmt(end) }
})

async function load() {
  try {
    const uid = filter.value === 'all' ? undefined : filter.value
    items.value = await fetchJournal(range.value.from, range.value.to, uid)
  } catch {
    showFailToast('加载日志失败')
  }
}

watch(filter, () => {
  void load()
})

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="journal-page">
    <header class="journal-page__hero fit-card">
      <p class="fit-section-label">Journal</p>
      <h1>日志摘要</h1>
    </header>

    <van-tabs v-model:active="filter">
      <van-tab title="双方" name="all" />
      <van-tab title="🐉" name="dragon" />
      <van-tab title="🍃" name="leaf" />
    </van-tabs>

    <van-cell-group inset>
      <van-cell v-for="item in items" :key="item.date" :title="item.date">
        <template #label>
          <div v-for="u in item.users" :key="u.user_id" class="journal-row">
            <strong>{{ u.display_name }}</strong>
            餐{{ u.meal_done ? '✓' : '—' }} · 水 {{ u.water_total_ml }}/{{ u.water_target_ml }} · 动{{
              u.workout_done ? '✓' : '—'
            }}
          </div>
        </template>
      </van-cell>
    </van-cell-group>
  </div>
</template>

<style scoped>
.journal-page {
  padding: 20px 0 32px;
}

.journal-page__hero {
  margin: 0 16px 16px;
  padding: 24px 20px;
}

.journal-page__hero h1 {
  margin: 0;
  font-size: 1.5rem;
}

.journal-row {
  margin-top: 4px;
  font-size: 13px;
}
</style>
