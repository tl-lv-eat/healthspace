import { http } from '@/api/http'

export interface WaterEntry {
  id: number
  user_id: string
  date: string
  amount_ml: number
  created_at: string
}

export interface WaterDay {
  target_ml: number
  total_ml: number
  entries: WaterEntry[]
}

export async function fetchWaterDay(date: string): Promise<WaterDay> {
  const { data } = await http.get<WaterDay>('/water', { params: { date } })
  return data
}

export async function addWaterEntry(date: string, amount_ml: number): Promise<WaterEntry> {
  const { data } = await http.post<WaterEntry>('/water', { date, amount_ml })
  return data
}

export async function patchWaterEntry(id: number, amount_ml: number): Promise<WaterEntry> {
  const { data } = await http.patch<WaterEntry>(`/water/${id}`, { amount_ml })
  return data
}

export async function deleteWaterEntry(id: number): Promise<void> {
  await http.delete(`/water/${id}`)
}
