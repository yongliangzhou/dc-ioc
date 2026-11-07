import { describe, expect, it } from 'vitest'
import {
  defaultLayout,
  isDefaultLayout,
  isVisible,
  moveSection,
  normalizeLayout,
  sectionStyle,
  toggleSection,
  DASHBOARD_SECTIONS,
} from '../useDashboardLayout'

describe('useDashboardLayout 纯函数', () => {
  it('默认布局包含全部 6 个区块且全部可见', () => {
    const layout = defaultLayout()
    expect(layout).toHaveLength(DASHBOARD_SECTIONS.length)
    expect(layout.every((x) => x.visible)).toBe(true)
    expect(layout.map((x) => x.order)).toEqual([0, 1, 2, 3, 4, 5])
  })

  it('非法/残缺输入按默认值补齐, 未知 id 丢弃', () => {
    const normalized = normalizeLayout([
      { id: 'kpi', visible: false, order: 0 },
      { id: 'ghost', visible: false, order: 9 },
      { id: 'trends', visible: 'yes' },
    ])
    expect(normalized).toHaveLength(DASHBOARD_SECTIONS.length)
    expect(normalized.find((x) => x.id === 'kpi')?.visible).toBe(false)
    expect(normalized.some((x) => (x.id as string) === 'ghost')).toBe(false)
    expect(normalized.find((x) => x.id === 'trends')?.visible).toBe(true)
  })

  it('显隐切换只影响目标区块', () => {
    const next = toggleSection(defaultLayout(), 'alarms')
    expect(isVisible(next, 'alarms')).toBe(false)
    expect(isVisible(next, 'kpi')).toBe(true)
  })

  it('上移/下移重排后 order 连续, 边界不越界', () => {
    const up = moveSection(defaultLayout(), 'trends', -1)
    expect(up[0].id).toBe('trends')
    expect(up[1].id).toBe('kpi')
    expect(up.map((x) => x.order)).toEqual([0, 1, 2, 3, 4, 5])
    expect(moveSection(defaultLayout(), 'kpi', -1)[0].id).toBe('kpi')
    expect(moveSection(defaultLayout(), 'campus', 1).at(-1)?.id).toBe('campus')
  })

  it('默认布局判定与 order 映射', () => {
    expect(isDefaultLayout(defaultLayout())).toBe(true)
    expect(isDefaultLayout(toggleSection(defaultLayout(), 'hvac'))).toBe(false)
    expect(sectionStyle(defaultLayout(), 'campus')).toEqual({ order: 5 })
  })
})
