<script setup lang="ts">
import { RouterView } from 'vue-router'
import PersonaSwitcher from '@/components/PersonaSwitcher.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div class="tab-layout">
    <header class="tab-layout__bar">
      <span class="tab-layout__brand">健康space🐉🍃</span>
      <PersonaSwitcher />
    </header>
    <main class="tab-layout__main">
      <RouterView :key="auth.user?.id ?? 'guest'" />
    </main>
    <van-tabbar route placeholder safe-area-inset-bottom>
      <van-tabbar-item replace to="/today" icon="home-o">今日</van-tabbar-item>
      <van-tabbar-item replace to="/calendar" icon="calendar-o">日历</van-tabbar-item>
      <van-tabbar-item replace to="/goals" icon="flag-o">目标</van-tabbar-item>
      <van-tabbar-item replace to="/mine" icon="user-o">我的</van-tabbar-item>
    </van-tabbar>
  </div>
</template>

<style scoped>
.tab-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.tab-layout__bar {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  padding-top: calc(10px + env(safe-area-inset-top, 0px));
  background: color-mix(in srgb, var(--bg) 88%, transparent);
  backdrop-filter: blur(10px);
}

.tab-layout__brand {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: 0.02em;
}

.tab-layout__main {
  flex: 1;
  padding-bottom: calc(50px + env(safe-area-inset-bottom, 0px));
  overflow-y: auto;
}
</style>
