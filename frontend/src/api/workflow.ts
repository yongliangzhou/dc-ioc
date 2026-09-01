import request from '@/api/request'

export type WType = 'incident' | 'problem' | 'change' | 'risk'
export type WStatus = 'new' | 'progress' | 'approval' | 'approved' | 'rejected' | 'closed'
export type WPriority = 'P1' | 'P2' | 'P3' | 'P4'
export type NodeStatus = 'approved' | 'rejected' | 'pending' | 'skipped'

export interface WNode {
  approver: string
  status: NodeStatus
  comment?: string
  at?: string
}
export interface WLog {
  user: string
  text: string
  at: string
}
export interface WorkflowItem {
  id: string
  type: WType
  title: string
  description: string
  priority: WPriority
  status: WStatus
  owner: string
  applicant: string
  createdAt: string
  updatedAt: string
  slaHours: number
  riskLevel?: 'high' | 'medium' | 'low'
  approval: WNode[]
  logs: WLog[]
  knowledgeLinks: string[]
}

export interface WorkflowListResp {
  items: WorkflowItem[]
}

export interface WorkflowTrendPoint {
  /** 该周周一, MM-DD */
  week: string
  created: number
  closed: number
}
export interface WorkflowStats {
  total: number
  open: number
  monthCreated: number
  monthClosed: number
  /** 平均解决时长(小时), 无已关闭流程时为 0 */
  avgResolve: number
  /** SLA 超时率百分比 (0-100) */
  breachRate: number
  byType: Record<string, number>
  byStatus: Record<string, number>
  byPriority: Record<string, number>
  trend: WorkflowTrendPoint[]
}

export const getWorkflows = () => request.get<unknown, WorkflowListResp>('/api/ops/workflows')
/** 服务端聚合统计(KPI + 分布 + 近 12 周趋势), 前端失败时回退本地计算 */
export const getWorkflowStats = () =>
  request.get<unknown, WorkflowStats>('/api/ops/workflows/stats')
export const createWorkflow = (data: Partial<WorkflowItem>) =>
  request.post<unknown, WorkflowItem>('/api/ops/workflows', data)
export const getWorkflow = (id: string) =>
  request.get<unknown, WorkflowItem>(`/api/ops/workflows/${id}`)
export const updateWorkflow = (id: string, patch: Partial<WorkflowItem>) =>
  request.put<unknown, WorkflowItem>(`/api/ops/workflows/${id}`, patch)
export const deleteWorkflow = (id: string) =>
  request.delete<unknown, void>(`/api/ops/workflows/${id}`)
export const advanceWorkflow = (id: string) =>
  request.post<unknown, WorkflowItem>(`/api/ops/workflows/${id}/advance`)
export const closeWorkflow = (id: string) =>
  request.post<unknown, WorkflowItem>(`/api/ops/workflows/${id}/close`)
export const reopenWorkflow = (id: string) =>
  request.post<unknown, WorkflowItem>(`/api/ops/workflows/${id}/reopen`)
export const approveNode = (
  id: string,
  nodeIndex: number,
  result: 'approved' | 'rejected',
  comment?: string,
) =>
  request.post<unknown, WorkflowItem>(`/api/ops/workflows/${id}/approve`, {
    node_index: nodeIndex,
    result,
    comment,
  })
export const addWorkflowLog = (id: string, text: string) =>
  request.post<unknown, WorkflowItem>(`/api/ops/workflows/${id}/logs`, { text })
export const linkKnowledge = (id: string, kbId: string) =>
  request.post<unknown, WorkflowItem>(`/api/ops/workflows/${id}/link`, { kb_id: kbId })
export const unlinkKnowledge = (id: string, kbId: string) =>
  request.delete<unknown, WorkflowItem>(`/api/ops/workflows/${id}/link/${kbId}`)
