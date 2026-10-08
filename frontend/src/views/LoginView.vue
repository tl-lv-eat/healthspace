<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showFailToast, showLoadingToast, closeToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

const USERS = [
  { id: 'dragon', emoji: '🐉', label: '龙' },
  { id: 'leaf', emoji: '🍃', label: '叶' },
] as const

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const selectedId = ref<(typeof USERS)[number]['id'] | null>(null)
const password = ref('')
const loading = ref(false)

async function onSubmit() {
  if (!selectedId.value) {
    showFailToast('请选择账号')
    return
  }
  if (!password.value) {
    showFailToast('请输入密码')
    return
  }
  loading.value = true
  showLoadingToast({ message: '登录中…', forbidClick: true, duration: 0 })
  try {
    await auth.login(selectedId.value, password.value)
    closeToast()
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/today'
    await router.replace(redirect)
  } catch {
    closeToast()
    showFailToast('密码错误或网络异常')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <header class="login-header">
      <h1>双人减</h1>
      <p>选择身份并输入密码</p>
    </header>

    <div class="user-cards">
      <button
        v-for="u in USERS"
        :key="u.id"
        type="button"
        class="user-card"
        :class="{ active: selectedId === u.id }"
        @click="selectedId = u.id"
      >
        <span class="emoji">{{ u.emoji }}</span>
        <span class="name">{{ u.label }}</span>
      </button>
    </div>

    <van-cell-group inset class="form">
      <van-field
        v-model="password"
        type="password"
        label="密码"
        placeholder="请输入密码"
        autocomplete="current-password"
        @keyup.enter="onSubmit"
      />
    </van-cell-group>

    <div class="actions">
      <van-button type="primary" block round :loading="loading" @click="onSubmit">
        进入
      </van-button>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  padding: 48px 16px 24px;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header h1 {
  margin: 0 0 8px;
  font-size: 1.75rem;
  font-weight: 600;
}

.login-header p {
  margin: 0;
  color: #969799;
  font-size: 14px;
}

.user-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 24px;
}

.user-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 120px;
  padding: 16px;
  border: 2px solid #ebedf0;
  border-radius: 12px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.user-card.active {
  border-color: #1989fa;
  box-shadow: 0 4px 12px rgba(25, 137, 250, 0.15);
}

.user-card .emoji {
  font-size: 2.5rem;
  line-height: 1;
}

.user-card .name {
  font-size: 15px;
  color: #323233;
}

.form {
  margin-bottom: 24px;
}

.actions {
  padding: 0 4px;
}
</style>
