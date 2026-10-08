import { http } from '@/api/http'

export interface CoupleSettings {
  settle_hour: number
  points_daily_water: number
  points_daily_deficit: number
  points_daily_workout_40: number
  points_plan_tier_b: number
  points_plan_tier_a: number
  points_plan_tier_fail: number
}

export async function fetchCoupleSettings(): Promise<CoupleSettings> {
  const { data } = await http.get<CoupleSettings>('/couple-settings')
  return data
}

export async function patchCoupleSettings(
  payload: Partial<CoupleSettings>,
): Promise<CoupleSettings> {
  const { data } = await http.patch<CoupleSettings>('/couple-settings', payload)
  return data
}

export async function settleDaily(date: string): Promise<Record<string, unknown>> {
  const { data } = await http.post<Record<string, unknown>>('/couple-settings/settle', null, {
    params: { date },
  })
  return data
}
