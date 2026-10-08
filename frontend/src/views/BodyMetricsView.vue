<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { showFailToast, showSuccessToast } from 'vant'
import BodyTrendChart from '@/components/BodyTrendChart.vue'
import { createBodyMetric, fetchBodyTrend, type TrendSeries } from '@/api/body'
import { formatDateLocal } from '@/api/today'

const recordedOn = ref(formatDateLocal())
const weightKg = ref<number | ''>('')
const heightCm = ref<number | ''>('')
const waistCm = ref<number | ''>('')
const bodyFat = ref<number | ''>('')
const chestCm = ref<number | ''>('')
const hipCm = ref<number | ''>('')
const note = ref('')
const series = ref<TrendSeries[]>([])
const submitting = ref(false)

async function reloadTrend() {
  try {
    series.value = await fetchBodyTrend(['dragon', 'leaf'])
  } catch {
    showFailToast('加载趋势失败')
  }
}

async function submit() {
  if (weightKg.value === '' || heightCm.value === '') {
    showFailToast('请填写体重与身高')
    return
  }
  submitting.value = true
  try {
    await createBodyMetric({
      recorded_on: recordedOn.value,
      weight_kg: Number(weightKg.value),
      height_cm: Number(heightCm.value),
      waist_cm: waistCm.value === '' ? null : Number(waistCm.value),
      body_fat_pct: bodyFat.value === '' ? null : Number(bodyFat.value),
      chest_cm: chestCm.value === '' ? null : Number(chestCm.value),
      hip_cm: hipCm.value === '' ? null : Number(hipCm.value),
      note: note.value,
    })
    showSuccessToast('已记录')
    note.value = ''
    await reloadTrend()
  } catch {
    showFailToast('提交失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  void reloadTrend()
})
</script>

<template>
  <div class="body-page">
    <header class="body-page__hero fit-card">
      <p class="fit-section-label">Body</p>
      <h1>身体周记</h1>
    </header>

    <section class="fit-card body-page__chart">
      <BodyTrendChart :series="series" />
    </section>

    <section class="fit-card body-page__form">
      <van-field v-model="recordedOn" label="日期" />
      <van-field v-model="weightKg" type="number" label="体重 kg" />
      <van-field v-model="heightCm" type="number" label="身高 cm" />
      <van-field v-model="waistCm" type="number" label="腰围 cm" />
      <van-field v-model="bodyFat" type="number" label="体脂 %" />
      <van-field v-model="chestCm" type="number" label="胸围 cm" />
      <van-field v-model="hipCm" type="number" label="臀围 cm" />
      <van-field v-model="note" label="备注" />
      <van-button block type="primary" :loading="submitting" @click="submit">保存记录</van-button>
    </section>
  </div>
</template>

<style scoped>
.body-page {
  padding: 20px 16px 32px;
}

.body-page__hero {
  padding: 24px 20px;
  margin-bottom: 16px;
}

.body-page__hero h1 {
  margin: 0;
  font-size: 1.5rem;
}

.body-page__chart,
.body-page__form {
  padding: 16px;
  margin-bottom: 16px;
}
</style>
