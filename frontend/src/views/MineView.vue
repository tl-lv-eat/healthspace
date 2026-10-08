<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast } from 'vant'
import { PERSONAS, otherPersona } from '@/constants/personas'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const switching = ref(false)

const partner = computed(() => otherPersona(auth.user?.id))
const mePersona = computed(() => PERSONAS.find((p) => p.id === auth.user?.id))

async function switchToPartner() {
  if (!partner.value || switching.value) return
  switching.value = true
  showLoadingToast({ message: '切换中…', forbidClick: true, duration: 0 })
  try {
    await auth.select(partner.value.id)
    closeToast()
    await router.replace(router.currentRoute.value.fullPath)
  } catch {
    closeToast()
    showFailToast('切换失败')
  } finally {
    switching.value = false
  }
}

function backToPick() {
  auth.clearSession()
  void router.push({ name: 'login' })
}
</script>

<template>
  <div class="mine">
    <header class="mine__hero fit-card">
      <p class="fit-section-label">当前身份</p>
      <h1>{{ auth.user?.display_name ?? '—' }}</h1>
      <p class="mine__id">{{ mePersona?.emoji }}</p>
      <button
        type="button"
        class="mine__switch"
        :disabled="switching"
        @click="switchToPartner"
      >
        切换为 {{ partner.emoji }} {{ partner.label }}
      </button>
    </header>

    <router-link to="/settings" class="mine__link fit-card">设置</router-link>
    <router-link to="/achievements" class="mine__link fit-card">成就</router-link>
    <router-link to="/body" class="mine__link fit-card">身体数据与趋势</router-link>
    <router-link to="/report" class="mine__link fit-card">AI 报告</router-link>
    <router-link to="/chat" class="mine__link fit-card">智能聊天</router-link>
    <router-link to="/push" class="mine__link fit-card">推送设置（PushPlus）</router-link>

    <button type="button" class="mine__logout" @click="backToPick">重新选人</button>
  </div>
</template>

<style scoped>
.mine {
  padding: 12px 16px 32px;
}

.mine__hero {
  padding: 28px 22px;
  margin-bottom: 20px;
  background:
    linear-gradient(145deg, var(--primary-soft), #fff 55%),
    var(--card);
}

.mine__hero h1 {
  margin: 0;
  font-size: 2rem;
  font-weight: 800;
}

.mine__id {
  margin: 8px 0 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--muted);
}

.mine__switch {
  margin-top: 18px;
  width: 100%;
  height: 44px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: #fff;
  font-weight: 800;
  cursor: pointer;
}

.mine__switch:disabled {
  opacity: 0.6;
}

.mine__link {
  display: block;
  padding: 16px 20px;
  margin-bottom: 16px;
  font-weight: 800;
  text-decoration: none;
  color: inherit;
}

.mine__logout {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 14px;
  background: var(--card);
  box-shadow: var(--shadow-sm);
  font-weight: 800;
  color: var(--muted);
  cursor: pointer;
}
</style>
