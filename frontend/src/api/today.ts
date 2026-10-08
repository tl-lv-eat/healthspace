import { http } from '@/api/http'
import type { Meal } from '@/api/meals'

export interface DoneFlags {
  meal: boolean
  water: boolean
  workout: boolean
}

export interface TodayWaterSummary {
  total_ml: number
  target_ml: number
  done: boolean
}

export interface TodayMe {
  user_id: string
  meals: Meal[]
  water: TodayWaterSummary
  workouts: unknown[]
  done: DoneFlags
}

export interface TodayPartner {
  user_id: string
  display_name: string
  done: DoneFlags
  water_total_ml: number
  water_target_ml: number
}

export interface TodayResponse {
  date: string
  me: TodayMe
  partner: TodayPartner
}

export async function fetchToday(date: string): Promise<TodayResponse> {
  const { data } = await http.get<TodayResponse>('/today', { params: { date } })
  return data
}

export function formatDateLocal(d = new Date()): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function formatDateLabel(dateStr: string): string {
  const [y, m, d] = dateStr.split('-').map(Number)
  if (!y || !m || !d) return dateStr
  const dt = new Date(y, m - 1, d)
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${m}月${d}日 周${weekdays[dt.getDay()]}`
}
