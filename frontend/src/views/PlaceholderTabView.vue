<script setup lang="ts">
defineProps<{
  phase: string
  title: string
}>()
</script>

<template>
  <div class="ph">
    <div class="ph__card fit-card">
      <p class="fit-section-label">Coming Soon</p>
      <h1>{{ title }}</h1>
      <p class="ph__phase">{{ phase }} 敬请期待</p>
    </div>
  </div>
</template>

<style scoped>
.ph {
  min-height: 70vh;
  display: grid;
  place-items: center;
  padding: 24px 16px;
}

.ph__card {
  width: 100%;
  max-width: 360px;
  padding: 36px 24px;
  text-align: center;
}

.ph__card h1 {
  margin: 0;
  font-size: 1.75rem;
  font-weight: 800;
}

.ph__phase {
  margin: 12px 0 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--muted);
}
</style>
