<script setup lang="ts">
import type { Goal } from '@/api/goals'

const props = defineProps<{
  goal: Goal
  mine: boolean
}>()

const emit = defineEmits<{ (e: 'refresh', id: number): void }>()

const progressPct = () => {
  if (props.goal.target_value <= 0) return 0
  const p = (props.goal.current_value / props.goal.target_value) * 100
  return Math.min(100, Math.round(p))
}
</script>

<template>
  <van-cell-group inset class="goal-card">
    <van-cell :title="goal.title" :label="`${goal.user_id} · ${goal.kind === 'short' ? '短期' : '长期'}`">
      <template #value>
        <van-tag v-if="goal.status === 'done'" type="success">完成</van-tag>
        <van-tag v-else-if="goal.status === 'cancelled'" type="default">取消</van-tag>
        <van-tag v-else type="primary">进行中</van-tag>
      </template>
    </van-cell>
    <van-cell title="进度">
      <template #label>
        {{ goal.current_value }}{{ goal.unit ? ' ' + goal.unit : '' }} / {{ goal.target_value
        }}{{ goal.unit ? ' ' + goal.unit : '' }}
      </template>
      <van-progress :percentage="progressPct()" stroke-width="6" />
    </van-cell>
    <van-cell v-if="mine && goal.status === 'active' && goal.metric !== 'custom'">
      <van-button size="small" type="primary" plain block @click="emit('refresh', goal.id)">刷新进度</van-button>
    </van-cell>
  </van-cell-group>
</template>

<style scoped>
.goal-card {
  margin-bottom: 12px;
}
</style>
