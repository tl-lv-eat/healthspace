<script setup lang="ts">
import type { DayStatus } from '@/api/calendar'

defineProps<{
  dragon: DayStatus
  leaf: DayStatus
}>()

function levelClass(level: string) {
  return `level-${level}`
}
</script>

<template>
  <div class="couple-day">
    <div class="couple-day__half" :class="levelClass(dragon.level)" title="龙龙" />
    <div class="couple-day__half couple-day__half--bottom" :class="levelClass(leaf.level)" title="孙孙" />
  </div>
</template>

<style scoped>
.couple-day {
  --level-full: #2f9e6b;
  --level-partial: #e6a23c;
  --level-none: color-mix(in srgb, var(--line) 80%, #c9c4bc);
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 36px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid color-mix(in srgb, var(--line) 70%, transparent);
}

.couple-day__half {
  flex: 1;
}

.couple-day__half--bottom {
  border-top: 1px solid rgba(0, 0, 0, 0.08);
}

.level-full {
  background: var(--level-full);
}

.level-partial {
  background: var(--level-partial);
}

.level-none {
  background: var(--level-none);
}
</style>
