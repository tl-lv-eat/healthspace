import { http } from '@/api/http'

export type AchievementScope = 'shared' | 'persona'
export type AchievementMetric =
  | 'green_days_total'
  | 'green_streak'
  | 'workout_sessions'
  | 'workout_minutes_total'
  | 'water_ok_days'
  | 'bmi_in_range'
  | 'body_fat_max'

export type MineAchievementStatus = 'incomplete' | 'claimable' | 'claimed'

export interface Achievement {
  id: number
  slug: string
  title: string
  description: string
  scope: AchievementScope
  metric: AchievementMetric
  target_value: number
  points_reward: number
  rule_json: Record<string, unknown>
  bind_user_id: string | null
  bind_sex: string | null
  sort_order: number
  enabled: boolean
}

export interface MineAchievementItem {
  achievement: Achievement
  progress: number
  target: number
  status: MineAchievementStatus
  claimed_at: string | null
}

export interface MineAchievementsResponse {
  incomplete: MineAchievementItem[]
  claimable: MineAchievementItem[]
  claimed: MineAchievementItem[]
}

export async function fetchMineAchievements(): Promise<MineAchievementsResponse> {
  const { data } = await http.get<MineAchievementsResponse>('/achievements/mine')
  return data
}

export async function claimAchievement(achievementId: number): Promise<MineAchievementItem> {
  const { data } = await http.post<MineAchievementItem>(`/achievements/${achievementId}/claim`)
  return data
}

export async function fetchAchievementCatalog(): Promise<Achievement[]> {
  const { data } = await http.get<Achievement[]>('/achievements')
  return data
}

export async function createAchievement(payload: {
  slug: string
  title: string
  description?: string
  scope?: AchievementScope
  metric: AchievementMetric
  target_value: number
  points_reward: number
  rule_json?: Record<string, unknown>
}): Promise<Achievement> {
  const { data } = await http.post<Achievement>('/achievements', payload)
  return data
}

export async function patchAchievement(
  id: number,
  payload: Partial<{
    title: string
    description: string
    target_value: number
    points_reward: number
    enabled: boolean
  }>,
): Promise<Achievement> {
  const { data } = await http.patch<Achievement>(`/achievements/${id}`, payload)
  return data
}

export async function deleteAchievement(id: number): Promise<void> {
  await http.delete(`/achievements/${id}`)
}
