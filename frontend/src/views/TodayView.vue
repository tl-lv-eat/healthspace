<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="today-shell">
    <van-nav-bar :title="`今日 · ${auth.user?.display_name ?? ''}`" fixed placeholder />
    <main class="today-body">
      <van-empty description="今日页开发中" />
    </main>
  </div>
</template>

<style scoped>
.today-body {
  padding: 24px 16px;
}
</style>
