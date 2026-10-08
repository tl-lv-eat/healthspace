import { http } from '@/api/http'

export interface JournalUserRow {
  user_id: string
  display_name: string
  meal_done: boolean
  water_total_ml: number
  water_target_ml: number
  water_done: boolean
  workout_done: boolean
}

export interface JournalItem {
  date: string
  users: JournalUserRow[]
}

export async function fetchJournal(
  from: string,
  to: string,
  userId?: string,
): Promise<JournalItem[]> {
  const { data } = await http.get<{ items: JournalItem[] }>('/journal', {
    params: { from, to, user_id: userId || undefined },
  })
  return data.items
}
