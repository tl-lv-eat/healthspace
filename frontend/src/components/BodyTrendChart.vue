<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import type { TrendSeries } from '@/api/body'

echarts.use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const props = defineProps<{
  series: TrendSeries[]
}>()

const el = ref<HTMLElement | null>(null)
let chart: echarts.ECharts | null = null

const LABELS: Record<string, string> = {
  dragon: '🐉',
  leaf: '🍃',
}

function render() {
  if (!el.value) return
  if (!chart) chart = echarts.init(el.value)

  const allDates = new Set<string>()
  for (const s of props.series) {
    for (const p of s.points) allDates.add(p.date)
  }
  const dates = [...allDates].sort()

  const eSeries = props.series.map((s) => {
    const byDate = new Map(s.points.map((p) => [p.date, p.weight_kg]))
    return {
      name: LABELS[s.user_id] ?? s.user_id,
      type: 'line' as const,
      connectNulls: true,
      data: dates.map((d) => byDate.get(d) ?? null),
    }
  })

  chart.setOption({
    legend: { data: eSeries.map((s) => s.name) },
    tooltip: { trigger: 'axis' },
    grid: { left: 48, right: 16, top: 40, bottom: 32 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', name: 'kg' },
    series: eSeries,
  })
}

watch(() => props.series, () => render(), { deep: true })

onMounted(() => {
  render()
  window.addEventListener('resize', () => chart?.resize())
})

onBeforeUnmount(() => {
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="el" class="body-trend-chart" />
</template>

<style scoped>
.body-trend-chart {
  width: 100%;
  height: 260px;
}
</style>
