import { http } from '@/api/http'

export type CardioType = 'run' | 'walk' | 'cycle' | 'rope' | 'elliptical' | 'other'

export const CARDIO_TYPE_LABELS: Record<CardioType, string> = {
  run: '跑步',
  walk: '步行',
  cycle: '骑行',
  rope: '跳绳',
  elliptical: '椭圆机',
  other: '其他',
}

export const BODY_PART_LABELS: Record<string, string> = {
  bodyweight: '自重',
  kettlebell: '壶铃',
  chest: '胸',
  back: '背',
  shoulders: '肩',
  legs: '腿',
  arms: '臂',
  core: '核心',
}

export interface WorkoutSet {
  reps: number
  weight?: number
}

export interface WorkoutPayloadCardio {
  cardio_type: CardioType
  duration_min: number
  intensity?: string
}

export interface WorkoutPayloadStrength {
  body_part: string
  exercise_name: string
  exercise_id?: number
  duration_min?: number
  sets: WorkoutSet[]
}

export interface Workout {
  id: number
  user_id: string
  date: string
  kind: 'cardio' | 'strength'
  payload: WorkoutPayloadCardio | WorkoutPayloadStrength
  created_at: string
}

export interface CardioCreate {
  date: string
  kind: 'cardio'
  cardio_type: CardioType
  duration_min: number
  intensity?: string
}

export interface StrengthCreate {
  date: string
  kind: 'strength'
  body_part: string
  exercise_id?: number
  exercise_name: string
  duration_min: number
  sets: WorkoutSet[]
}

export async function fetchWorkouts(date: string): Promise<Workout[]> {
  const { data } = await http.get<Workout[]>('/workouts', { params: { date } })
  return data
}

export async function createWorkout(body: CardioCreate | StrengthCreate): Promise<Workout> {
  const { data } = await http.post<Workout>('/workouts', body)
  return data
}

export async function deleteWorkout(id: number): Promise<void> {
  await http.delete(`/workouts/${id}`)
}

export async function patchWorkout(
  id: number,
  body: Partial<{
    cardio_type: CardioType
    duration_min: number
    intensity: string
    body_part: string
    exercise_name: string
    exercise_id: number
    sets: WorkoutSet[]
  }>,
): Promise<Workout> {
  const { data } = await http.patch<Workout>(`/workouts/${id}`, body)
  return data
}

export function formatWorkoutSummary(w: Workout): string {
  if (w.kind === 'cardio') {
    const p = w.payload as WorkoutPayloadCardio
    const label = CARDIO_TYPE_LABELS[p.cardio_type] ?? p.cardio_type
    return `${label} ${p.duration_min} 分钟`
  }
  const p = w.payload as WorkoutPayloadStrength
  const part = BODY_PART_LABELS[p.body_part] ?? p.body_part
  const setCount = p.sets?.length ?? 0
  const reps = p.sets?.[0]?.reps
  const repsPart = reps != null ? ` · ${setCount}×${reps}` : setCount ? ` · ${setCount} 组` : ''
  const minPart = (p.duration_min ?? 0) > 0 ? ` · ${p.duration_min} 分钟` : ''
  return `${part} · ${p.exercise_name}${minPart}${repsPart}`
}
