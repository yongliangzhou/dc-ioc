import { describe, expect, it } from 'vitest'
import {
  applyColumns,
  defaultColumns,
  isDefaultColumns,
  moveColumn,
  normalizeColumns,
  toggleColumn,
  visibleKeys,
  type ColumnSeed,
} from '../useColumnConfig'

const seeds: ColumnSeed[] = [
  { key: 'name', label: '名称', locked: true },
  { key: 'status', label: '状态' },
  { key: 'temp', label: '温度' },
]

describe('useColumnConfig 纯函数', () => {
  it('默认列全部可见且 order 连续', () => {
    const cols = defaultColumns(seeds)
    expect(cols.map((c) => c.order)).toEqual([0, 1, 2])
    expect(cols.every((c) => c.visible)).toBe(true)
    expect(cols[0].locked).toBe(true)
    expect(isDefaultColumns(cols, seeds)).toBe(true)
  })

  it('未知 key 丢弃、缺失列补齐、locked 列强制可见', () => {
    const cols = normalizeColumns(
      [
        { key: 'ghost', visible: false, order: 0 },
        { key: 'name', visible: false, order: 9 },
        { key: 'temp', visible: false },
      ],
      seeds,
    )
    expect(cols).toHaveLength(3)
    expect(cols.some((c) => c.key === 'ghost')).toBe(false)
    expect(cols.find((c) => c.key === 'name')?.visible).toBe(true)
    expect(cols.find((c) => c.key === 'temp')?.visible).toBe(false)
    expect(cols.map((c) => c.order)).toEqual([0, 1, 2])
    expect(normalizeColumns(null, seeds)).toEqual(defaultColumns(seeds))
  })

  it('toggle 不影响 locked 列, move 边界不越界且 order 连续', () => {
    const cols = defaultColumns(seeds)
    expect(toggleColumn(cols, 'name').find((c) => c.key === 'name')?.visible).toBe(true)
    expect(toggleColumn(cols, 'status').find((c) => c.key === 'status')?.visible).toBe(false)
    expect(moveColumn(cols, 'name', -1)[0].key).toBe('name')
    const moved = moveColumn(cols, 'temp', -1)
    expect(moved.map((c) => c.key)).toEqual(['name', 'temp', 'status'])
    expect(moved.map((c) => c.order)).toEqual([0, 1, 2])
  })

  it('applyColumns 按配置显隐与顺序过滤 TableColumn 数组', () => {
    const all = [
      { key: 'name', label: '名称' },
      { key: 'status', label: '状态' },
      { key: 'temp', label: '温度' },
    ]
    let cols = toggleColumn(defaultColumns(seeds), 'status')
    cols = moveColumn(cols, 'temp', -1)
    expect(visibleKeys(cols)).toEqual(['name', 'temp'])
    expect(applyColumns(all, cols).map((c) => c.key)).toEqual(['name', 'temp'])
    expect(applyColumns(all, defaultColumns(seeds))).toEqual(all)
  })
})
