import { describe, it, expect } from 'vitest'
import { STATUS_MAP, statusClassOf, statusLabelOf, DEFAULT_STATUS_CLASS } from '@dc-ioc/ui'

describe('@dc-ioc/ui 状态语义映射（阶段 1 组件收敛回归）', () => {
  it('已知状态返回完整 dui- 类名，不再产生 dui-dui-* 双前缀', () => {
    expect(statusClassOf('online')).toBe('dui-g')
    expect(statusClassOf('running')).toBe('dui-g')
    expect(statusClassOf('fault')).toBe('dui-r')
    expect(statusClassOf('standby')).toBe('dui-a')
    expect(statusClassOf('offline')).toBe('dui-o')
    expect(statusClassOf('closing')).toBe('dui-b')
    for (const key of Object.keys(STATUS_MAP as Record<string, unknown>)) {
      const cls = statusClassOf(key)
      expect(cls.startsWith('dui-')).toBe(true)
      expect(cls.startsWith('dui-dui-')).toBe(false)
    }
  })

  it('大小写不敏感，未知/空状态回退到默认类', () => {
    expect(statusClassOf('FAULT')).toBe('dui-r')
    expect(statusClassOf('  Online ')).toBe(DEFAULT_STATUS_CLASS)
    expect(statusClassOf('unknown')).toBe(DEFAULT_STATUS_CLASS)
    expect(statusClassOf('')).toBe(DEFAULT_STATUS_CLASS)
    expect(statusClassOf(null)).toBe(DEFAULT_STATUS_CLASS)
    expect(statusClassOf(undefined)).toBe(DEFAULT_STATUS_CLASS)
  })

  it('默认文案可读，未知状态原样回显，空值显示占位符', () => {
    expect(statusLabelOf('offline')).toBe('离线')
    expect(statusLabelOf('maintenance')).toBe('检修')
    expect(statusLabelOf('custom-state')).toBe('custom-state')
    expect(statusLabelOf('')).toBe('-')
    expect(statusLabelOf(null)).toBe('-')
  })
})
