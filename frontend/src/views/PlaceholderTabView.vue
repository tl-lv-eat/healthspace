<script setup lang="ts">
defineProps<{
  phase: string
  title: string
}>()
</script>

<template>
  <div class="placeholder-tab">
    <van-empty>
      <p class="placeholder-tab__title">{{ title }}</p>
      <p class="placeholder-tab__phase">{{ phase }} 敬请期待</p>
    </van-empty>
  </div>
</template>

<style scoped>
.placeholder-tab {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
}

.placeholder-tab__title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #323233;
}

.placeholder-tab__phase {
  margin: 0;
  font-size: 14px;
  color: #969799;
}
</style>
