import request from '@/api/request'

/** 阶段四 · 可配置个人仪表盘 (P4-4)。
 *
 * 复用既有 `/api/ops/graphic-config/{kind}` 的 JSON 覆盖层机制 (ADR-0004),
 * kind=dashboard, 布局存于 `payload.params.layout`, 不新增表。
 * 后端不可达时回退 localStorage 并显式标注来源。
 */
export const DASHBOARD_KIND = 'dashboard'
export const STORAGE_KEY = 'dc_ioc_dashboard_layout'

export const DASHBOARD_SECTIONS = [
  { id: 'kpi', labelZh: 'KPI 指标', labelEn: 'KPIs' },
  { id: 'trends', labelZh: '关键趋势', labelEn: 'Trends' },
  { id: 'alarms', labelZh: '实时告警', labelEn: 'Alarms' },
  { id: 'hvac', labelZh: '制冷系统', labelEn: 'Cooling' },
  { id: 'health', labelZh: '业务域健康度', labelEn: 'Health' },
  { id: 'campus', labelZh: '校区总览', labelEn: 'Campuses' },
] as const

export type SectionId = (typeof DASHBOARD_SECTIONS)[number]['id']

export interface LayoutItem {
  id: SectionId
  visible: boolean
  order: number
}

export function defaultLayout(): LayoutItem[] {
  return DASHBOARD_SECTIONS.map((s, i) => ({ id: s.id, visible: true, order: i }))
}

/** 防御式解析: 非法/残缺配置一律按默认值补齐, 未知 id 丢弃。 */
export function normalizeLayout(input: unknown): LayoutItem[] {
  const base = defaultLayout()
  if (!Array.isArray(input)) return base
  const known = new Set<string>(DASHBOARD_SECTIONS.map((s) => s.id))
  const valid = input.filter(
    (x): x is Record<string, unknown> =>
      !!x && typeof x === 'object' && known.has(String((x as Record<string, unknown>).id)),
  )
  const overrides = new Map<string, { visible?: unknown; order?: unknown }>()
  for (const item of valid) overrides.set(String(item.id), item)
  const merged = base.map((b) => {
    const o = overrides.get(b.id)
    const visible = o && typeof o.visible === 'boolean' ? (o.visible as boolean) : true
    const order =
      o && typeof o.order === 'number' && Number.isFinite(o.order) ? (o.order as number) : b.order
    return { id: b.id, visible, order }
  })
  return merged.sort((a, b) => a.order - b.order).map((x, i) => ({ ...x, order: i }))
}

export function moveSection(layout: LayoutItem[], id: SectionId, delta: number): LayoutItem[] {
  const list = normalizeLayout(layout)
  const idx = list.findIndex((x) => x.id === id)
  const target = idx + delta
  if (idx < 0 || target < 0 || target >= list.length) return list
  const copy = [...list]
  ;[copy[idx], copy[target]] = [copy[target], copy[idx]]
  return copy.map((x, i) => ({ ...x, order: i }))
}

export function toggleSection(layout: LayoutItem[], id: SectionId): LayoutItem[] {
  return normalizeLayout(layout).map((x) => (x.id === id ? { ...x, visible: !x.visible } : x))
}

export function isVisible(layout: LayoutItem[], id: SectionId): boolean {
  return normalizeLayout(layout).find((x) => x.id === id)?.visible ?? true
}

export function sectionStyle(layout: LayoutItem[], id: SectionId): { order: number } {
  return { order: normalizeLayout(layout).find((x) => x.id === id)?.order ?? 0 }
}

export function isDefaultLayout(layout: LayoutItem[]): boolean {
  const d = defaultLayout()
  const n = normalizeLayout(layout)
  return d.every((x, i) => n[i].id === x.id && n[i].visible === true && n[i].order === i)
}

function payloadOf(layout: LayoutItem[]) {
  return { nodes: [], edges: [], params: { layout }, removed: [] }
}

export interface LoadedLayout {
  layout: LayoutItem[]
  source: 'server' | 'local' | 'default'
}

export async function loadDashboardLayout(): Promise<LoadedLayout> {
  try {
    const r = await request.get<{ payload?: { params?: { layout?: unknown } } }>(
      `/api/ops/graphic-config/${DASHBOARD_KIND}`,
    )
    const raw = r.data?.payload?.params?.layout
    if (raw !== undefined) {
      return { layout: normalizeLayout(raw), source: 'server' }
    }
  } catch (err) {
    console.warn('[dashboard-layout] 后端不可达:', err)
  }
  try {
    const cached = localStorage.getItem(STORAGE_KEY)
    if (cached) return { layout: normalizeLayout(JSON.parse(cached)), source: 'local' }
  } catch (err) {
    console.warn('[dashboard-layout] 本地布局解析失败:', err)
  }
  return { layout: defaultLayout(), source: 'default' }
}

export type SaveResult = 'server' | 'local' | 'failed'

export async function saveDashboardLayout(layout: LayoutItem[]): Promise<SaveResult> {
  const normalized = normalizeLayout(layout)
  try {
    await request.put(`/api/ops/graphic-config/${DASHBOARD_KIND}`, {
      title: 'Dashboard Layout',
      payload: payloadOf(normalized),
    })
    return 'server'
  } catch (err) {
    console.warn('[dashboard-layout] 保存到后端失败, 落本地:', err)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(normalized))
      return 'local'
    } catch {
      return 'failed'
    }
  }
}

export async function resetDashboardLayout(): Promise<SaveResult> {
  try {
    await request.delete(`/api/ops/graphic-config/${DASHBOARD_KIND}`)
  } catch (err) {
    console.warn('[dashboard-layout] 清除服务端布局失败:', err)
  }
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    /* noop */
  }
  return saveDashboardLayout(defaultLayout())
}
