import request from './request'

// ===== Health 设备健康度 =====

export interface HealthScoreView {
  equipmentId: number
  equipmentCode: string
  equipmentName: string
  category: string
  domain: string
  healthScore: number
  trend: string
  prevScore: number
}

export interface HealthOverview {
  averageScore: number
  criticalCount: number
  warningCount: number
  healthyCount: number
  scores: HealthScoreView[]
}

// ---- 后端/模拟原始结构: equipment_health.build_equipment_health() ----
interface RawEquip {
  id?: number | string
  code?: string
  name?: string
  domain?: string
  category?: string
  health?: number
  grade?: string
  issues?: unknown
  status?: string
  loadPct?: number
}
interface RawHealth {
  avgHealth?: number
  byDomain?: {
    domain?: string
    label?: string
    avgHealth?: number
    count?: number
    grade?: string
  }[]
  byEquipment?: RawEquip[]
  worst?: RawEquip[]
  summary?: { 优?: number; 良?: number; 中?: number; 差?: number }
  count?: number
}

function mapHealth(raw: RawHealth): HealthOverview {
  const summary = raw.summary ?? {}
  const scores: HealthScoreView[] = (raw.byEquipment ?? []).map((e) => ({
    equipmentId: Number(e.id ?? 0),
    equipmentCode: e.code ?? String(e.id ?? ''),
    equipmentName: e.name ?? e.code ?? String(e.id ?? ''),
    category: e.category ?? '',
    domain: e.domain ?? '',
    healthScore: Number(e.health ?? 0),
    trend: 'stable',
    prevScore: Number(e.health ?? 0),
  }))

  return {
    averageScore: Number(raw.avgHealth ?? 0),
    criticalCount: summary['差'] ?? 0,
    warningCount: (summary['良'] ?? 0) + (summary['中'] ?? 0),
    healthyCount: summary['优'] ?? 0,
    scores,
  }
}

export function getHealthOverview(): Promise<HealthOverview> {
  return request.get<unknown, RawHealth>('/api/ops/equipment-health').then(mapHealth)
}
