import { http } from '@/api/http'

export interface WeekPlan {
  id: number | null
  user_id: string
  week_start: string
  start_date: string
  end_date: string
  period_days: number
  title: string | null
  note: string
  daily_kcal_cap: number | null
  water_target_ml: number
  weekly_kcal_deficit: number
  weekly_workout_sessions: number
  target_weight_kg: number | null
  meal_mode: string
  workout_mode: string
  workout_cardio_min: number | null
  workout_strength_sets: number | null
}

export interface WeekPlanUpsert {
  id?: number | null
  target_user_id?: string
  week_start?: string
  start_date: string
  end_date: string
  title?: string | null
  note?: string
  daily_kcal_cap?: number | null
  water_target_ml: number
  weekly_kcal_deficit: number
  weekly_workout_sessions: number
  target_weight_kg?: number | null
  meal_mode?: string
  workout_mode?: string
  workout_cardio_min?: number | null
  workout_strength_sets?: number | null
}

export async function fetchWeekPlan(on: string): Promise<WeekPlan> {
  const { data } = await http.get<WeekPlan>('/week-plans', { params: { on } })
  return data
}

export async function listWeekPlans(month?: string): Promise<WeekPlan[]> {
  const { data } = await http.get<WeekPlan[]>('/week-plans', {
    params: { list: true, ...(month != null && month !== '' ? { month } : {}) },
  })
  return data
}

export async function saveWeekPlan(body: WeekPlanUpsert): Promise<WeekPlan> {
  const { data } = await http.put<WeekPlan>('/week-plans', body)
  return data
}

export async function deleteWeekPlan(id: number): Promise<void> {
  await http.delete(`/week-plans/${id}`)
}
