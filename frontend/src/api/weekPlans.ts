import { http } from '@/api/http'

export interface WeekPlan {
  id: number | null
  user_id: string
  week_start: string
  water_target_ml: number
  meal_mode: string
  workout_mode: string
  workout_cardio_min: number | null
  workout_strength_sets: number | null
}

export interface WeekPlanUpsert {
  week_start: string
  water_target_ml: number
  meal_mode: string
  workout_mode: string
  workout_cardio_min?: number | null
  workout_strength_sets?: number | null
}

export async function fetchWeekPlan(weekStart: string): Promise<WeekPlan> {
  const { data } = await http.get<WeekPlan>('/week-plans', { params: { week_start: weekStart } })
  return data
}

export async function saveWeekPlan(body: WeekPlanUpsert): Promise<WeekPlan> {
  const { data } = await http.put<WeekPlan>('/week-plans', body)
  return data
}
