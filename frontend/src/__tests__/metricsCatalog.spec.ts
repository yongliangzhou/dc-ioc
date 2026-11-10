import { describe, it, expect } from 'vitest'
import {
  metricsCatalog,
  severityOf,
  formatMetric,
  BAR_THRESHOLDS,
  CAPACITY_THRESHOLDS,
} from '@/config/metricsCatalog'

describe('指标字典（阶段 1 阈值收编）', () => {
  it('每条定义都有单位、精度、来源与分组', () => {
    for (const [key, def] of Object.entries(metricsCatalog)) {
      expect(def.key).toBe(key)
      expect(def.unit).toBeTruthy()
      expect(def.precision).toBeGreaterThanOrEqual(0)
      expect(def.source.startsWith('/api/')).toBe(true)
      expect(def.group).toBeTruthy()
    }
  })

  it('direction=above 的阈值判定（严格大于，与页面原表达式一致）', () => {
    expect(severityOf('network.switch.cpu', 60)).toBe('normal')
    expect(severityOf('network.switch.cpu', 61)).toBe('warning')
    expect(severityOf('network.switch.cpu', 80)).toBe('warning')
    expect(severityOf('network.switch.cpu', 81)).toBe('danger')
    expect(severityOf('power.fuel.pressure', 0.6)).toBe('warning')
  })

  it('direction=below 的阈值判定，danger 优先于 warn', () => {
    expect(severityOf('power.fuel.fullLoadHours', 12)).toBe('normal')
    expect(severityOf('power.fuel.fullLoadHours', 11)).toBe('warning')
    expect(severityOf('power.fuel.fullLoadHours', 8)).toBe('warning')
    expect(severityOf('power.fuel.fullLoadHours', 7)).toBe('danger')
    expect(severityOf('power.battery.voltage', 199)).toBe('danger')
    expect(severityOf('network.wireless.onlineRate', 89)).toBe('warning')
  })

  it('未登记指标、空值与非有限值不误判', () => {
    expect(severityOf('not.registered', 999)).toBe('normal')
    expect(severityOf('power.battery.soc', null)).toBe('normal')
    expect(severityOf('power.battery.soc', Number.NaN)).toBe('normal')
  })

  it('格式化按精度，空值显示占位符', () => {
    expect(formatMetric('power.battery.soc', 87.345)).toBe('87.3')
    expect(formatMetric('power.fuel.fullLoadHours', 8)).toBe('8.0')
    expect(formatMetric('power.battery.soc', null)).toBe('-')
    expect(formatMetric('unknown', 12.345)).toBe('12.345')
  })

  it('容量与图表阈值与 03_METRICS_IA.md §2 一致', () => {
    expect(CAPACITY_THRESHOLDS).toEqual({ warn: 85, full: 100 })
    expect(BAR_THRESHOLDS).toEqual({ warn: 70, danger: 85 })
    expect(metricsCatalog['capacity.usedRatio'].thresholds?.warn).toBe(CAPACITY_THRESHOLDS.warn)
  })
})
