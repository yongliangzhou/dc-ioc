/* ===== 上架模拟器 (容量 What-if) ===== */

/** 推演请求体 (后端契约: POST /api/ops/capacity/what-if) */
export interface WhatIfRequest {
  /** 新增机柜数 1-500 */
  cabinets: number
  /** 单柜功率 kW 0.5-50 */
  kwPerCabinet: number
  /** 推演月数 6-36 */
  monthsHorizon: number
  /** 数据中心编码, 如 "DC1" */
  idcCode: string
}

/** 基线维度 (GET baseline) — 注意 id 为中文字符串, 前端直接展示, 不要按英文 key 匹配 */
export interface WhatIfBaselineDim {
  id: string
  used: number
  total: number
  unit: string
}

/** 基线响应 */
export interface WhatIfBaseline {
  dims: WhatIfBaselineDim[]
  rooms: Array<Record<string, unknown>>
  forecast: string
  knowledge: Record<string, unknown>
  /** real=真实数据 / generated=生成基线 */
  _source: 'real' | 'generated'
}

/** 推演后维度 */
export interface WhatIfResultDim {
  id: string
  unit: string
  usedNow: number
  usedAfter: number
  capacity: number
  pctNow: number
  pctAfter: number
  headroomPercent: number
  /** "YYYY-MM" | "now" (当前已超) | null (horizon 内到不了) */
  reach85Month: string | null
  reach100Month: string | null
  addedByRacks: number
}

/** 推演结果响应 */
export interface WhatIfResult {
  cabinets: number
  kwPerCabinet: number
  monthsHorizon: number
  source: string
  dims: WhatIfResultDim[]
  /** 瓶颈维度名 (与 dims[].id 同源) */
  bottleneck: string
  suggestions: string[]
}
