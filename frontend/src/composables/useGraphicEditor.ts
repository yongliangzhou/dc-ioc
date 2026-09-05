/**
 * useGraphicEditor — 统一图形编辑入口的状态机
 *
 * 背景: 冷源工艺流程 / 制冷链路 / 温度云图 / 10KV·0.4KV 一次系统图 / 配电链路 /
 * 柴发并机 / 储油示意 / 电池组拓扑 / 门禁平面 / 周界示意 / 消防平面 等图形页
 * 都是"接口数据 + 页面内写死坐标"的只读渲染, 没有编辑入口。
 *
 * 方案: 后端按 kind 存一份「场景覆盖层」JSON, 页面渲染时把接口数据构成的节点
 * 清单与本覆盖层合并 ——
 *   · 覆盖层节点 id 与页面节点一致  → 改名/改坐标/改状态/改参数(覆盖)
 *   · 覆盖层节点 id 页面数据里没有  → 用户新增的节点
 *   · removed 中的 id              → 用户删除的节点
 * 这样既有展示逻辑(模板/坐标计算)完全不用重写, 编辑结果又能真实生效与持久化。
 *
 * 用法:
 *   const editor = useGraphicEditor('power-lv-schematic', { title: '0.4KV 低压一次系统图' })
 *   const feederNodesView = computed(() =>
 *     editor.apply(feederNodes.value, {
 *       toNode: (n) => ({ id: n.id, label: n.label, type: '馈线', x: n.x, y: n.y, status: n.breaker }),
 *       fromNode: (g, base) => ({ ...(base as BreakerNode), id: g.id, label: g.label || g.id,
 *                                 x: g.x ?? 0, y: g.y ?? 0, breaker: g.status || '分闸' }),
 *     }))
 *   <GraphicEditDrawer v-model="editOpen" :editor="editor" :defaults="..." />
 */
import {
  computed,
  getCurrentInstance,
  onMounted,
  ref,
  watch,
  type ComputedRef,
  type Ref,
} from 'vue'
import { deleteGraphicConfig, getGraphicConfig, saveGraphicConfig } from '@/api'
import type { GraphicEdge, GraphicNode, GraphicScene } from '@/types/graphic'
import { toErrorMessage } from './useAsyncPage'

/** 后端不可达时的本地兜底存储前缀 (明确标注, 不假装已提交) */
const LS_PREFIX = 'dc-ioc:graphic-scene:'

export function emptyScene(): GraphicScene {
  return { nodes: [], edges: [], params: {}, removed: [] }
}

/** 容错归一化: 后端/本地 JSON 可能缺字段 */
export function normalizeScene(raw: unknown): GraphicScene {
  const p = (raw ?? {}) as Partial<GraphicScene>
  const nodes = Array.isArray(p.nodes) ? p.nodes : []
  return {
    nodes: nodes.map((n) => ({
      id: String(n?.id ?? ''),
      label: String(n?.label ?? ''),
      type: String(n?.type ?? ''),
      x: n?.x == null ? null : Number(n.x),
      y: n?.y == null ? null : Number(n.y),
      status: String(n?.status ?? ''),
      params: (n?.params ?? {}) as Record<string, string>,
    })),
    edges: (Array.isArray(p.edges) ? p.edges : []).map((e) => ({
      id: String(e?.id ?? ''),
      source: String(e?.source ?? ''),
      target: String(e?.target ?? ''),
      label: String(e?.label ?? ''),
    })),
    params: (p.params ?? {}) as Record<string, string>,
    removed: (Array.isArray(p.removed) ? p.removed : []).map(String),
  }
}

/** 默认节点 + 覆盖项 → 最终节点 (覆盖项留空字段回退到默认值) */
export function mergeNode(base: GraphicNode, ov: GraphicNode): GraphicNode {
  return {
    id: base.id,
    label: ov.label || base.label,
    type: ov.type || base.type || '',
    x: ov.x ?? base.x ?? null,
    y: ov.y ?? base.y ?? null,
    status: ov.status || base.status || '',
    params: { ...(base.params ?? {}), ...(ov.params ?? {}) },
  }
}

/** 页面节点 T ↔ 通用 GraphicNode 的双向映射 */
export interface NodeAdapter<T> {
  /** 页面节点 → 通用节点 (id 用于与覆盖层对齐) */
  toNode: (item: T) => GraphicNode
  /** 通用节点 → 页面节点 (覆盖/新增后回写给模板渲染) */
  fromNode: (node: GraphicNode, base?: T) => T
}

