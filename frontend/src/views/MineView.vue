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
  <div class="mine-view">
    <van-cell-group inset>
      <van-cell title="账号" :value="auth.user?.id ?? '—'" />
      <van-cell title="展示名" :value="auth.user?.display_name ?? '—'" />
    </van-cell-group>
    <div class="mine-view__actions">
      <van-button block type="default" @click="logout">退出登录</van-button>
    </div>
  </div>
</template>

<style scoped>
.mine-view {
  padding: 16px 0;
}

.mine-view__actions {
  margin: 24px 16px;
}
</style>
