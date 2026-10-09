import { http } from '@/api/http'
import type { Meal } from '@/api/meals'
import type { Workout } from '@/api/workouts'

export interface DoneFlags {
  meal: boolean
  water: boolean
  workout: boolean
}

export interface WaterEntryBrief {
  id: number
  amount_ml: number
  created_at: string
}

export interface TodayWaterSummary {
  total_ml: number
  target_ml: number
  done: boolean
  entries: WaterEntryBrief[]
}

export interface DayEnergy {
  intake_kcal: number
  burn_kcal: number
  bmr: number
  surplus_kcal: number
  /** Plan progress credit; 0 until meals are complete (default 早午晚). */
  deficit_contrib?: number
  meals_complete?: boolean
  /** No meal / water / workout logged. */
  empty?: boolean
  daily_deficit_target: number
  daily_kcal_cap: number | null
  water_target_ml: number
  period_days: number
}

export interface TodayPlanBrief {
  id: number
  title: string | null
  start_date: string
  end_date: string
}

export interface DaySection {
  user_id: string
  display_name?: string
  meals: Meal[]
  water: TodayWaterSummary
  workouts: Workout[]
  done: DoneFlags
  energy: DayEnergy
  plan: TodayPlanBrief | null
}

export type TodayMe = DaySection

export type TodayPartner = DaySection & { display_name: string }

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
