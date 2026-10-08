<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showConfirmDialog, showFailToast, showLoadingToast } from 'vant'
import CardioForm from '@/components/CardioForm.vue'
import StrengthPicker from '@/components/StrengthPicker.vue'
import { formatDateLabel, formatDateLocal } from '@/api/today'
import {
  deleteWorkout,
  fetchWorkouts,
  formatWorkoutSummary,
  type Workout,
} from '@/api/workouts'

const route = useRoute()
const router = useRouter()

const date = computed(() => {
  const q = route.query.date
  return typeof q === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(q) ? q : formatDateLocal()
})

const workouts = ref<Workout[]>([])
const activeTab = ref(0)

async function reload(withOverlay = false) {
  if (withOverlay) {
    showLoadingToast({ message: '加载中…', forbidClick: true, duration: 0 })
  }
  try {
    workouts.value = await fetchWorkouts(date.value)
  } catch {
    showFailToast('加载运动记录失败')
  } finally {
    if (withOverlay) closeToast()
  }
}

onMounted(() => {
  void reload(true)
})

function goBack() {
  router.push({ name: 'today', query: { date: date.value } })
}

async function onDelete(w: Workout) {
  try {
    await showConfirmDialog({
      title: '删除这条运动？',
      message: formatWorkoutSummary(w),
    })
  } catch {
    return
  }
  showLoadingToast({ message: '删除中…', forbidClick: true, duration: 0 })
  try {
    await deleteWorkout(w.id)
    closeToast()
    await reload()
  } catch {
    closeToast()
    showFailToast('删除失败')
  }
}
</script>

<template>
  <div class="workout-shell">
    <van-nav-bar
      title="记录运动"
      left-text="返回"
      left-arrow
      fixed
      placeholder
      @click-left="goBack"
    />
    <p class="date-line">{{ formatDateLabel(date) }}</p>

    <section v-if="workouts.length" class="logged">
      <h3>今日已记</h3>
      <van-cell-group inset>
        <van-swipe-cell v-for="w in workouts" :key="w.id">
          <van-cell :title="formatWorkoutSummary(w)" :label="w.created_at.slice(11, 16)" />
          <template #right>
            <van-button square type="danger" text="删除" class="swipe-btn" @click="onDelete(w)" />
          </template>
        </van-swipe-cell>
      </van-cell-group>
    </section>

    <van-tabs v-model:active="activeTab" sticky offset-top="46">
      <van-tab title="有氧">
        <CardioForm :date="date" @saved="reload()" />
      </van-tab>
      <van-tab title="力量">
        <StrengthPicker :date="date" @saved="reload()" />
      </van-tab>
    </van-tabs>
  </div>
</template>

<style scoped>
.workout-shell {
  min-height: 100vh;
  background: #f7f8fa;
  padding-bottom: 32px;
}

.date-line {
  margin: 0;
  padding: 10px 16px;
  font-size: 13px;
  color: #646566;
  background: #fff;
  border-bottom: 1px solid #ebedf0;
}

.logged {
  padding: 16px 0 0;
}

.logged h3 {
  margin: 0 16px 10px;
  font-size: 14px;
  font-weight: 600;
  color: #646566;
}

.swipe-btn {
  height: 100%;
}

:deep(.van-tabs__content) {
  padding: 0 16px;
}
</style>
