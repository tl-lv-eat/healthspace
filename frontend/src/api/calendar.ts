import { http } from '@/api/http'
import type { TodayResponse } from '@/api/today'

export type DayLevel = 'full' | 'partial' | 'none'

export interface DayStatus {
  meal: boolean
  water: boolean
  workout: boolean
  level: DayLevel
}

export interface CalendarDay {
  date: string
  dragon: DayStatus
  leaf: DayStatus
}

export interface CalendarMonth {
  year: number
  month: number
  days: CalendarDay[]
}

export interface CalendarDayDetail {
  date: string
  dragon: { user_id: string; display_name: string; status: DayStatus }
  leaf: { user_id: string; display_name: string; status: DayStatus }
  me: TodayResponse['me']
  partner: TodayResponse['partner']
}

export async function fetchCalendarMonth(year: number, month: number): Promise<CalendarMonth> {
  const { data } = await http.get<CalendarMonth>('/calendar', { params: { year, month } })
  return data
}

export async function fetchCalendarDay(date: string): Promise<CalendarDayDetail> {
  const { data } = await http.get<CalendarDayDetail>('/calendar/day', { params: { date } })
  return data
}
