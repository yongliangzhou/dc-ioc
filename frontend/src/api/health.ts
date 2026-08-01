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

export function getHealthOverview(): Promise<HealthOverview> {
  return request.get('/api/health/overview').then((r: any) => r.data)
}
