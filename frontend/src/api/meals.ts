import { http } from '@/api/http'

export type MealType = 'breakfast' | 'lunch' | 'dinner' | 'snack'

export interface Meal {
  id: number
  user_id: string
  date: string
  meal_type: MealType
  image_path: string | null
  food_summary: string
  ai_kcal: number | null
  user_kcal: number
  advice: string
  created_at: string
}

export interface MealEstimate {
  food_summary: string
  kcal: number
  advice: string
  reason: string
  image_path: string
  estimate_failed?: boolean
}

export interface MealCreatePayload {
  date: string
  meal_type: MealType
  food_summary: string
  ai_kcal?: number | null
  user_kcal: number
  advice?: string
  image_path?: string | null
}

export async function fetchMeals(date: string): Promise<Meal[]> {
  const { data } = await http.get<Meal[]>('/meals', { params: { date } })
  return data
}

export async function estimateMeal(file: File): Promise<MealEstimate> {
  const form = new FormData()
  form.append('file', file)
  // Do not set Content-Type manually — browser/axios must add multipart boundary.
  const { data } = await http.post<MealEstimate>('/meals/estimate', form, {
    timeout: 120_000,
  })
  return data
}

export async function refineMealEstimate(payload: {
  image_path?: string | null
  food_summary: string
  kcal: number
  reason: string
  advice: string
  message: string
}): Promise<MealEstimate> {
  const { data } = await http.post<MealEstimate>('/meals/estimate/refine', payload, {
    timeout: 120_000,
  })
  return data
}

export async function createMeal(payload: MealCreatePayload): Promise<Meal> {
  const { data } = await http.post<Meal>('/meals', payload)
  return data
}

export async function patchMeal(
  id: number,
  body: { user_kcal?: number; food_summary?: string },
): Promise<Meal> {
  const { data } = await http.patch<Meal>(`/meals/${id}`, body)
  return data
}

export async function deleteMeal(id: number): Promise<void> {
  await http.delete(`/meals/${id}`)
}

export const MEAL_TYPE_LABELS: Record<MealType, string> = {
  breakfast: '早餐',
  lunch: '午餐',
  dinner: '晚餐',
  snack: '加餐',
}

export const MEAL_TYPES: MealType[] = ['breakfast', 'lunch', 'dinner', 'snack']
