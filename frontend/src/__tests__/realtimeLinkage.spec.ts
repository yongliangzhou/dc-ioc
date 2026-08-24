import { describe, expect, it } from 'vitest'
import { mapAlarm, toClock, type RawAlarm } from '@/engine/realtimeLinkage'

describe('realtimeLinkage: toClock', () => {
  it('ISO -> HH:MM:SS', () => {
    expect(toClock('2026-08-12T09:05:03Z')).toMatch(/^\d{2}:\d{2}:\d{2}$/)
  })
  it('非法输入原样返回', () => {
    expect(toClock('not-a-date')).toBe('not-a-date')
  })
})

describe('realtimeLinkage: mapAlarm', () => {
  const raw: RawAlarm = {
    id: 'evt-1',
    device_id: 'HV-01',
    metric_name: 'u',
    value: '410',
    threshold: '400',
    unit: 'V',
    level: 'crit',
    system: '高压',
    desc: '电压越限',
    state: '待确认',
    ts: '2026-08-12T09:05:03Z',
    owner: '张三',
    category: 'power',
  }
  it('映射后端告警为前端 RtAlarm', () => {
    const a = mapAlarm(raw)
    expect(a.id).toBe('evt-1')
    expect(a.deviceId).toBe('HV-01')
    expect(a.metric).toBe('u')
    expect(a.value).toBe(410)
    expect(a.threshold).toBe(400)
    expect(a.level).toBe('crit')
    expect(a.system).toBe('高压')
    expect(a.message).toBe('电压越限')
    expect(a.status).toBe('待确认')
    expect(a.rt).toBe(true)
    expect(a.time).toMatch(/^\d{2}:\d{2}:\d{2}$/)
  })
  it('缺失字段兜底', () => {
    const a = mapAlarm({})
    expect(a.id).toContain(':') // `${device_id}:${metric_name}:${level}`
    expect(a.level).toBe('info')
    expect(a.unit).toBe('')
  })
})
