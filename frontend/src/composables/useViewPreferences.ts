import { computed, ref } from 'vue'
import request from '@/api/request'
import { useAuthStore } from '@/stores/modules/auth'

/**
 * 阶段 3 · 筛选视图保存（04 §6.2，复用 ADR-0004 的 JSON 覆盖层）。
 *
 * - `kind = fv:{username}:{pageId}`，把用户维度编进 kind，实现「个人视图」隔离，
 *   不新增表/端点；后端 `graphic_config.kind` 是 `String(64)`，超长自动加哈希后缀。
 * - 后端 `GraphicScene.params` 是 `Dict[str, str]`，视图数组以 JSON 字符串存于
 *   `params.views`，`params.defaultId` 存字符串。
 * - PUT 限 admin/operator；viewer 或后端不可达时回退 localStorage，返回 `source`
 *   供调用方用 `DataBadge` 标注「仅本机保存」。
 * - 所有外部输入经 `normalize*`：未知字段、非法类型、超量视图一律丢弃或补齐。
 */
export const MAX_VIEWS = 10
const KIND_LIMIT = 64

export interface ColumnPreference {
  key: string
  visible: boolean
  order: number
}

export interface FilterView {
  id: string
  name: string
  filters: Record<string, string | number>
  columns: ColumnPreference[]
  page?: number
  size?: number
}

export interface ViewState {
  views: FilterView[]
  defaultId: string | null
}

export type ViewSource = 'server' | 'local' | 'default'
export type SaveResult = 'server' | 'local' | 'failed'

export interface LoadedViews {
  state: ViewState
  source: ViewSource
}

const isRecord = (x: unknown): x is Record<string, unknown> =>
  !!x && typeof x === 'object' && !Array.isArray(x)

/** FNV-1a 32 位：稳定、无依赖，用于压缩超长 kind 且保持唯一性。 */
function fnv1a(s: string): string {
  let h = 0x811c9dc5
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return (h >>> 0).toString(16).padStart(8, '0')
}

export function viewKind(pageId: string, username: string): string {
  const safeUser = username.replace(/[^\w.-]/g, '_')
  const safePage = pageId.replace(/[^\w.-]/g, '_')
  const raw = `fv:${safeUser}:${safePage}`
  if (raw.length <= KIND_LIMIT) return raw
  return `fv:${safeUser.slice(0, 16)}:${safePage.slice(0, 24)}:${fnv1a(raw)}`
}

export function viewStorageKey(pageId: string, username: string): string {
  return `dc_ioc_filter_views_${viewKind(pageId, username).replace(/[^\w]/g, '_')}`
}

export function emptyViewState(): ViewState {
  return { views: [], defaultId: null }
}

function normalizeColumns(input: unknown): ColumnPreference[] {
  if (!Array.isArray(input)) return []
  const seen = new Set<string>()
  const out: ColumnPreference[] = []
  input.forEach((raw, i) => {
    if (!isRecord(raw)) return
    const key = typeof raw.key === 'string' ? raw.key.slice(0, 64) : ''
    if (!key || seen.has(key)) return
    seen.add(key)
    out.push({
      key,
      visible: typeof raw.visible === 'boolean' ? raw.visible : true,
      order: typeof raw.order === 'number' && Number.isFinite(raw.order) ? raw.order : i,
    })
  })
  return out.sort((a, b) => a.order - b.order).map((x, i) => ({ ...x, order: i }))
}

function normalizeFilters(input: unknown): Record<string, string | number> {
  if (!isRecord(input)) return {}
  const out: Record<string, string | number> = {}
  for (const [key, value] of Object.entries(input)) {
    if (typeof value === 'string' && value.length <= 200) out[key] = value
    else if (typeof value === 'number' && Number.isFinite(value)) out[key] = value
  }
  return out
}

export function normalizeView(raw: unknown): FilterView | null {
  if (!isRecord(raw)) return null
  const id = typeof raw.id === 'string' && raw.id ? raw.id.slice(0, 64) : ''
  const name = typeof raw.name === 'string' && raw.name.trim() ? raw.name.trim().slice(0, 40) : ''
  if (!id || !name) return null
  const view: FilterView = {
    id,
    name,
    filters: normalizeFilters(raw.filters),
    columns: normalizeColumns(raw.columns),
  }
  if (typeof raw.page === 'number' && Number.isFinite(raw.page) && raw.page >= 1) {
    view.page = Math.floor(raw.page)
  }
  if (typeof raw.size === 'number' && Number.isFinite(raw.size) && raw.size >= 1) {
    view.size = Math.floor(raw.size)
  }
  return view
}

/** 后端返回 JSON 字符串，localStorage 里可能是数组，两者都兼容。 */
export function parseViews(raw: unknown): unknown[] {
  if (Array.isArray(raw)) return raw
  if (typeof raw === 'string') {
    try {
      const parsed: unknown = JSON.parse(raw)
      return Array.isArray(parsed) ? parsed : []
    } catch {
      return []
    }
  }
  return []
}

