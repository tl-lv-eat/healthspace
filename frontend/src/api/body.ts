import { http } from '@/api/http'

export interface BodyMetricCreate {
  recorded_on: string
  weight_kg?: number | null
  waist_cm?: number | null
  body_fat_pct?: number | null
  chest_cm?: number | null
  hip_cm?: number | null
  height_cm?: number | null
  note?: string
}

export interface BodyMetricOut extends BodyMetricCreate {
  id: number
  user_id: string
  created_at: string
  bmi: number | null
}

export interface TrendPoint {
  date: string
  weight_kg: number | null
  bmi: number | null
}

export interface TrendSeries {
  user_id: string
  points: TrendPoint[]
}

export async function createBodyMetric(body: BodyMetricCreate): Promise<BodyMetricOut> {
  const { data } = await http.post<BodyMetricOut>('/body', body)
  return data
}

export async function fetchBodyTrend(userIds: string[]): Promise<TrendSeries[]> {
  const { data } = await http.get<{ series: TrendSeries[] }>('/body/trend', {
    params: { user_ids: userIds.join(',') },
  })
  return data.series
}

export async function fetchBodyMetrics(userId?: string): Promise<BodyMetricOut[]> {
  const { data } = await http.get<BodyMetricOut[]>('/body', {
    params: userId ? { user_id: userId } : undefined,
  })
  return data
}
