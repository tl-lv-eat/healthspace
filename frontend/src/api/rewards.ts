import { http } from '@/api/http'

export interface Reward {
  id: number
  creator_user_id: string
  title: string
  description: string | null
  is_private: boolean
  scale_level: number
  cost_note: string
  points_price: number
  active: boolean
  created_at: string
}

export interface Redemption {
  id: number
  reward_id: number
  redeemer_user_id: string
  points_spent: number
  status: 'pending' | 'fulfilled' | 'cancelled'
  created_at: string
  fulfilled_at: string | null
  reward_title: string | null
}

export async function fetchRewards(): Promise<Reward[]> {
  const { data } = await http.get<Reward[]>('/rewards')
  return data
}

export async function createReward(payload: {
  title: string
  description?: string
  is_private?: boolean
  scale_level?: number
  cost_note?: string
  points_price: number
}): Promise<Reward> {
  const { data } = await http.post<Reward>('/rewards', payload)
  return data
}

export async function revealReward(id: number): Promise<string> {
  const { data } = await http.post<{ description: string }>(`/rewards/${id}/reveal`)
  return data.description
}

export async function redeemReward(id: number): Promise<Redemption> {
  const { data } = await http.post<Redemption>(`/rewards/${id}/redeem`)
  return data
}

export async function fetchMyRedemptions(): Promise<Redemption[]> {
  const { data } = await http.get<Redemption[]>('/rewards/redemptions/mine')
  return data
}

export async function patchRedemption(id: number, status: 'fulfilled' | 'cancelled'): Promise<Redemption> {
  const { data } = await http.patch<Redemption>(`/rewards/redemptions/${id}`, { status })
  return data
}
