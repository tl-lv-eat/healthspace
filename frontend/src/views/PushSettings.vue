<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast, showSuccessToast } from 'vant'
import { fetchPushSettings, savePushSettings, testPush, type PushSettings } from '@/api/push'

const router = useRouter()
const settings = ref<PushSettings | null>(null)
const hourOptions = Array.from({ length: 24 }, (_, i) => i)

async function load() {
  try {
    settings.value = await fetchPushSettings()
  } catch {
    showFailToast('加载推送设置失败')
  }
}

async function save() {
  if (!settings.value) return
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    settings.value = await savePushSettings({
      token: settings.value.token,
      enabled: settings.value.enabled,
      remind_hours: settings.value.remind_hours,
    })
    showSuccessToast('已保存')
  } catch {
    showFailToast('保存失败')
  } finally {
    closeToast()
  }
}

async function onTest() {
  showLoadingToast({ message: '发送测试…', forbidClick: true, duration: 0 })
  try {
    await testPush()
    showSuccessToast('已发送')
    await load()
  } catch {
    showFailToast('测试失败')
    await load()
  } finally {
    closeToast()
  }
}

function toggleHour(h: number) {
  if (!settings.value) return
  const set = new Set(settings.value.remind_hours)
  if (set.has(h)) set.delete(h)
  else set.add(h)
  settings.value.remind_hours = [...set].sort((a, b) => a - b)
}

function goBack() {
  router.back()
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="push-page">
    <van-nav-bar title="推送设置" left-arrow @click-left="goBack" />

    <van-cell-group v-if="settings" inset class="push-page__group">
      <van-field v-model="settings.token" label="Token" placeholder="PushPlus token" />
      <van-cell title="启用提醒">
        <template #right-icon>
          <van-switch v-model="settings.enabled" size="20px" />
        </template>
      </van-cell>
      <van-cell title="提醒时段（点选小时）">
        <template #label>
          <div class="push-page__hours">
            <button
              v-for="h in hourOptions"
              :key="h"
              type="button"
              class="push-page__hour"
              :class="{ on: settings.remind_hours.includes(h) }"
              @click="toggleHour(h)"
            >
              {{ h }}
            </button>
          </div>
        </template>
      </van-cell>
      <van-cell v-if="settings.last_error" title="最近错误" :label="settings.last_error" />
      <van-cell
        v-if="settings.last_success_at"
        title="最近成功"
        :label="settings.last_success_at"
      />
    </van-cell-group>

    <div v-if="settings" class="push-page__actions">
      <van-button block type="primary" @click="save">保存</van-button>
      <van-button block plain type="primary" @click="onTest">发送测试</van-button>
      <p class="push-page__hint">
        在
        <a href="https://www.pushplus.plus/" target="_blank" rel="noopener">PushPlus</a>
        获取 token，绑定微信接收提醒。
      </p>
    </div>
  </div>
</template>

<style scoped>
.push-page {
  min-height: 100vh;
  padding-bottom: 24px;
}

.push-page__group {
  margin-top: 12px;
}

.push-page__hours {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.push-page__hour {
  width: 36px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--bg);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.push-page__hour.on {
  background: var(--primary-soft);
  border-color: var(--primary);
  color: var(--primary-dark);
}

.push-page__actions {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.push-page__hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.4;
}

.push-page__hint a {
  color: var(--primary);
}
</style>
