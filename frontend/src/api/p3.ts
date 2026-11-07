import request from '@/api/request'

/** 阶段三 API 汇总: IPAM / 自动发现 / 采购盘点 / 自定义字段。 */
const IPAM = '/api/ipam'
const DISCOVERY = '/api/ops/discovery'
const PROCUREMENT = '/api/ops/procurement'
const STOCKTAKE = '/api/ops/stocktake'
const CUSTOM = '/api/ops/custom-fields'

export interface P3Row {
  id: number
  [key: string]: unknown
}

export interface SubnetRow extends P3Row {
  cidr: string
  vlan_id: number | null
  gateway: string
  total: number
  used: number
  available: number
  utilization_pct: number
}

export interface CandidateRow extends P3Row {
  ip: string
  open_ports: number[]
  status: 'pending' | 'confirmed' | 'rejected'
  matched_ci: string
}

export interface CustomFieldRow extends P3Row {
  key: string
  label_zh: string
  label_en: string
  type: 'text' | 'number' | 'date' | 'select'
  options: string[]
  required: boolean
  applies_to: string
}

async function get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
  const r = await request.get<T>(url, { params })
  return r.data
}

export const p3Api = {
  // ---- IPAM ----
  vlans: () => get<P3Row[]>(`${IPAM}/vlans`),
  addVlan: (body: { vlan_id: number; name?: string; site?: string; description?: string }) =>
    request.post<P3Row>(`${IPAM}/vlans`, body).then((r) => r.data),
  delVlan: (id: number) => request.delete(`${IPAM}/vlans/${id}`).then((r) => r.data),
  subnets: () => get<SubnetRow[]>(`${IPAM}/subnets`),
  addSubnet: (body: { cidr: string; vlan_id?: number | null; gateway?: string }) =>
    request.post<P3Row>(`${IPAM}/subnets`, body).then((r) => r.data),
  delSubnet: (id: number) => request.delete(`${IPAM}/subnets/${id}`).then((r) => r.data),
  allocate: (id: number, deviceCi = '') =>
    request
      .post<P3Row>(`${IPAM}/subnets/${id}/allocate`, null, {
        params: { device_ci: deviceCi },
      })
      .then((r) => r.data),
  addresses: (subnetId?: number) =>
    get<P3Row[]>(`${IPAM}/addresses`, subnetId ? { subnet_id: subnetId } : undefined),
  addAddress: (body: { address: string; subnet_id?: number; device_ci?: string }) =>
    request.post<P3Row>(`${IPAM}/addresses`, body).then((r) => r.data),
  delAddress: (id: number) => request.delete(`${IPAM}/addresses/${id}`).then((r) => r.data),
  ipamStats: () => get<Record<string, number>>(`${IPAM}/stats`),

  // ---- 自动发现 ----
  candidates: (status?: string) =>
    get<CandidateRow[]>(`${DISCOVERY}/candidates`, status ? { status } : undefined),
  scan: (body: { cidr: string; ports: number[]; concurrency?: number }) =>
    request
      .post<{ scanned: number; created: number; updated: number }>(`${DISCOVERY}/scan`, body)
      .then((r) => r.data),
  confirm: (id: number, matchedCi = '') =>
    request
      .post<CandidateRow>(`${DISCOVERY}/candidates/${id}/confirm`, { matched_ci: matchedCi })
      .then((r) => r.data),
  reject: (id: number) =>
    request.post<CandidateRow>(`${DISCOVERY}/candidates/${id}/reject`).then((r) => r.data),
  delCandidate: (id: number) => request.delete(`${DISCOVERY}/candidates/${id}`).then((r) => r.data),

  // ---- 采购 / 盘点 ----
  orders: () => get<P3Row[]>(`${PROCUREMENT}/orders`),
  addOrder: (body: Record<string, unknown>) =>
    request.post<P3Row>(`${PROCUREMENT}/orders`, body).then((r) => r.data),
  delOrder: (id: number) => request.delete(`${PROCUREMENT}/orders/${id}`).then((r) => r.data),
  expiring: (days = 30) => get<P3Row[]>(`${PROCUREMENT}/expiring`, { days }),
  tasks: () => get<P3Row[]>(`${STOCKTAKE}/tasks`),
  addTask: (body: { name: string; scope?: string }) =>
    request.post<P3Row>(`${STOCKTAKE}/tasks`, body).then((r) => r.data),
  items: (taskId: number) => get<P3Row[]>(`${STOCKTAKE}/tasks/${taskId}/items`),
  addItem: (
    taskId: number,
    body: { asset_ci: string; result?: string; expected_location?: string },
  ) => request.post<P3Row>(`${STOCKTAKE}/tasks/${taskId}/items`, body).then((r) => r.data),
  report: (taskId: number, expectedCis: string[] = []) =>
    get<Record<string, unknown>>(`${STOCKTAKE}/tasks/${taskId}/report`, {
      expected_cis: expectedCis.join(','),
    }),

  // ---- 自定义字段 ----
  customFields: () => get<CustomFieldRow[]>(CUSTOM),
  addCustomField: (body: Record<string, unknown>) =>
    request.post<CustomFieldRow>(CUSTOM, body).then((r) => r.data),
  delCustomField: (id: number) => request.delete(`${CUSTOM}/${id}`).then((r) => r.data),
  customValues: (equipmentId: number) =>
    get<{ equipment_id: number; values: Record<string, unknown> }>(
      `${CUSTOM}/values/${equipmentId}`,
    ),
  saveCustomValues: (equipmentId: number, values: Record<string, unknown>) =>
    request.put(`${CUSTOM}/values/${equipmentId}`, { values }).then((r) => r.data),
}
