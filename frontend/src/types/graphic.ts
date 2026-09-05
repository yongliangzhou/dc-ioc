/* ===== 统一图形编辑入口 (图形场景配置 + 加油记录) =====
 *
 * 冷源工艺流程 / 制冷链路 / 温度云图 / 10KV·0.4KV 一次系统图 / 配电链路 /
 * 柴发并机 / 储油示意 / 电池组拓扑 / 门禁平面 / 周界示意 / 消防平面 等图形页
 * 原先都是只读渲染, 没有编辑入口。
 *
 * 这里定义"场景覆盖层"契约: 后端按 kind 存一份 JSON, 页面渲染时把接口数据
 * 构成的节点清单与本覆盖层合并 —— 改名/改坐标/改参数 = 覆盖, removed 里的
 * id = 删除, 覆盖层里新增的 id = 用户自建节点。既有展示逻辑无需重写。
 */

/** 图形节点 (与页面节点按 id 对齐) */
export interface GraphicNode {
  id: string
  label: string
  type?: string
  x?: number | null
  y?: number | null
  status?: string
  params?: Record<string, string>
}

/** 图形连线 */
export interface GraphicEdge {
  id: string
  source: string
  target: string
  label?: string
}

/** 一份图形场景覆盖层 */
export interface GraphicScene {
  nodes: GraphicNode[]
  edges: GraphicEdge[]
  params: Record<string, string>
  removed: string[]
}

/** 后端返回的图形配置 (GET/PUT /api/ops/graphic-config/{kind}) */
export interface GraphicConfigPayload {
  kind: string
  title: string
  payload: GraphicScene
  updatedBy: string
  updatedAt: string | null
}

/** 加油(补油)记录 (储油系统 · 加油记录模块) */
export interface RefuelRecordItem {
  id: number
  no: string
  date: string
  tank: string
  amount: number
  before: number | null
  after: number | null
  vendor: string
  grade: string
  qc: string
  operator: string
  status: string
  note?: string
  createdBy?: string
  updatedBy?: string
  updatedAt?: string | null
}