/** 合并「页面原始节点清单 + 场景覆盖层」→ 最终渲染清单 */
export function applyScene<T>(base: T[], scene: GraphicScene, adapter: NodeAdapter<T>): T[] {
  const removed = new Set(scene.removed ?? [])
  const overrides = new Map((scene.nodes ?? []).map((n) => [n.id, n]))
  const out: T[] = []
  const baseIds = new Set<string>()
  for (const item of base) {
    const bn = adapter.toNode(item)
    baseIds.add(bn.id)
    if (removed.has(bn.id)) continue
    const ov = overrides.get(bn.id)
    out.push(ov ? adapter.fromNode(mergeNode(bn, ov), item) : item)
  }
  // 用户自建节点: 覆盖层里 id 不在页面数据中的条目
  for (const n of scene.nodes ?? []) {
    if (baseIds.has(n.id) || removed.has(n.id)) continue
    out.push(adapter.fromNode(n))
  }
  return out
}

export interface GraphicEditorApi {
  kind: string
  scene: Ref<GraphicScene>
  loading: Ref<boolean>
  saving: Ref<boolean>
  error: Ref<string>
  dirty: Ref<boolean>
  /** 后端不可达: 编辑仅保存在浏览器本地, 必须在 UI 上显式提示 */
  usingFallback: Ref<boolean>
  updatedBy: Ref<string>
  updatedAt: Ref<string | null>
  hasOverrides: ComputedRef<boolean>
  reload: () => Promise<void>
  save: () => Promise<boolean>
  reset: () => Promise<boolean>
  apply: <T>(base: T[], adapter: NodeAdapter<T>) => T[]
  upsertNode: (node: GraphicNode) => void
  removeNode: (id: string, isCustom: boolean) => void
  restoreNode: (id: string) => void
  setEdge: (edge: GraphicEdge) => void
  removeEdge: (id: string) => void
  setParam: (key: string, value: string) => void
  removeParam: (key: string) => void
  getParam: (key: string, fallback?: string) => string
  /** 用户新增的节点 (覆盖层里有、页面默认数据里没有的条目), 供硬编码 SVG 页面叠加渲染 */
  customNodes: (defaults: GraphicNode[]) => GraphicNode[]
  /** 该 id 是否被用户删除 (硬编码节点无法从 v-for 里消失, 只能按此标记 v-if 隐藏) */
  isHidden: (id: string) => boolean
  /** 取覆盖后的名称/状态/坐标/参数, 无覆盖则返回页面默认值 */
  labelOf: (id: string, fallback: string) => string
  statusOf: (id: string, fallback: string) => string
  coordXOf: (id: string, fallback: number) => number
  coordYOf: (id: string, fallback: number) => number
  paramOf: (id: string, key: string, fallback?: string) => string
}

function readLocal(kind: string): GraphicScene | null {
  try {
    const raw = localStorage.getItem(LS_PREFIX + kind)
    return raw ? normalizeScene(JSON.parse(raw)) : null
  } catch {
    return null
  }
}

function writeLocal(kind: string, scene: GraphicScene | null) {
  try {
    if (!scene) localStorage.removeItem(LS_PREFIX + kind)
    else localStorage.setItem(LS_PREFIX + kind, JSON.stringify(scene))
  } catch {
    /* 隐私模式下 localStorage 不可用: 忽略, 由后端保存兜底 */
  }
}

export interface UseGraphicEditorOptions {
  /** 挂载后自动拉取已保存配置, 默认 true */
  autoLoad?: boolean
  /** 保存到后端的图形标题 (用于 /api/ops/graphic-config 列表) */
  title?: string
}

