<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="tab-layout">
    <main class="tab-layout__main">
      <RouterView />
    </main>
    <van-tabbar route placeholder safe-area-inset-bottom>
      <van-tabbar-item replace to="/today" icon="home-o">今日</van-tabbar-item>
      <van-tabbar-item replace to="/calendar" icon="calendar-o">日历</van-tabbar-item>
      <van-tabbar-item replace to="/journal" icon="notes-o">日志</van-tabbar-item>
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
  background: var(--page-bg, #f7f8fa);
}

.tab-layout__main {
  flex: 1;
  padding-bottom: calc(50px + env(safe-area-inset-bottom, 0px));
  overflow-y: auto;
}
</style>
