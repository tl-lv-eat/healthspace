<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showFailToast } from 'vant'
import DaySectionPanel from '@/components/DaySectionPanel.vue'
import { fetchCalendarDay, type CalendarDayDetail } from '@/api/calendar'
import { formatDateLabel } from '@/api/today'

const route = useRoute()
const router = useRouter()
const detail = ref<CalendarDayDetail | null>(null)

const dateStr = computed(() => String(route.params.date ?? ''))

async function load() {
  try {
    detail.value = await fetchCalendarDay(dateStr.value)
  } catch {
    showFailToast('加载日详情失败')
  }
}

function editToday() {
  void router.push({ name: 'today', query: { date: dateStr.value } })
}

const columns = computed(() => {
  if (!detail.value) return []
  const d = detail.value
  return [
    {
      key: 'dragon' as const,
      displayName: d.dragon.display_name,
      status: d.dragon.status,
      section: d.sections.dragon,
    },
    {
      key: 'leaf' as const,
      displayName: d.leaf.display_name,
      status: d.leaf.status,
      section: d.sections.leaf,
    },
  ]
})

watch(dateStr, () => {
  void load()
})

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="day">
    <header class="day__bar">
      <button type="button" class="day__back" aria-label="返回" @click="router.back()">←</button>
      <h1>{{ formatDateLabel(dateStr) }}</h1>
      <button type="button" class="day__edit" @click="editToday">去改记</button>
    </header>

    <div v-if="detail" class="day__grid">
      <DaySectionPanel
        v-for="col in columns"
        :key="col.key"
        :section="col.section"
        :display-name="col.displayName"
        :status="col.status"
      />
    </div>
    <p v-else class="day__loading">加载中…</p>
  </div>
</template>

<style scoped>
.day {
  padding: 12px 14px 40px;
}

.day__bar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.day__bar h1 {
  flex: 1;
  margin: 0;
  font-size: 1.05rem;
  font-weight: 800;
  min-width: 0;
}

.day__back,
.day__edit {
  border: none;
  background: var(--card);
  color: var(--ink);
  font-weight: 800;
  padding: 8px 12px;
  border-radius: 999px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  flex-shrink: 0;
}

.day__edit {
  background: var(--primary);
  color: var(--on-primary, #fff);
}

.day__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  align-items: start;
}

@media (max-width: 640px) {
  .day__grid {
    grid-template-columns: 1fr;
  }
}

.day__loading {
  margin: 24px 0;
  text-align: center;
  font-size: 13px;
  color: var(--muted);
  font-weight: 600;
}
</style>
