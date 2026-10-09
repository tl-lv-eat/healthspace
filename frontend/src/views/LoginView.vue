<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { showFailToast, showLoadingToast, closeToast } from 'vant'
import { PERSONAS, type PersonaId } from '@/constants/personas'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const loading = ref(false)

async function pick(id: PersonaId) {
  if (loading.value) return
  loading.value = true
  showLoadingToast({ message: '进入中…', forbidClick: true, duration: 0 })
  try {
    await auth.select(id)
    closeToast()
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/today'
    await router.replace(redirect)
  } catch {
    closeToast()
    showFailToast('进入失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login">
    <div class="login__hero">
      <p class="login__eyebrow">龙龙 × 孙孙</p>
      <h1 class="login__brand">健康space🐉🍃</h1>
      <p class="login__tagline">选一下现在是谁在记</p>
    </div>

    <div class="login__pick">
      <button
        v-for="u in PERSONAS"
        :key="u.id"
        type="button"
        class="persona"
        :class="[`persona--${u.id}`]"
        :disabled="loading"
        @click="pick(u.id)"
      >
        <span class="persona__emoji">{{ u.emoji }}</span>
        <span class="persona__label">{{ u.label }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100vh;
  padding: 56px 22px 40px;
  display: flex;
  flex-direction: column;
}

.login__hero {
  margin-bottom: 40px;
}

.login__eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.12em;
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
}

.login__pick {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}

.persona {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  min-height: 160px;
  padding: 22px 18px;
  border: 2px solid transparent;
  border-radius: var(--radius);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  text-align: left;
  font: inherit;
  transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.persona:disabled {
  opacity: 0.7;
  cursor: wait;
}

.persona:active:not(:disabled) {
  transform: scale(0.98);
}

.persona--dragon {
  border-color: rgba(232, 196, 138, 0.45);
  background: linear-gradient(160deg, #1a1c22 20%, #12141a);
  color: #f3efe8;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.35);
}

.persona--leaf {
  border-color: rgba(232, 93, 142, 0.4);
  background: linear-gradient(160deg, #fff 30%, #fce4ee);
  color: #2a1820;
  box-shadow: 0 14px 36px rgba(200, 80, 120, 0.12);
}

.persona__emoji {
  font-size: 2.4rem;
  line-height: 1;
  margin-bottom: 10px;
}

.persona__label {
  font-size: 1.2rem;
  font-weight: 800;
}
</style>
