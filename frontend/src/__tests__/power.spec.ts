import { describe, expect, it } from 'vitest'
import { avg, normStatus, num, toDevices, type RawItem } from '@/api/power'

describe('power: num', () => {
  it('解析有效数字', () => {
    expect(num('12.5')).toBe(12.5)
    expect(num(42)).toBe(42)
    expect(num('380.0')).toBe(380)
  })
  it('非数字返回 null (避免把"无数据"显示成 0)', () => {
    expect(num('')).toBeNull()
    expect(num('N/A')).toBeNull()
    expect(num(null)).toBeNull()
    expect(num(undefined)).toBeNull()
  })
})

describe('power: avg', () => {
  it('非空均值保留 1 位小数', () => {
    expect(avg([1, 2, 3])).toBe(2)
    expect(avg([10, 20])).toBe(15)
  })
  it('含 null 时忽略', () => {
    expect(avg([10, null, 20])).toBe(15)
  })
  it('全空返回 null', () => {
    expect(avg([null, null])).toBeNull()
    expect(avg([])).toBeNull()
  })
})

describe('power: normStatus', () => {
  it('中文状态映射', () => {
    expect(normStatus('运行中')).toBe('online')
    expect(normStatus('故障')).toBe('fault')
    expect(normStatus('告警')).toBe('warning')
    expect(normStatus('待机')).toBe('standby')
    expect(normStatus('')).toBe('unknown')
  })
})

describe('power: toDevices', () => {
  const list: RawItem[] = [
    { device_id: 'A1', state: '运行', u: '380', i: '10', load: '50' },
    { device_id: 'A2', state: '故障', u: '0', i: '0', load: '0' },
  ]
  it('映射为统一 PowerDeviceView 并补编号', () => {
    const out = toDevices(list, '高压配电', 'HV', (d) => ({
      status: normStatus(d.state),
      voltage: num(d.u),
      current: num(d.i),
      loadPercent: num(d.load),
    }))
    expect(out).toHaveLength(2)
    expect(out[0].id).toBe('HV-1') // id 为设备编码(无 d.id 时用 prefix-序号)
    expect(out[0].no).toBe(1) // no 为列表序号(支持 offset 续编)
    expect(out[0].roomName).toBe('高压配电')
    expect(out[1].status).toBe('fault')
    expect(out[1].no).toBe(2)
  })
})
