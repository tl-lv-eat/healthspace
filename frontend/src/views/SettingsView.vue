<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showSuccessToast, showLoadingToast } from 'vant'
import { personaById } from '@/constants/personas'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const name = ref(auth.user?.display_name ?? '')
const sex = ref<'male' | 'female' | ''>(
  auth.user?.sex === 'male' || auth.user?.sex === 'female' ? auth.user.sex : '',
)
const age = ref<number | ''>(auth.user?.age != null ? auth.user.age : '')
const saving = ref(false)

watch(
  () => auth.user,
  (u) => {
    if (u?.display_name != null) name.value = u.display_name
    if (u?.sex === 'male' || u?.sex === 'female') sex.value = u.sex
    else if (u) sex.value = ''
    age.value = u?.age != null ? u.age : ''
  },
  { deep: true },
)

async function save() {
  const trimmed = name.value.trim()
  if (!trimmed) {
    showFailToast('名字不能为空')
    return
  }
  if (trimmed.length > 32) {
    showFailToast('名字最多 32 字')
    return
  }
  if (!sex.value) {
    showFailToast('请选择性别（用于 BMR 计算）')
    return
  }
  const ageNum = age.value === '' ? NaN : Number(age.value)
  if (!Number.isInteger(ageNum) || ageNum < 10 || ageNum > 100) {
    showFailToast('年龄请填写 10–100 的整数')
    return
  }
  saving.value = true
  showLoadingToast({ message: '保存中…', forbidClick: true, duration: 0 })
  try {
    await auth.updateProfile({
      display_name: trimmed,
      sex: sex.value,
      age: ageNum,
    })
    closeToast()
    showSuccessToast('已保存')
  } catch {
    closeToast()
    showFailToast('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="settings">
    <header class="settings__top">
      <button type="button" class="settings__back" @click="router.back()">← 返回</button>
      <h1>设置</h1>
    </header>

    <section class="settings__card fit-card">
      <p class="fit-section-label">显示名称</p>
      <p class="settings__hint">
        当前身份 {{ personaById(auth.user?.id)?.emoji }} · 对方看到的也是这个名字
      </p>
      <van-field
        v-model="name"
        maxlength="32"
        placeholder="例如：龙龙 / 叶子"
        class="settings__field"
      />

      <p class="fit-section-label settings__label-gap">身体资料</p>
      <p class="settings__hint">用于 Mifflin-St Jeor 基础代谢（BMR）与今日热量上限</p>
      <van-field label="性别" class="settings__field settings__field--inline">
        <template #input>
          <van-radio-group v-model="sex" direction="horizontal" class="settings__sex">
            <van-radio name="male">男</van-radio>
            <van-radio name="female">女</van-radio>
          </van-radio-group>
        </template>
      </van-field>
      <van-field
        v-model.number="age"
        type="digit"
        label="年龄"
        placeholder="例如：28"
        class="settings__field"
      />

      <van-button type="primary" block :loading="saving" class="settings__save" @click="save">
        保存
      </van-button>
    </section>
  </div>
</template>

<style scoped>
.settings {
  min-height: 100vh;
  padding: 12px 16px 40px;
}

.settings__top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.settings__top h1 {
  margin: 0;
  font-size: 1.35rem;
  font-weight: 800;
}

.settings__back {
  border: none;
  background: transparent;
  font: inherit;
  font-weight: 700;
  color: var(--muted);
  cursor: pointer;
  padding: 0;
}

.settings__card {
  padding: 22px 18px;
}

.settings__hint {
  margin: 0 0 14px;
  font-size: 13px;
  color: var(--muted);
}

.settings__label-gap {
  margin-top: 8px;
}

.settings__field {
  margin-bottom: 16px;
  padding: 4px 12px;
  background: var(--bg);
  border-radius: 14px;
}

.settings__field--inline :deep(.van-field__body) {
  align-items: center;
}

.settings__field :deep(.van-cell) {
  background: transparent;
  padding: 8px 0;
}

.settings__sex {
  gap: 16px;
}

.settings__save {
  height: 44px !important;
  font-weight: 800 !important;
  border-radius: 14px !important;
}
</style>
