import { http } from './http'

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export async function sendChatMessage(message: string): Promise<string> {
  const { data } = await http.post<{ reply: string }>('/chat', { message })
  return data.reply
}

export async function fetchChatHistory(limit = 50): Promise<ChatMessage[]> {
  const { data } = await http.get<{ messages: ChatMessage[] }>('/chat/history', {
    params: { limit },
  })
  return data.messages
}

export async function clearChatHistory(): Promise<void> {
  await http.delete('/chat/history')
}

export const CHAT_DISCLAIMER = '非医疗建议，不能替代医师诊断。'