export function useGraphicEditor(
  kind: string,
  options: UseGraphicEditorOptions = {},
): GraphicEditorApi {
  const { autoLoad = true, title = '' } = options
  const scene = ref<GraphicScene>(emptyScene())
  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')
  const dirty = ref(false)
  const usingFallback = ref(false)
  const updatedBy = ref('')
  const updatedAt = ref<string | null>(null)

  // 任何编辑都标记为未保存 (首次拉取/保存导致的写入不算脏)
  let silent = false
  watch(
    scene,
    () => {
      if (!silent) dirty.value = true
    },
    { deep: true },
  )
  function applySilent(fn: () => void) {
    silent = true
    try {
      fn()
    } finally {
      silent = false
    }
  }

  async function reload() {
    loading.value = true
    error.value = ''
    try {
      const res = await getGraphicConfig(kind)
      applySilent(() => {
        scene.value = normalizeScene(res?.payload)
      })
      updatedBy.value = res?.updatedBy || ''
      updatedAt.value = res?.updatedAt || null
      usingFallback.value = false
      dirty.value = false
    } catch (e) {
      // 后端不可达/未授权: 不阻塞页面, 退回本地兜底并显式标注
      const local = readLocal(kind)
      applySilent(() => {
        scene.value = local ?? emptyScene()
      })
      usingFallback.value = true
      error.value = toErrorMessage(e)
      dirty.value = false
    } finally {
      loading.value = false
    }
  }

  /** 保存覆盖层到后端; 失败则落本地并在 UI 上标注"仅本地生效" */
  async function save() {
    saving.value = true
    error.value = ''
    try {
      const res = await saveGraphicConfig(kind, title, scene.value)
      updatedBy.value = res?.updatedBy || ''
      updatedAt.value = res?.updatedAt || null
      usingFallback.value = false
      dirty.value = false
      writeLocal(kind, null)
      return true
    } catch (e) {
      writeLocal(kind, scene.value)
      usingFallback.value = true
      error.value = toErrorMessage(e)
      return false
    } finally {
      saving.value = false
    }
  }

  /** 清空本图形的全部编辑, 页面回到默认渲染 */
  async function reset() {
    saving.value = true
    error.value = ''
    try {
      await deleteGraphicConfig(kind)
      applySilent(() => {
        scene.value = emptyScene()
      })
      writeLocal(kind, null)
      usingFallback.value = false
      dirty.value = false
      return true
    } catch (e) {
      // 404 (本就没有配置) 视为成功
      const msg = toErrorMessage(e)
      if (/不存在|404/.test(msg)) {
        applySilent(() => {
          scene.value = emptyScene()
        })
        dirty.value = false
        return true
      }
      error.value = msg
      return false
    } finally {
      saving.value = false
    }
  }

  function apply<T>(base: T[], adapter: NodeAdapter<T>): T[] {
    return applyScene(base, scene.value, adapter)
  }

  function upsertNode(node: GraphicNode) {
    const idx = scene.value.nodes.findIndex((n) => n.id === node.id)
    if (idx >= 0) scene.value.nodes[idx] = { ...node }
    else scene.value.nodes.push({ ...node })
    // 若之前被删除过, 重新加回来
    scene.value.removed = scene.value.removed.filter((id) => id !== node.id)
  }

  function removeNode(id: string, isCustom = false) {
    if (isCustom) {
      scene.value.nodes = scene.value.nodes.filter((n) => n.id !== id)
      return
    }
    // 页面自带节点: 记入 removed (页面数据每次刷新都会带回它, 只能显式排除)
    scene.value.nodes = scene.value.nodes.filter((n) => n.id !== id)
    if (!scene.value.removed.includes(id)) scene.value.removed.push(id)
  }

  function restoreNode(id: string) {
    scene.value.removed = scene.value.removed.filter((r) => r !== id)
  }

  function setEdge(edge: GraphicEdge) {
    const idx = scene.value.edges.findIndex((e) => e.id === edge.id)
    if (idx >= 0) scene.value.edges[idx] = { ...edge }
    else scene.value.edges.push({ ...edge })
  }

  function removeEdge(id: string) {
    scene.value.edges = scene.value.edges.filter((e) => e.id !== id)
  }

  function setParam(key: string, value: string) {
    scene.value.params = { ...scene.value.params, [key]: value }
  }

  function removeParam(key: string) {
    const next = { ...scene.value.params }
    delete next[key]
    scene.value.params = next
  }

  function getParam(key: string, fallback = '') {
    const v = scene.value.params?.[key]
    return v == null || v === '' ? fallback : String(v)
  }

  /** 用户新增的节点: 覆盖层里有、页面默认数据里没有 */
  function customNodes(defaults: GraphicNode[]): GraphicNode[] {
    const ids = new Set(defaults.map((d) => d.id))
    const removed = new Set(scene.value.removed ?? [])
    return scene.value.nodes.filter((n) => !ids.has(n.id) && !removed.has(n.id))
  }

  function isHidden(id: string) {
    return (scene.value.removed ?? []).includes(id)
  }

  function nodeOf(id: string): GraphicNode | undefined {
    return scene.value.nodes.find((n) => n.id === id)
  }

  function labelOf(id: string, fallback: string) {
    return nodeOf(id)?.label || fallback
  }

  function statusOf(id: string, fallback: string) {
    return nodeOf(id)?.status || fallback
  }

  function coordXOf(id: string, fallback: number) {
    const n = nodeOf(id)
    return n?.x ?? fallback
  }

  function coordYOf(id: string, fallback: number) {
    const n = nodeOf(id)
    return n?.y ?? fallback
  }

  function paramOf(id: string, key: string, fallback = '') {
    const v = nodeOf(id)?.params?.[key]
    return v == null || v === '' ? fallback : String(v)
  }

  const hasOverrides = computed(
    () =>
      scene.value.nodes.length > 0 ||
      scene.value.edges.length > 0 ||
      scene.value.removed.length > 0 ||
      Object.keys(scene.value.params ?? {}).length > 0,
  )

  if (autoLoad && getCurrentInstance()) {
    onMounted(() => void reload())
  }

  return {
    kind,
    scene,
    loading,
    saving,
    error,
    dirty,
    usingFallback,
    updatedBy,
    updatedAt,
    hasOverrides,
    reload,
    save,
    reset,
    apply,
    upsertNode,
    removeNode,
    restoreNode,
    setEdge,
    removeEdge,
    setParam,
    removeParam,
    getParam,
    customNodes,
    isHidden,
    labelOf,
    statusOf,
    coordXOf,
    coordYOf,
    paramOf,
  }
}
