<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showFailToast, showLoadingToast, closeToast } from 'vant'
import { useAuthStore } from '@/stores/auth'

const USERS = [
  { id: 'dragon', emoji: '🐉', label: 'Dragon', hint: '男方' },
  { id: 'leaf', emoji: '🍃', label: 'Leaf', hint: '女方' },
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
  <div class="login">
    <div class="login__hero">
      <p class="login__eyebrow">COUPLE FITNESS</p>
      <h1 class="login__brand">双人减</h1>
      <p class="login__tagline">饮食 · 饮水 · 训练，和 TA 一起推进</p>
    </div>

    <div class="login__pick">
      <button
        v-for="u in USERS"
        :key="u.id"
        type="button"
        class="persona"
        :class="{ 'persona--on': selectedId === u.id, [`persona--${u.id}`]: true }"
        @click="selectedId = u.id"
      >
        <span class="persona__emoji">{{ u.emoji }}</span>
        <span class="persona__label">{{ u.label }}</span>
        <span class="persona__hint">{{ u.hint }}</span>
      </button>
    </div>

    <div class="login__sheet fit-card">
      <label class="login__field-label">密码</label>
      <van-field
        v-model="password"
        type="password"
        placeholder="输入密码进入"
        autocomplete="current-password"
        class="login__field"
        @keyup.enter="onSubmit"
      />
      <van-button
        type="primary"
        block
        class="login__cta"
        :loading="loading"
        @click="onSubmit"
      >
        Start Today
      </van-button>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  padding: 56px 22px 32px;
  display: flex;
  flex-direction: column;
}

.login__hero {
  margin-bottom: 36px;
}

.login__eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
  color: var(--primary-dark);
}

.login__brand {
  margin: 0;
  font-size: clamp(2.6rem, 12vw, 3.4rem);
  font-weight: 800;
  line-height: 1;
  color: var(--ink);
}

.login__tagline {
  margin: 14px 0 0;
  font-size: 15px;
  color: var(--muted);
  font-weight: 500;
  max-width: 16em;
}

.login__pick {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 20px;
}

.persona {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-height: 132px;
  padding: 18px 16px;
  border: 2px solid transparent;
  border-radius: var(--radius);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  text-align: left;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.persona--on {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.persona--dragon.persona--on {
  border-color: #ff8787;
  background: linear-gradient(160deg, #fff 40%, var(--cal-soft));
}

.persona--leaf.persona--on {
  border-color: var(--primary);
  background: linear-gradient(160deg, #fff 40%, var(--primary-soft));
}

.persona__emoji {
  font-size: 2.2rem;
  line-height: 1;
  margin-bottom: 8px;
}

.persona__label {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 700;
}

.persona__hint {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.login__sheet {
  padding: 20px 18px 18px;
  margin-top: auto;
}

.login__field-label {
  display: block;
  margin-bottom: 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--muted);
}

.login__field {
  margin-bottom: 16px;
  padding: 4px 12px;
  background: var(--bg);
  border-radius: 14px;
}

.login__field :deep(.van-cell) {
  background: transparent;
  padding: 8px 0;
}

.login__cta {
  height: 48px !important;
  font-weight: 800 !important;
  letter-spacing: 0.02em;
  border-radius: 14px !important;
}
</style>
