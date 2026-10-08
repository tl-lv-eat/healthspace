import { http } from './http'

export interface AiReport {
  id: number
  user_id: string
  kind: 'daily' | 'weekly'
  period_key: string
  content_md: string
  created_at: string
}

export async function fetchReport(kind: 'daily' | 'weekly', period: string): Promise<AiReport> {
  const { data } = await http.get<AiReport>('/reports', { params: { kind, period } })
  return data
}

export async function generateReport(
  kind: 'daily' | 'weekly',
  period: string,
  force = false,
): Promise<AiReport> {
  const { data } = await http.post<AiReport>('/reports/generate', { kind, period, force })
  return data
}
