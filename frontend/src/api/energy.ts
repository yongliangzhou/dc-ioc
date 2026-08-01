import request from './request'

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
}

export function getEnergyOverview(): Promise<EnergyOverview> {
  return request.get('/api/ops/energy').then((r: any) => r.data)
}
