<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast } from 'vant'
import { http } from '@/api/http'
import { PERSONAS, personaById } from '@/constants/personas'
import { useAuthStore } from '@/stores/auth'

const props = withDefaults(defineProps<{ compact?: boolean }>(), { compact: true })

const auth = useAuthStore()
const router = useRouter()
const open = ref(false)
const switching = ref(false)

type LivePersona = { id: string; display_name: string; emoji: string }
const live = ref<LivePersona[]>([])

async function loadPersonas() {
  try {
    const { data } = await http.get<LivePersona[]>('/auth/personas')
    live.value = data
  } catch {
    live.value = PERSONAS.map((p) => ({
      id: p.id,
      display_name: p.label,
      emoji: p.emoji,
    }))
  }
}

onMounted(() => {
  void loadPersonas()
})

watch(
  () => auth.user?.display_name,
  () => {
    void loadPersonas()
  },
)

const options = computed(() => {
  if (live.value.length) return live.value
  return PERSONAS.map((p) => ({ id: p.id, display_name: p.label, emoji: p.emoji }))
})

const current = computed(() => {
  const fromLive = options.value.find((p) => p.id === auth.user?.id)
  if (fromLive) return fromLive
  const base = personaById(auth.user?.id)
  return base
    ? { id: base.id, display_name: auth.user?.display_name ?? base.label, emoji: base.emoji }
    : null
})

async function switchTo(id: string) {
  if (!id || id === auth.user?.id || switching.value) {
    open.value = false
    return
  }
  switching.value = true
  open.value = false
  showLoadingToast({ message: '切换中…', forbidClick: true, duration: 0 })
  try {
    await auth.select(id)
    closeToast()
    await router.replace(router.currentRoute.value.fullPath)
  } catch {
    closeToast()
    showFailToast('切换失败')
  } finally {
    switching.value = false
  }
}
</script>

<template>
  <div class="ps" :class="{ 'ps--compact': props.compact }">
    <button
      type="button"
      class="ps__trigger"
      :aria-expanded="open"
      :disabled="switching"
      @click="open = !open"
    >
      <span class="ps__emoji">{{ current?.emoji ?? '·' }}</span>
      <span class="ps__name">{{ current?.display_name ?? '选择' }}</span>
      <span class="ps__caret">▾</span>
    </button>
    <div v-if="open" class="ps__menu" role="listbox">
      <button
        v-for="p in options"
        :key="p.id"
        type="button"
        class="ps__option"
        :class="{ 'ps__option--on': p.id === auth.user?.id }"
        role="option"
        @click="switchTo(p.id)"
      >
        <span class="ps__emoji">{{ p.emoji }}</span>
        <strong class="ps__label">{{ p.display_name }}</strong>
      </button>
    </div>
    <button v-if="open" type="button" class="ps__scrim" aria-label="关闭" @click="open = false" />
  </div>
</template>

<style scoped>
.ps {
  position: relative;
  z-index: 20;
}

.ps__trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  max-width: 140px;
  padding: 0 10px 0 8px;
  border: 1px solid var(--line);
  border-radius: 999px;
  background: var(--card);
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  font: inherit;
}

.ps__emoji {
  font-size: 1.05rem;
  line-height: 1;
}

.ps__name {
  font-size: 13px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ps__caret {
  font-size: 10px;
  color: var(--muted);
  flex-shrink: 0;
}

.ps__menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 168px;
  padding: 6px;
  border-radius: 16px;
  background: var(--card);
  box-shadow: var(--shadow);
  display: grid;
  gap: 4px;
  z-index: 22;
}

.ps__option {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 10px 12px;
  border: none;
  border-radius: 12px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
}

.ps__option--on,
.ps__option:hover {
  background: var(--primary-soft);
}

.ps__label {
  font-size: 14px;
  font-weight: 700;
}

.ps__scrim {
  position: fixed;
  inset: 0;
  border: none;
  background: transparent;
  z-index: 21;
  cursor: default;
}
</style>
