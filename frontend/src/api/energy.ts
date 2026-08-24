import request from './request'
import type { EnergyAdvice } from '@/types'

// ===== Energy 能耗分析 =====

export interface EnergyTrend {
  date: string
  pue: number | null
  totalKwh: number
  itKwh: number
  coolingKwh: number
}

export interface EnergyOverview {
  todayPue: number | null
  todayTotalKwh: number | null
  todayItKwh: number | null
  todayCoolingKwh: number | null
  weekTrend: EnergyTrend[]
  loadForecast?: { h: number; actual: number | null; pred: number }[]
  aiSaving?: { enabled?: boolean; algo?: string; monthSaveKwh?: number; saveRate?: number }
  breakdown?: { id: string; kw: number; pct: number }[]
  carbon?: { greenPct?: number; pv?: string; monthCO2?: number }
  advice?: EnergyAdvice
}

// ---- 后端/模拟原始结构: generated.energy() ----
interface RawBreakdown {
  id?: string
  name?: string
  kw?: number
  pct?: number
}
interface RawEnergy {
  todayKwh?: number
  monthKwh?: number
  yearKwh?: number
  pueTrend?: number[]
  loadForecast?: { h: number; actual: number | null; pred: number }[]
  aiSaving?: { enabled?: boolean; algo?: string; monthSaveKwh?: number; saveRate?: number }
  breakdown?: RawBreakdown[]
  carbon?: { greenPct?: number; pv?: string; monthCO2?: number }
}

function mapEnergy(raw: RawEnergy): EnergyOverview {
  const pueTrend = raw.pueTrend ?? []
  const lastPue = pueTrend.length ? pueTrend[pueTrend.length - 1] : null
  const breakdown = raw.breakdown ?? []
  const it = breakdown.find((b) => (b.id ?? b.name ?? '').includes('IT'))
  const cool = breakdown.find((b) => (b.id ?? b.name ?? '').includes('制冷'))
  const itKwh = it?.kw ?? null
  const coolKwh = cool?.kw ?? null
  const todayTotal = raw.todayKwh ?? null

  const weekTrend: EnergyTrend[] = pueTrend.map((p, i) => ({
    date: `D${i + 1}`,
    pue: p,
    totalKwh: todayTotal ? Math.round(todayTotal / Math.max(1, pueTrend.length)) : 0,
    itKwh: itKwh ? Math.round(itKwh / Math.max(1, pueTrend.length)) : 0,
    coolingKwh: coolKwh ? Math.round(coolKwh / Math.max(1, pueTrend.length)) : 0,
  }))

  return {
    todayPue: lastPue,
    todayTotalKwh: todayTotal ?? null,
    todayItKwh: itKwh ?? null,
    todayCoolingKwh: coolKwh ?? null,
    weekTrend,
    loadForecast: raw.loadForecast ?? [],
    aiSaving: raw.aiSaving,
    breakdown: (raw.breakdown ?? []).map((b) => ({
      id: b.id ?? b.name ?? '',
      kw: b.kw ?? 0,
      pct: b.pct ?? 0,
    })),
    carbon: raw.carbon,
    advice: (raw as { advice?: EnergyAdvice }).advice,
  }
}

export function getEnergyOverview(): Promise<EnergyOverview> {
  return request.get<unknown, RawEnergy>('/api/ops/energy').then(mapEnergy)
}

export interface EnergyAdviceAdoptIn {
  suggestionId: string
  title: string
  priority: string
  savingKw: number
  savingPct: number
  detail: string
  basis: string
  action: 'adopt' | 'ignore'
  note?: string
  pueCurrent?: number | null
  pueTarget?: number | null
  user?: string
}

export interface EnergyAdviceAdoptRecord {
  id: number
  suggestionId: string
  title: string
  priority: string
  savingKw: number
  savingPct: number
  detail: string
  basis: string
  action: string
  note: string
  pueCurrent: number
  pueTarget: number
  user: string
  createdAt: string
}

export function adoptEnergyAdvice(payload: EnergyAdviceAdoptIn): Promise<EnergyAdviceAdoptRecord> {
  return request.post<unknown, EnergyAdviceAdoptRecord>('/api/ops/energy/advice', payload)
}

export function getEnergyAdvice(action = ''): Promise<{ records: EnergyAdviceAdoptRecord[]; stats: { total: number; adopted: number; ignored: number; adoptedSavingKw: number } }> {
  return request.get('/api/ops/energy/advice', { params: action ? { action } : {} })
}
