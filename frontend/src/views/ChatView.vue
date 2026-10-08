<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { closeToast, showFailToast, showLoadingToast } from 'vant'
import {
  CHAT_DISCLAIMER,
  clearChatHistory,
  fetchChatHistory,
  sendChatMessage,
  type ChatMessage,
} from '@/api/chat'

const router = useRouter()
const messages = ref<ChatMessage[]>([])
const input = ref('')
const listEl = ref<HTMLElement | null>(null)
const sending = ref(false)

async function scrollBottom() {
  await nextTick()
  const el = listEl.value
  if (el) el.scrollTop = el.scrollHeight
}

async function loadHistory() {
  try {
    messages.value = await fetchChatHistory(50)
    await scrollBottom()
  } catch {
    showFailToast('加载聊天记录失败')
  }
}

async function send() {
  const text = input.value.trim()
  if (!text || sending.value) return
  sending.value = true
  input.value = ''
  showLoadingToast({ message: '思考中…', forbidClick: true, duration: 0 })
  try {
    const reply = await sendChatMessage(text)
    await loadHistory()
    if (!messages.value.some((m) => m.role === 'assistant' && m.content === reply)) {
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        content: reply,
        created_at: new Date().toISOString(),
      })
    }
    await scrollBottom()
  } catch {
    showFailToast('发送失败')
    input.value = text
  } finally {
    sending.value = false
    closeToast()
  }
}

async function onClear() {
  try {
    await clearChatHistory()
    messages.value = []
  } catch {
    showFailToast('清空失败')
  }
}

function goBack() {
  router.back()
}

onMounted(() => {
  void loadHistory()
})
</script>

<template>
  <div class="chat-page">
    <van-nav-bar title="智能聊天" left-arrow @click-left="goBack">
      <template #right>
        <button type="button" class="chat-page__clear" @click="onClear">清空</button>
      </template>
    </van-nav-bar>

    <div ref="listEl" class="chat-page__list">
      <div
        v-for="m in messages"
        :key="m.id"
        class="chat-page__bubble"
        :class="m.role === 'user' ? 'chat-page__bubble--user' : 'chat-page__bubble--bot'"
      >
        {{ m.content }}
      </div>
    </div>

    <footer class="chat-page__footer">
      <p class="chat-page__disclaimer">{{ CHAT_DISCLAIMER }}</p>
      <div class="chat-page__input-row">
        <van-field v-model="input" rows="1" autosize type="textarea" placeholder="问教练…" />
        <van-button type="primary" size="small" :disabled="sending" @click="send">发送</van-button>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg);
}

.chat-page__clear {
  border: none;
  background: none;
  color: var(--primary);
  font-weight: 700;
  font-size: 13px;
}

.chat-page__list {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px 8px;
}

.chat-page__bubble {
  max-width: 85%;
  margin-bottom: 10px;
  padding: 10px 14px;
  border-radius: 16px;
  font-size: 14px;
  line-height: 1.45;
  font-weight: 500;
}

.chat-page__bubble--user {
  margin-left: auto;
  background: var(--primary);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-page__bubble--bot {
  margin-right: auto;
  background: var(--card);
  box-shadow: var(--shadow-sm);
  border-bottom-left-radius: 4px;
}

.chat-page__footer {
  padding: 8px 12px calc(8px + env(safe-area-inset-bottom));
  background: var(--card);
  border-top: 1px solid var(--line);
}

.chat-page__disclaimer {
  margin: 0 4px 8px;
  font-size: 11px;
  color: var(--muted);
  text-align: center;
  line-height: 1.35;
}

.chat-page__input-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}
</style>
