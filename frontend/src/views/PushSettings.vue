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

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="push">
    <header class="push-hero">
      <div class="push-hero__glow" aria-hidden="true" />
      <button type="button" class="push-back" @click="router.back()">← 返回</button>
      <p class="fit-section-label">Notify</p>
      <h1>推送提醒</h1>
      <p class="push-hero__hint">PushPlus 绑定微信 · 按时段提醒</p>
    </header>

    <section v-if="settings" class="push-block">
      <div class="push-block__head">
        <p class="fit-section-label">Token</p>
        <h2>账号绑定</h2>
      </div>
      <label class="push-field">
        <span>PushPlus Token</span>
        <input v-model="settings.token" placeholder="粘贴 token" />
      </label>
      <div class="push-toggle">
        <div>
          <strong>启用提醒</strong>
          <p>关闭后不再推送</p>
        </div>
        <van-switch v-model="settings.enabled" size="22px" />
      </div>
    </section>

    <section v-if="settings" class="push-block">
      <div class="push-block__head">
        <p class="fit-section-label">Hours</p>
        <h2>提醒时段</h2>
        <p class="push-block__hint">点选小时 · 已选 {{ settings.remind_hours.length }} 个</p>
      </div>
      <div class="push-hours">
        <button
          v-for="h in hourOptions"
          :key="h"
          type="button"
          class="push-hour"
          :class="{ 'push-hour--on': settings.remind_hours.includes(h) }"
          @click="toggleHour(h)"
        >
          {{ h }}
        </button>
      </div>
    </section>

    <section v-if="settings && (settings.last_error || settings.last_success_at)" class="push-block push-block--meta">
      <p v-if="settings.last_success_at">
        <span>最近成功</span>
        <strong>{{ settings.last_success_at }}</strong>
      </p>
      <p v-if="settings.last_error" class="push-err">
        <span>最近错误</span>
        <strong>{{ settings.last_error }}</strong>
      </p>
    </section>

    <div v-if="settings" class="push-actions">
      <button type="button" class="push-btn push-btn--primary" @click="save">保存</button>
      <button type="button" class="push-btn" @click="onTest">发送测试</button>
      <p class="push-hint">
        在
        <a href="https://www.pushplus.plus/" target="_blank" rel="noopener">PushPlus</a>
        获取 token，绑定微信接收提醒。
      </p>
    </div>
  </div>
</template>

<style scoped>
.push {
  padding: 12px 14px 40px;
}

.push-hero {
  position: relative;
  overflow: hidden;
  padding: 14px 18px 20px;
  margin-bottom: 16px;
  border-radius: 28px;
  border: 1px solid var(--line);
  background:
    linear-gradient(155deg, color-mix(in srgb, var(--water) 14%, var(--card)), var(--card) 55%);
  box-shadow: var(--shadow);
  animation: push-in 0.45s ease both;
}

.push-hero__glow {
  position: absolute;
  width: 180px;
  height: 180px;
  right: -40px;
  top: -50px;
  border-radius: 50%;
  background: radial-gradient(circle, color-mix(in srgb, var(--water) 30%, transparent), transparent 70%);
  pointer-events: none;
}

.push-back {
  position: relative;
  border: none;
  background: transparent;
  padding: 0;
  margin-bottom: 10px;
  font: inherit;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
}

.push-hero h1 {
  position: relative;
  margin: 0;
  font-size: 1.7rem;
  font-weight: 800;
}

.push-hero__hint {
  position: relative;
  margin: 6px 0 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--muted);
}

.push-block {
  padding: 16px;
  margin-bottom: 12px;
  border-radius: 20px;
  background: var(--card);
  border: 1px solid var(--line);
  box-shadow: var(--shadow-sm);
}

.push-block__head .fit-section-label {
  margin-bottom: 4px;
}

.push-block__head h2 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
}

.push-block__hint {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.push-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  font-size: 12px;
  font-weight: 800;
  color: var(--muted);
}

.push-field input {
  height: 44px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: color-mix(in srgb, var(--bg) 75%, var(--card));
  color: var(--ink);
  font: inherit;
  font-weight: 700;
}

.push-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  background: color-mix(in srgb, var(--bg) 60%, var(--card));
  border: 1px solid var(--line);
}

.push-toggle strong {
  display: block;
  font-size: 14px;
  font-weight: 800;
}

.push-toggle p {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.push-hours {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 8px;
  margin-top: 12px;
}

.push-hour {
  height: 36px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: color-mix(in srgb, var(--bg) 70%, var(--card));
  color: var(--muted);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}

.push-hour--on {
  background: var(--primary);
  border-color: transparent;
  color: var(--on-primary, #fff);
}

.push-block--meta p {
  margin: 0 0 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.push-block--meta p:last-child {
  margin-bottom: 0;
}

.push-block--meta strong {
  color: var(--ink);
  font-weight: 700;
  word-break: break-all;
}

.push-err strong {
  color: var(--cal);
}

.push-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
}

.push-btn {
  height: 46px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: var(--card);
  color: var(--ink);
  font-weight: 800;
  font-size: 14px;
  cursor: pointer;
}

.push-btn--primary {
  background: var(--primary);
  border-color: transparent;
  color: var(--on-primary, #fff);
}

.push-hint {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.45;
  font-weight: 600;
}

.push-hint a {
  color: var(--primary-dark);
  font-weight: 800;
}

@keyframes push-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
</style>
