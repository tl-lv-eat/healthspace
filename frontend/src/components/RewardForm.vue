<script setup lang="ts">
import { ref } from 'vue'
import { showSuccessToast, showFailToast } from 'vant'
import { createReward } from '@/api/rewards'

const emit = defineEmits<{ (e: 'created'): void }>()

const show = ref(false)
const title = ref('')
const description = ref('')
const pointsPrice = ref(30)
const scaleLevel = ref(3)
const costNote = ref('')
const isPrivate = ref(false)
const submitting = ref(false)

function open() {
  show.value = true
}

async function submit() {
  if (!title.value.trim()) {
    showFailToast('请填写标题')
    return
  }
  if (pointsPrice.value <= 0) {
    showFailToast('积分价须大于 0')
    return
  }
  submitting.value = true
  try {
    await createReward({
      title: title.value.trim(),
      description: description.value,
      is_private: isPrivate.value,
      scale_level: scaleLevel.value,
      cost_note: costNote.value,
      points_price: pointsPrice.value,
    })
    showSuccessToast('已添加奖励')
    show.value = false
    title.value = ''
    description.value = ''
    emit('created')
  } catch {
    showFailToast('创建失败')
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<template>
  <van-popup v-model:show="show" position="bottom" round :style="{ maxHeight: '85vh' }">
    <div class="reward-form">
      <h3>新建奖励</h3>
      <van-field v-model="title" label="标题" placeholder="例如：火锅 night" />
      <van-field v-model="description" rows="2" autosize type="textarea" label="说明" />
      <van-field v-model.number="pointsPrice" type="digit" label="积分价" />
      <van-field v-model.number="scaleLevel" type="digit" label="尺度 1-5" />
      <van-field v-model="costNote" label="花费感" placeholder="约200元" />
      <van-cell title="私密奖励">
        <template #right-icon>
          <van-switch v-model="isPrivate" size="20" />
        </template>
      </van-cell>
      <van-button type="primary" block :loading="submitting" @click="submit">保存</van-button>
    </div>
  </van-popup>
</template>

<style scoped>
.reward-form {
  padding: 20px 16px 32px;
}

.reward-form h3 {
  margin: 0 0 12px;
  text-align: center;
}
</style>
