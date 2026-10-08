import { http } from '@/api/http'
import type { DaySection, TodayMe, TodayPartner } from '@/api/today'

export type DayLevel = 'full' | 'partial' | 'none'

export interface DayStatus {
  meal: boolean
  water: boolean
  workout: boolean
  level: DayLevel
  intake_kcal?: number
  burn_kcal?: number
  bmr?: number
  surplus_kcal?: number
  calorie_exceeded?: boolean
  calorie_ok?: boolean
  water_ml?: number
  water_target_ml?: number
  water_ok?: boolean
  daily_deficit_target?: number
  deficit_contrib?: number
  had_workout?: boolean
}

export interface CalendarDay {
  date: string
  dragon: DayStatus
  leaf: DayStatus
}

export interface WeekProgress {
  week_start: string
  start_date?: string
  end_date?: string
  period_days?: number
  weekly_kcal_deficit_target: number
  weekly_kcal_deficit_done: number
  weekly_workout_sessions_target: number
  weekly_workout_sessions_done: number
  water_ok_days: number
  target_weight_kg: number | null
  water_target_ml: number
}

export interface CalendarMonth {
  year: number
  month: number
  days: CalendarDay[]
  week_start?: string
  my_week_progress?: WeekProgress
}

export interface CalendarPersonaSummary {
  user_id: string
  display_name: string
  status: DayStatus
}

export interface CalendarDayDetail {
  date: string
  dragon: CalendarPersonaSummary
  leaf: CalendarPersonaSummary
  sections: {
    dragon: DaySection
    leaf: DaySection
  }
  /** Viewer-relative sections (legacy; prefer `sections` for dual-column UI). */
  me: TodayMe
  partner: TodayPartner
}

export async function fetchCalendarMonth(year: number, month: number): Promise<CalendarMonth> {
  const { data } = await http.get<CalendarMonth>('/calendar', { params: { year, month } })
  return data
}

export async function fetchCalendarDay(date: string): Promise<CalendarDayDetail> {
  const { data } = await http.get<CalendarDayDetail>('/calendar/day', { params: { date } })
  return data
}
