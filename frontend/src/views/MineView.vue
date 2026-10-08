<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

function logout() {
  auth.clearSession()
  void router.push({ name: 'login' })
}
</script>

<template>
  <div class="mine">
    <header class="mine__hero fit-card">
      <p class="fit-section-label">Profile</p>
      <h1>{{ auth.user?.display_name ?? '—' }}</h1>
      <p class="mine__id">@{{ auth.user?.id ?? '—' }}</p>
    </header>

    <button type="button" class="mine__logout" @click="logout">退出登录</button>
  </div>
</template>

<style scoped>
.mine {
  padding: 20px 16px 32px;
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

.mine__logout {
  width: 100%;
  height: 48px;
  border: none;
  border-radius: 14px;
  background: var(--card);
  box-shadow: var(--shadow-sm);
  font-weight: 800;
  color: var(--cal);
  cursor: pointer;
}
</style>
