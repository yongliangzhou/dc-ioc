import request from './request'

/**
 * 风险项 —— 字段名严格对齐后端 crud/risk.py::_to_dict
 *
 * 历史坑：这里曾用 { title, category, severity, probability, mitigation, status }，
 * 与后端实际返回的 { risk, cat, level, prob, impact, ctrl, closed } 完全对不上，
 * 导致列表「标题 / 类别 / 严重性 / 可能性」四列恒为空，
 * 「状态」因 r.status 不存在而永远显示"已缓解"。已按后端字段修正。
 */
export interface RiskView {
  id: number
  code: string
  /** 风险描述 */
  risk: string
  /** 类别 */
  cat: string
  /** 可能性 1=低 2=中 3=高 4=极高 */
  prob: number
  /** 影响 1=低 2=中 3=高 4=极高 */
  impact: number
  /** 风险等级：低 / 中 / 高（后端由 prob × impact 派生） */
  level: string
  /** 缓解措施 */
  ctrl: string | null
  owner: string
  /** 0=未关闭，1=已缓解 */
  closed: number
}

export interface RiskStats {
  /** 总数（前端由 high + mid + low 派生，后端不直接给） */
  total: number
  /** 未关闭 = total - closed */
  open: number
  /** 已缓解 = closed */
  mitigated: number
  /** 高风险数（与后端 high 同义，保留别名便于 KPI 语义化） */
  critical: number
  high: number
  mid: number
  low: number
}

// 后端动态 JSON 的宽松原始记录类型 (字段为 unknown, 经由 Number()/String() 收窄)
interface RawItem {
  [k: string]: unknown
}

/**
 * 与后端 crud/risk.py::_level 保持一致的等级判定。
 * 后端的 level 是写入时派生的，若历史数据 level 缺失或过时，
 * 前端用同一公式重算，保证矩阵配色与后端口径一致。
 */
export function riskLevelOf(prob: number, impact: number): '高' | '中' | '低' {
  const score = (prob || 1) * (impact || 1)
  if (score >= 12) return '高'
  if (score >= 6) return '中'
  return '低'
}

/** 归一化后端原始记录：字段收窄为类型声明的形状，避免后端口径漂移把 UI 打空 */
function mapRisk(raw: RawItem): RiskView {
  const prob = Number(raw.prob ?? raw.probability) || 1
  const impact = Number(raw.impact) || 1
  return {
    id: Number(raw.id) || 0,
    code: String(raw.code ?? ''),
    risk: String(raw.risk ?? raw.title ?? ''),
    cat: String(raw.cat ?? raw.category ?? ''),
    prob,
    impact,
    level: String(raw.level ?? riskLevelOf(prob, impact)),
    ctrl: raw.ctrl == null ? null : String(raw.ctrl),
    owner: String(raw.owner ?? ''),
    closed: Number(raw.closed) || 0,
  }
}

// 后端 GET /api/ops/risk 返回 { stats: {high, mid, low, closed}, matrix: [...] }
export async function getRisks(): Promise<RiskView[]> {
  const resp = await request.get<unknown, RawItem>('/api/ops/risk')
  const list = Array.isArray(resp.matrix) ? (resp.matrix as RawItem[]) : []
  return list.map(mapRisk)
}

// ---- 风险项写操作 ----
export interface RiskCreate {
  risk: string
  cat?: string
  prob?: number
  impact?: number
  ctrl?: string
  owner?: string
  code?: string
  closed?: number
}
export function createRisk(payload: RiskCreate): Promise<unknown> {
  return request.post('/api/ops/risk', payload)
}
export function updateRisk(id: number, payload: Partial<RiskCreate>): Promise<unknown> {
  return request.put(`/api/ops/risk/${id}`, payload)
}
export function deleteRisk(id: number): Promise<unknown> {
  return request.delete(`/api/ops/risk/${id}`)
}

// 基于采集数据 + 活跃告警自动分析生成风险提示 (草稿)
export function analyzeRisk(): Promise<unknown> {
  return request.post('/api/ops/risk/analyze', {})
}

/** 后端 stats 的 {high, mid, low, closed} → 前端展示口径 */
function mapStats(raw: RawItem | undefined): RiskStats {
  const s = raw ?? {}
  const high = Number(s.high) || 0
  const mid = Number(s.mid) || 0
  const low = Number(s.low) || 0
  const closed = Number(s.closed) || 0
  const total = high + mid + low
  return {
    total,
    open: total - closed,
    mitigated: closed,
    critical: high,
    high,
    mid,
    low,
  }
}

export async function getRiskStats(): Promise<RiskStats> {
  const resp = await request.get<unknown, RawItem>('/api/ops/risk')
  return mapStats(resp.stats as RawItem | undefined)
}

export interface RiskOverview {
  risks: RiskView[]
  stats: RiskStats
}

/**
 * 一次请求拿到「风险列表 + 统计」。
 * 原页面分别调 getRisks() 和 getRiskStats()，对同一个 /api/ops/risk 发两次请求。
 */
export async function getRiskOverview(): Promise<RiskOverview> {
  const resp = await request.get<unknown, RawItem>('/api/ops/risk')
  const list = Array.isArray(resp.matrix) ? (resp.matrix as RawItem[]) : []
  return {
    risks: list.map(mapRisk),
    stats: mapStats(resp.stats as RawItem | undefined),
  }
}
