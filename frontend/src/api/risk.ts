import request from './request'
export interface RiskView { id: number; code: string; title: string; category: string; severity: string; probability: string; description: string | null; mitigation: string | null; status: string }
export interface RiskStats { total: number; open: number; mitigated: number; critical: number; high: number }
export function getRisks(): Promise<RiskView[]> { return request.get('/api/risk') }
export function getRiskStats(): Promise<RiskStats> { return request.get('/risk/stats') }
