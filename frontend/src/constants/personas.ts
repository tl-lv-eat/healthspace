export const PERSONAS = [
  { id: 'dragon', emoji: '🐉', label: '龙龙' },
  { id: 'leaf', emoji: '🍃', label: '孙孙' },
] as const

export type PersonaId = (typeof PERSONAS)[number]['id']

export function personaById(id: string | undefined | null) {
  return PERSONAS.find((p) => p.id === id) ?? null
}

export function otherPersona(id: string | undefined | null) {
  return PERSONAS.find((p) => p.id !== id) ?? PERSONAS[0]
}
