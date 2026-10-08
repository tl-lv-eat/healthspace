import { http } from '@/api/http'

export interface LedgerEntry {
  id: number
  delta: number
  reason: string
  created_at: string
}

export async function fetchPointsBalance(): Promise<number> {
  const { data } = await http.get<{ balance: number }>('/points/balance')
  return data.balance
}

export async function fetchPointsLedger(): Promise<LedgerEntry[]> {
  const { data } = await http.get<LedgerEntry[]>('/points/ledger')
  return data
}

export async function evaluatePoints(date: string): Promise<void> {
  await http.post('/points/evaluate', { date })
}
