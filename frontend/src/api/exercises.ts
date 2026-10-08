import { http } from '@/api/http'

export interface Exercise {
  id: number
  slug: string
  name_zh: string
  name_en: string
  body_part: string
  gif_url: string
  instructions_zh: string
  is_custom: boolean
  owner_user_id: string | null
}

export async function fetchExercises(bodyPart?: string): Promise<Exercise[]> {
  const { data } = await http.get<Exercise[]>('/exercises', {
    params: bodyPart ? { body_part: bodyPart } : undefined,
  })
  return data
}