export function normalizeViewState(input: unknown): ViewState {
  if (!isRecord(input)) return emptyViewState()
  const views = parseViews(input.views)
    .map(normalizeView)
    .filter((v): v is FilterView => v !== null)
    .slice(0, MAX_VIEWS)
  const ids = new Set(views.map((v) => v.id))
  const defaultId =
    typeof input.defaultId === 'string' && ids.has(input.defaultId)
      ? input.defaultId
      : (views[0]?.id ?? null)
  return { views, defaultId }
}

export function newViewId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `v_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
}

export function upsertView(state: ViewState, view: FilterView): ViewState {
  const next = normalizeView(view)
  if (!next) return normalizeViewState(state)
  const base = normalizeViewState(state)
  const views = base.views.some((v) => v.id === next.id)
    ? base.views.map((v) => (v.id === next.id ? next : v))
    : [...base.views, next].slice(-MAX_VIEWS)
  const ids = new Set(views.map((v) => v.id))
  return {
    views,
    defaultId: base.defaultId && ids.has(base.defaultId) ? base.defaultId : (views[0]?.id ?? null),
  }
}

export function removeView(state: ViewState, id: string): ViewState {
  const base = normalizeViewState(state)
  const views = base.views.filter((v) => v.id !== id)
  return { views, defaultId: base.defaultId === id ? (views[0]?.id ?? null) : base.defaultId }
}

export function renameView(state: ViewState, id: string, name: string): ViewState {
  const base = normalizeViewState(state)
  const clean = String(name).trim().slice(0, 40)
  return {
    ...base,
    views: base.views.map((v) => (v.id === id && clean ? { ...v, name: clean } : v)),
  }
}

function payloadOf(state: ViewState) {
  return {
    nodes: [],
    edges: [],
    removed: [],
    params: {
      views: JSON.stringify(state.views),
      defaultId: state.defaultId ?? '',
    },
  }
}

export async function loadViewPreferences(pageId: string, username: string): Promise<LoadedViews> {
  const kind = viewKind(pageId, username)
  const key = viewStorageKey(pageId, username)
  try {
    const r = await request.get<{
      payload?: { params?: { views?: unknown; defaultId?: unknown } }
    }>(`/api/ops/graphic-config/${encodeURIComponent(kind)}`)
    const params = r.data?.payload?.params
    if (params && params.views !== undefined) {
      return {
        state: normalizeViewState({ views: params.views, defaultId: params.defaultId }),
        source: 'server',
      }
    }
  } catch (err) {
    console.warn('[view-preferences] 后端不可达:', err)
  }
  try {
    const cached = localStorage.getItem(key)
    if (cached) return { state: normalizeViewState(JSON.parse(cached)), source: 'local' }
  } catch (err) {
    console.warn('[view-preferences] 本地视图解析失败:', err)
  }
  return { state: emptyViewState(), source: 'default' }
}

export async function saveViewPreferences(
  pageId: string,
  username: string,
  state: ViewState,
): Promise<SaveResult> {
  const kind = viewKind(pageId, username)
  const key = viewStorageKey(pageId, username)
  const normalized = normalizeViewState(state)
  try {
    await request.put(`/api/ops/graphic-config/${encodeURIComponent(kind)}`, {
      title: `Filter views: ${pageId}`.slice(0, 128),
      payload: payloadOf(normalized),
    })
    try {
      localStorage.removeItem(key)
    } catch {
      /* noop */
    }
    return 'server'
  } catch (err) {
    console.warn('[view-preferences] 保存到后端失败, 落本地:', err)
    try {
      localStorage.setItem(key, JSON.stringify(normalized))
      return 'local'
    } catch {
      return 'failed'
    }
  }
}

export async function resetViewPreferences(pageId: string, username: string): Promise<SaveResult> {
  const kind = viewKind(pageId, username)
  try {
    await request.delete(`/api/ops/graphic-config/${encodeURIComponent(kind)}`)
  } catch (err) {
    console.warn('[view-preferences] 清除服务端视图失败:', err)
  }
  try {
    localStorage.removeItem(viewStorageKey(pageId, username))
  } catch {
    /* noop */
  }
  return saveViewPreferences(pageId, username, emptyViewState())
}

/** 组件层入口：自动取当前用户，暴露响应式 state / source / saving。 */
export function useViewPreferences(pageId: string) {
  const auth = useAuthStore()
  const username = computed(() => auth.user?.username || 'anonymous')
  const state = ref<ViewState>(emptyViewState())
  const source = ref<ViewSource>('default')
  const saving = ref(false)

  async function load(): Promise<void> {
    const loaded = await loadViewPreferences(pageId, username.value)
    state.value = loaded.state
    source.value = loaded.source
  }

  async function save(next: ViewState): Promise<SaveResult> {
    saving.value = true
    try {
      const result = await saveViewPreferences(pageId, username.value, next)
      state.value = normalizeViewState(next)
      source.value = result === 'server' ? 'server' : result === 'local' ? 'local' : source.value
      return result
    } finally {
      saving.value = false
    }
  }

  async function reset(): Promise<SaveResult> {
    saving.value = true
    try {
      state.value = emptyViewState()
      return await resetViewPreferences(pageId, username.value)
    } finally {
      saving.value = false
    }
  }

  return { state, source, saving, load, save, reset, username }
}
