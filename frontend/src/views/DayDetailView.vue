<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { showFailToast } from 'vant'
import { fetchCalendarDay, type CalendarDayDetail } from '@/api/calendar'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const detail = ref<CalendarDayDetail | null>(null)

const date = () => String(route.params.date ?? '')

async function load() {
  try {
    detail.value = await fetchCalendarDay(date())
  } catch {
    showFailToast('加载日详情失败')
  }
}

function editToday() {
  void router.push({ name: 'today', query: { date: date() } })
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="day-detail">
    <van-nav-bar :title="date()" left-arrow @click-left="router.back()" />

    <template v-if="detail">
      <section class="fit-card day-detail__block">
        <h2>{{ detail.dragon.display_name }} · {{ detail.dragon.status.level }}</h2>
        <p>
          饮食 {{ detail.dragon.status.meal ? '✓' : '—' }} · 饮水
          {{ detail.dragon.status.water ? '✓' : '—' }} · 运动
          {{ detail.dragon.status.workout ? '✓' : '—' }}
        </p>
      </section>
      <section class="fit-card day-detail__block">
        <h2>{{ detail.leaf.display_name }} · {{ detail.leaf.status.level }}</h2>
        <p>
          饮食 {{ detail.leaf.status.meal ? '✓' : '—' }} · 饮水
          {{ detail.leaf.status.water ? '✓' : '—' }} · 运动
          {{ detail.leaf.status.workout ? '✓' : '—' }}
        </p>
      </section>

      <section v-if="detail.me.user_id === auth.user?.id" class="fit-card day-detail__block">
        <h2>我的记录</h2>
        <p>餐 {{ detail.me.meals.length }} · 饮水 {{ detail.me.water.total_ml }} ml · 运动 {{ detail.me.workouts.length }}</p>
        <van-button block type="primary" @click="editToday">编辑今日</van-button>
      </section>
    </template>
  </div>
</template>

<style scoped>
.day-detail {
  padding-bottom: 32px;
}

.day-detail__block {
  margin: 12px 16px;
  padding: 16px;
}

.day-detail__block h2 {
  margin: 0 0 8px;
  font-size: 1rem;
}

.day-detail__block p {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--muted);
}
</style>
