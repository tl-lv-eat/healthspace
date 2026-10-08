import { http } from '@/api/http'

export type RewardCategory = 'food' | 'fun' | 'intimacy' | 'adult'
export type RewardStatus = 'pending_review' | 'listed' | 'rejected' | 'archived'
export type RewardListScope = 'listed' | 'pending_review_for_me' | 'mine'

export const REWARD_CATEGORY_OPTIONS: { value: RewardCategory; label: string }[] = [
  { value: 'food', label: '饮食奖励' },
  { value: 'fun', label: '玩乐奖励' },
  { value: 'intimacy', label: '亲密奖励' },
  { value: 'adult', label: '18+奖励' },
]

export function rewardCategoryLabel(category: RewardCategory | string): string {
  return REWARD_CATEGORY_OPTIONS.find((o) => o.value === category)?.label ?? category
}

export interface Reward {
  id: number
  creator_user_id: string
  title: string
  description: string | null
  is_private: boolean
  scale_level: number
  cost_note: string
  points_price: number
  category: RewardCategory
  status: RewardStatus
  reject_reason: string | null
  reviewed_by: string | null
  reviewed_at: string | null
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

export interface FetchRewardsParams {
  scope?: RewardListScope
  category?: RewardCategory
}

export async function fetchRewards(params: FetchRewardsParams = {}): Promise<Reward[]> {
  const { data } = await http.get<Reward[]>('/rewards', { params })
  return data
}

export async function createReward(payload: {
  title: string
  description?: string
  is_private?: boolean
  scale_level?: number
  cost_note?: string
  points_price: number
  category: RewardCategory
}): Promise<Reward> {
  const { data } = await http.post<Reward>('/rewards', payload)
  return data
}

export async function patchReward(
  id: number,
  payload: Partial<{
    title: string
    description: string
    is_private: boolean
    scale_level: number
    cost_note: string
    points_price: number
    category: RewardCategory
    active: boolean
  }>,
): Promise<Reward> {
  const { data } = await http.patch<Reward>(`/rewards/${id}`, payload)
  return data
}

export async function approveReward(id: number): Promise<Reward> {
  const { data } = await http.post<Reward>(`/rewards/${id}/approve`)
  return data
}

export async function rejectReward(id: number, reason: string): Promise<Reward> {
  const { data } = await http.post<Reward>(`/rewards/${id}/reject`, { reason })
  return data
}

export async function resubmitReward(id: number): Promise<Reward> {
  const { data } = await http.post<Reward>(`/rewards/${id}/resubmit`)
  return data
}

export async function archiveReward(id: number): Promise<Reward> {
  const { data } = await http.post<Reward>(`/rewards/${id}/archive`)
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

export async function fetchCoupleRedemptions(): Promise<Redemption[]> {
  const { data } = await http.get<Redemption[]>('/rewards/redemptions', {
    params: { scope: 'couple' },
  })
  return data
}

export async function fetchMyRedemptions(): Promise<Redemption[]> {
  const { data } = await http.get<Redemption[]>('/rewards/redemptions/mine')
  return data
}

export async function patchRedemption(id: number, status: 'fulfilled'): Promise<Redemption> {
  const { data } = await http.patch<Redemption>(`/rewards/redemptions/${id}`, { status })
  return data
}
