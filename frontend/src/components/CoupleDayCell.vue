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
    <div class="couple-day__half" :class="levelClass(dragon.level)" />
    <div class="couple-day__half couple-day__half--bottom" :class="levelClass(leaf.level)" />
  </div>
</template>

<style scoped>
.couple-day {
  --level-full: #3d8b6e;
  --level-partial: #d4a017;
  --level-none: #e8e4de;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 36px;
  border-radius: 6px;
  overflow: hidden;
}

.couple-day__half {
  flex: 1;
}

.couple-day__half--bottom {
  border-top: 1px solid rgba(0, 0, 0, 0.06);
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
