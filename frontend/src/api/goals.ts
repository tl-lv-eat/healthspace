import { http } from '@/api/http'

export interface Goal {
  id: number
  user_id: string
  kind: 'short' | 'long'
  title: string
  description: string
  metric: 'weight_kg' | 'workout_days' | 'custom'
  target_value: number
  current_value: number
  unit: string
  start_date: string
  end_date: string | null
  status: 'active' | 'done' | 'cancelled'
  created_at: string
}

export interface GoalCreatePayload {
  kind: string
  title: string
  description?: string
  metric: string
  target_value: number
  unit?: string
  start_date: string
  end_date?: string | null
}

export async function fetchGoals(scope: 'mine' | 'all' = 'all'): Promise<Goal[]> {
  const { data } = await http.get<Goal[]>('/goals', { params: { scope } })
  return data
}

export async function createGoal(payload: GoalCreatePayload): Promise<Goal> {
  const { data } = await http.post<Goal>('/goals', payload)
  return data
}

export async function refreshGoal(id: number): Promise<Goal> {
  const { data } = await http.post<Goal>(`/goals/${id}/refresh`)
  return data
}
