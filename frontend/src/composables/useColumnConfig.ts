/**
 * 阶段 3 · 表格列配置（04 §6.2）。
 *
 * 页面把硬编码 `<th>` 抽成 `ColumnSeed[]`，用本文件的纯函数管理显隐与顺序，
 * `applyColumns()` 输出可直接传给 `DeviceTable.vue` 的 `columns: TableColumn[]`，
 * 表格组件本身无需改动。持久化结构由 `useViewPreferences` 负责。
 */
export interface ColumnDef {
  key: string
  label: string
  visible: boolean
  order: number
  /** 主键/名称等关键列不允许隐藏 */
  locked?: boolean
}

export interface ColumnSeed {
  key: string
  label: string
  locked?: boolean
}

export function defaultColumns(seeds: ColumnSeed[]): ColumnDef[] {
  return seeds.map((s, i) => ({
    key: s.key,
    label: s.label,
    visible: true,
    order: i,
    ...(s.locked ? { locked: true } : {}),
  }))
}

const isRecord = (x: unknown): x is Record<string, unknown> =>
  !!x && typeof x === 'object' && !Array.isArray(x)

/** 防御式解析：未知 key 丢弃、缺失列补齐、locked 列强制可见、order 重排为连续值。 */
export function normalizeColumns(input: unknown, seeds: ColumnSeed[]): ColumnDef[] {
  const base = defaultColumns(seeds)
  if (!Array.isArray(input)) return base
  const known = new Set(base.map((c) => c.key))
  const overrides = new Map<string, Record<string, unknown>>()
  for (const raw of input) {
    if (!isRecord(raw)) continue
    if (typeof raw.key === 'string' && known.has(raw.key)) overrides.set(raw.key, raw)
  }
  const merged = base.map((b) => {
    const o = overrides.get(b.key)
    return {
      ...b,
      visible: b.locked ? true : o && typeof o.visible === 'boolean' ? o.visible : true,
      order: o && typeof o.order === 'number' && Number.isFinite(o.order) ? o.order : b.order,
    }
  })
  return merged.sort((a, b) => a.order - b.order).map((x, i) => ({ ...x, order: i }))
}

export function toggleColumn(cols: ColumnDef[], key: string): ColumnDef[] {
  return cols.map((c) => (c.key === key && !c.locked ? { ...c, visible: !c.visible } : c))
}

export function moveColumn(cols: ColumnDef[], key: string, delta: number): ColumnDef[] {
  const idx = cols.findIndex((c) => c.key === key)
  const target = idx + delta
  if (idx < 0 || target < 0 || target >= cols.length) return cols
  const copy = [...cols]
  ;[copy[idx], copy[target]] = [copy[target], copy[idx]]
  return copy.map((c, i) => ({ ...c, order: i }))
}

export function visibleKeys(cols: ColumnDef[]): string[] {
  return cols.filter((c) => c.visible).map((c) => c.key)
}

/** 按配置的显隐与顺序过滤/排序任意 `{ key }` 列数组（TableColumn 等）。 */
export function applyColumns<T extends { key: string }>(all: T[], cols: ColumnDef[]): T[] {
  const order = new Map(cols.map((c) => [c.key, c.order]))
  const visible = new Set(visibleKeys(cols))
  return all
    .filter((c) => visible.has(c.key))
    .sort(
      (a, b) =>
        (order.get(a.key) ?? Number.MAX_SAFE_INTEGER) -
        (order.get(b.key) ?? Number.MAX_SAFE_INTEGER),
    )
}

export function isDefaultColumns(cols: ColumnDef[], seeds: ColumnSeed[]): boolean {
  const d = defaultColumns(seeds)
  const n = normalizeColumns(cols, seeds)
  return d.every((x, i) => n[i].key === x.key && n[i].visible === true && n[i].order === i)
}
