<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast } from 'vant'
import WaterPanel from '@/components/WaterPanel.vue'
import MealPanel from '@/components/MealPanel.vue'
import { useAuthStore } from '@/stores/auth'
import {
  fetchToday,
  formatDateLabel,
  formatDateLocal,
  type TodayResponse,
} from '@/api/today'
import { fetchWaterDay, type WaterDay } from '@/api/water'
import { formatWorkoutSummary } from '@/api/workouts'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
function dateFromRoute(): string {
  const q = route.query.date
  if (typeof q === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(q)) return q
  return formatDateLocal()
}

const date = ref(dateFromRoute())
const today = ref<TodayResponse | null>(null)
const waterDay = ref<WaterDay | null>(null)
const refreshing = ref(false)

async function reload(withOverlay = false) {
  if (withOverlay) {
    showLoadingToast({ message: '加载中…', forbidClick: true, duration: 0 })
  }
  try {
    const [t, w] = await Promise.all([fetchToday(date.value), fetchWaterDay(date.value)])
    today.value = t
    waterDay.value = w
  } catch {
    showFailToast('加载今日数据失败')
  } finally {
    refreshing.value = false
    if (withOverlay) closeToast()
  }
}

watch(
  () => route.query.date,
  () => {
    const next = dateFromRoute()
    if (next !== date.value) {
      date.value = next
      void reload(true)
    }
  },
)

onMounted(() => {
  date.value = dateFromRoute()
  void reload(true)
})

function doneLabel(ok: boolean): string {
  return ok ? '✓' : '—'
}

function goWorkout() {
  router.push({ name: 'workout', query: { date: date.value } })
}

function partnerSummary(): string {
  const p = today.value?.partner
  if (!p) return ''
  return `${p.display_name}：饮食 ${doneLabel(p.done.meal)} · 饮水 ${doneLabel(p.done.water)} (${p.water_total_ml}/${p.water_target_ml}ml) · 运动 ${doneLabel(p.done.workout)}`
}
</script>

<template>
  <div class="today-shell">
    <van-nav-bar :title="formatDateLabel(date)" fixed placeholder />
    <div v-if="today" class="partner-bar">
      {{ partnerSummary() }}
    </div>
    <main class="today-body">
      <van-pull-refresh v-model="refreshing" @refresh="reload()">
        <template v-if="today && waterDay">
          <WaterPanel
            :date="date"
            :target-ml="waterDay.target_ml"
            :total-ml="waterDay.total_ml"
            :entries="waterDay.entries"
            @changed="reload()"
          />
          <MealPanel :date="date" :meals="today.me.meals" @changed="reload()" />
          <section class="panel workout-panel">
            <header class="panel-head">
              <h2>运动</h2>
              <van-button size="small" type="primary" plain round @click="goWorkout">去记录</van-button>
            </header>
            <van-cell-group v-if="today.me.workouts.length" inset class="entry-list">
              <van-cell
                v-for="w in today.me.workouts"
                :key="w.id"
                :title="formatWorkoutSummary(w)"
                :label="w.created_at.slice(11, 16)"
              />
            </van-cell-group>
            <p v-else class="empty-hint">今天还没有运动记录</p>
          </section>
        </template>
        <van-empty v-else description="暂无数据" />
      </van-pull-refresh>
    </main>
    <footer v-if="auth.user" class="today-foot">{{ auth.user.display_name }} 的今日</footer>
  </div>
</template>

<style scoped>
.today-shell {
  min-height: 100vh;
  background: #f7f8fa;
}

.partner-bar {
  padding: 8px 16px;
  font-size: 12px;
  line-height: 1.5;
  color: #646566;
  background: #fff;
  border-bottom: 1px solid #ebedf0;
}

.today-body {
  padding: 16px 16px 32px;
}

.today-foot {
  text-align: center;
  padding: 12px;
  font-size: 12px;
  color: #c8c9cc;
}

.panel {
  margin-bottom: 20px;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.panel-head h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}

.entry-list {
  margin: 0 !important;
}

.empty-hint {
  margin: 8px 4px 0;
  font-size: 13px;
  color: #969799;
}
</style>
