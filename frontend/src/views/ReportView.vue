<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast, showSuccessToast } from 'vant'
import { fetchReport, generateReport, type AiReport } from '@/api/reports'
import { formatDateLocal } from '@/api/today'

const route = useRoute()
const router = useRouter()

const kind = ref<'daily' | 'weekly'>('daily')
const period = ref(formatDateLocal())
const report = ref<AiReport | null>(null)
const loading = ref(false)

const title = computed(() => (kind.value === 'daily' ? 'AI 日报告' : 'AI 周报'))

function mondayOf(iso: string): string {
  const d = new Date(iso + 'T12:00:00')
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  d.setDate(d.getDate() + diff)
  return d.toISOString().slice(0, 10)
}

async function load() {
  loading.value = true
  try {
    report.value = await fetchReport(kind.value, period.value)
  } catch {
    report.value = null
  } finally {
    loading.value = false
  }
}

async function onGenerate(force: boolean) {
  showLoadingToast({ message: force ? '重新生成…' : '生成中…', forbidClick: true, duration: 0 })
  try {
    report.value = await generateReport(kind.value, period.value, force)
    showSuccessToast('已更新')
  } catch {
    showFailToast('生成失败，旧报告仍保留')
    await load()
  } finally {
    closeToast()
  }
}

watch(kind, () => {
  if (kind.value === 'weekly') {
    period.value = mondayOf(period.value)
  }
  void load()
})

onMounted(() => {
  const qKind = route.query.kind
  if (qKind === 'weekly' || qKind === 'daily') kind.value = qKind
  const qPeriod = route.query.period
  if (typeof qPeriod === 'string' && qPeriod.length >= 8) period.value = qPeriod
  void load()
})

function goBack() {
  router.back()
}
</script>

<template>
  <div class="report-page">
    <van-nav-bar :title="title" left-arrow @click-left="goBack" />

    <van-tabs v-model:active="kind">
      <van-tab title="日报告" name="daily" />
      <van-tab title="周报" name="weekly" />
    </van-tabs>

    <div class="report-page__toolbar fit-card">
      <label class="report-page__date">
        <span>日期</span>
        <input v-model="period" type="date" />
      </label>
      <div class="report-page__actions">
        <van-button size="small" type="primary" :loading="loading" @click="onGenerate(false)">
          生成
        </van-button>
        <van-button size="small" plain type="primary" @click="onGenerate(true)">重新生成</van-button>
      </div>
    </div>

    <article v-if="report" class="report-page__body fit-card">
      <p class="report-page__meta">{{ report.period_key }} · {{ report.created_at.slice(0, 16) }}</p>
      <pre class="report-page__md">{{ report.content_md }}</pre>
    </article>
    <van-empty v-else-if="!loading" description="暂无报告，点生成" />
  </div>
</template>

<style scoped>
.report-page {
  min-height: 100vh;
  padding-bottom: 24px;
}

.report-page__toolbar {
  margin: 12px 16px;
  padding: 14px 16px;
}

.report-page__date {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  font-weight: 700;
  margin-bottom: 12px;
}

.report-page__date input {
  flex: 1;
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 8px 10px;
  font: inherit;
}

.report-page__actions {
  display: flex;
  gap: 10px;
}

.report-page__body {
  margin: 0 16px;
  padding: 16px;
}

.report-page__meta {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.report-page__md {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.55;
}
</style>
