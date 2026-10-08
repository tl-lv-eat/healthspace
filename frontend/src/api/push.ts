import { http } from './http'

export interface PushSettings {
  token: string
  enabled: boolean
  remind_hours: number[]
  last_success_at: string | null
  last_error: string | null
}

export async function fetchPushSettings(): Promise<PushSettings> {
  const { data } = await http.get<PushSettings>('/push/settings')
  return data
}

export async function savePushSettings(patch: Partial<PushSettings>): Promise<PushSettings> {
  const { data } = await http.put<PushSettings>('/push/settings', patch)
  return data
}

export async function testPush(): Promise<void> {
  await http.post('/push/test', {})
}
