<script setup lang="ts">
import { ref } from 'vue'
import { showSuccessToast, showFailToast } from 'vant'
import {
  createReward,
  patchReward,
  type Reward,
  type RewardCategory,
  REWARD_CATEGORY_OPTIONS,
} from '@/api/rewards'

const emit = defineEmits<{ (e: 'saved'): void }>()

const show = ref(false)
const editingId = ref<number | null>(null)
const title = ref('')
const description = ref('')
const pointsPrice = ref(30)
const scaleLevel = ref(3)
const costNote = ref('')
const isPrivate = ref(false)
const category = ref<RewardCategory>('food')
const submitting = ref(false)

function resetFields() {
  editingId.value = null
  title.value = ''
  description.value = ''
  pointsPrice.value = 30
  scaleLevel.value = 3
  costNote.value = ''
  isPrivate.value = false
  category.value = 'food'
}

function open(reward?: Reward) {
  resetFields()
  if (reward) {
    editingId.value = reward.id
    title.value = reward.title
    description.value = reward.description ?? ''
    pointsPrice.value = reward.points_price
    scaleLevel.value = reward.scale_level
    costNote.value = reward.cost_note
    isPrivate.value = reward.is_private
    category.value = reward.category
  }
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
    const payload = {
      title: title.value.trim(),
      description: description.value,
      is_private: isPrivate.value,
      scale_level: scaleLevel.value,
      cost_note: costNote.value,
      points_price: pointsPrice.value,
      category: category.value,
    }
    if (editingId.value != null) {
      await patchReward(editingId.value, payload)
      showSuccessToast('已保存')
    } else {
      await createReward(payload)
      showSuccessToast('已提交审核')
    }
    show.value = false
    resetFields()
    emit('saved')
  } catch {
    showFailToast(editingId.value != null ? '保存失败' : '提交失败')
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<template>
  <van-popup v-model:show="show" position="bottom" round :style="{ maxHeight: '85vh' }">
    <div class="reward-form">
      <h3>{{ editingId != null ? '编辑奖励' : '新建奖励' }}</h3>
      <van-field v-model="title" label="标题" placeholder="例如：火锅 night" />
      <van-field label="分类">
        <template #input>
          <van-radio-group v-model="category" direction="horizontal" class="reward-form__cats">
            <van-radio v-for="opt in REWARD_CATEGORY_OPTIONS" :key="opt.value" :name="opt.value">
              {{ opt.label }}
            </van-radio>
          </van-radio-group>
        </template>
      </van-field>
      <van-field v-model="description" rows="2" autosize type="textarea" label="说明" />
      <van-field v-model.number="pointsPrice" type="digit" label="积分价" />
      <van-field v-model.number="scaleLevel" type="digit" label="尺度 1-5" />
      <van-field v-model="costNote" label="花费感" placeholder="约200元" />
      <van-cell title="私密奖励">
        <template #right-icon>
          <van-switch v-model="isPrivate" size="20" />
        </template>
      </van-cell>
      <p v-if="editingId == null" class="reward-form__hint">创建后将进入待对方审核，通过后上架。</p>
      <van-button type="primary" block :loading="submitting" @click="submit">
        {{ editingId != null ? '保存' : '提交审核' }}
      </van-button>
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

.reward-form__cats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 12px;
}

.reward-form__hint {
  margin: 8px 0 12px;
  font-size: 12px;
  opacity: 0.65;
  text-align: center;
}
</style>
