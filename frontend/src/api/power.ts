import request from './request'

// ---- 后端返回的真实结构 (与 generator hv / lv / genset / fuel / battery 对齐) ----
// hv():      { incomers:[{id,src,state,u,i,p,pf,...}], feeders:[...], transformers:[{id,state,load,uLow,...}], ... }
// lv():      { transformers:[{id,state,load,u,i,p,...}], upsGroups:[...], hvdc:[...], branches:[{id,name,loadPct,u,p,...}], ... }
// genset():  { units:[{id,state,u,i,p,rpm,...}], busState, ... }
// fuel():    { mainTanks:[{id,cap,level,t,...}], dayTanks:[...], pumps:[{id,state,mode,...}], ... }
// battery(): { groups:[{id,type,soc,u,i,state,maxT,...}], ... }

export interface PowerDeviceView {
  id: number
  code: string
  name: string
  roomName: string
  status: string
  voltage: number | null
  current: number | null
  powerKw: number | null
  loadPercent: number | null
  powerFactor: number | null
  fuelLevel: number | null
  fuelConsumption: number | null
  commissionedOn: string | null
  healthScore: number | null
}

export interface PowerSystemSummary {
  total: number
  online: number
  avgLoadPercent: number | null
  avgVoltage: number | null
  avgCurrent: number | null
  devices: PowerDeviceView[]
}

export interface PowerOverview {
  totalEquipment: number
  onlineCount: number
  faultCount: number
  warningCount: number
  hv: PowerSystemSummary
  lv: PowerSystemSummary
  genset: PowerSystemSummary
  fuel: PowerSystemSummary
  battery: PowerSystemSummary
}

// ---- 工具函数 ----

/** 后端中文状态 -> 前端统一状态标识。 */
function normStatus(state: unknown): string {
  const s = String(state ?? '').trim()
  if (!s) return 'unknown'
  if (s.includes('故障') || s.includes('检修') || s.includes('停机') || s.includes('失电')) return 'fault'
  if (s.includes('告警') || s.includes('异常') || s.includes('预警')) return 'warning'
  if (s.includes('待机') || s.includes('备用') || s.includes('热备')) return 'standby'
  if (s.includes('运行') || s.includes('合闸') || s.includes('正常') || s.includes('在线')) return 'online'
  return 'standby'
}

function num(v: unknown): number | null {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

/** 对非空数值求均值; 全空返回 null (避免把"无数据"显示成 0)。 */
function avg(list: (number | null)[]): number | null {
  const vals = list.filter((v): v is number => v != null)
  if (!vals.length) return null
  return Number((vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(1))
}

interface RawItem {
  [k: string]: unknown
}

/** 通用: 把后端某个设备数组映射为统一的 PowerDeviceView 列表。 */
function toDevices(
  list: RawItem[],
  room: string,
  prefix: string,
  pick: (d: RawItem) => Partial<PowerDeviceView>,
  offset = 0,
): PowerDeviceView[] {
  return list.map((d, i) => {
    const code = String(d.id ?? `${prefix}-${i + 1}`)
    return {
      id: offset + i + 1,
      code,
      name: String(d.name ?? d.id ?? `${prefix}-${i + 1}`),
      roomName: room,
      status: normStatus(d.state ?? d.breaker),
      voltage: null,
      current: null,
      powerKw: null,
      loadPercent: null,
      powerFactor: null,
      fuelLevel: null,
      fuelConsumption: null,
      commissionedOn: null,
      healthScore: null,
      ...pick(d),
    }
  })
}

function summarize(devices: PowerDeviceView[]): PowerSystemSummary {
  return {
    total: devices.length,
    online: devices.filter((d) => d.status === 'online').length,
    avgLoadPercent: avg(devices.map((d) => d.loadPercent)),
    avgVoltage: avg(devices.map((d) => d.voltage)),
    avgCurrent: avg(devices.map((d) => d.current)),
    devices,
  }
}

// ---- 各子域映射器 ----

/** 10KV 中压: 进线 + 馈线 + 变压器 (中压侧电压单位 kV, 统一换算为 V)。 */
function mapHv(raw: RawItem): PowerSystemSummary {
  const incomers = (raw?.incomers as RawItem[]) ?? []
  const feeders = (raw?.feeders as RawItem[]) ?? []
  const transformers = (raw?.transformers as RawItem[]) ?? []
  const kv = (v: unknown) => {
    const n = num(v)
    return n == null ? null : Number((n * 1000).toFixed(0))
  }
  const devices = [
    ...toDevices(incomers, '10KV 开关站', 'IN', (d) => ({
      voltage: kv(d.u),
      current: num(d.i),
      powerKw: num(d.p) != null ? Number((num(d.p)! * 1000).toFixed(0)) : null,
      powerFactor: num(d.pf),
    })),
    ...toDevices(feeders, '10KV 开关站', 'F', (d) => ({
      name: String(d.load ?? d.id ?? ''),
      voltage: kv(d.ua),
      current: num(d.i),
      powerKw: num(d.p) != null ? Number((num(d.p)! * 1000).toFixed(0)) : null,
      powerFactor: num(d.pf),
    }), incomers.length),
    ...toDevices(transformers, '变压器室', 'T', (d) => ({
      voltage: kv(d.uHigh),
      current: num(d.iHigh),
      loadPercent: num(d.load),
    }), incomers.length + feeders.length),
  ]
  return summarize(devices)
}

/** 0.4KV 低压: 变压器 + UPS + HVDC + 出线回路。 */
function mapLv(raw: RawItem): PowerSystemSummary {
  const transformers = (raw?.transformers as RawItem[]) ?? []
  const ups = (raw?.upsGroups as RawItem[]) ?? []
  const hvdc = (raw?.hvdc as RawItem[]) ?? []
  const branches = (raw?.branches as RawItem[]) ?? []
  let off = 0
  const t = toDevices(transformers, '变压器室', 'T', (d) => ({
    voltage: num(d.u) != null ? Number((num(d.u)! * 1000).toFixed(0)) : null,
    current: num(d.i),
    powerKw: num(d.p),
    loadPercent: num(d.load),
    powerFactor: num(d.pf),
  }), off)
  off += t.length
  const u = toDevices(ups, 'UPS 电力室', 'UPS', (d) => ({
    voltage: num(d.uOut),
    current: num(d.iOut),
    powerKw: num(d.p),
    loadPercent: num(d.load),
    powerFactor: num(d.pf),
  }), off)
  off += u.length
  const h = toDevices(hvdc, 'HVDC 电力室', 'HVDC', (d) => ({
    voltage: num(d.u),
    current: num(d.i),
    powerKw: num(d.p),
    loadPercent: num(d.load),
    powerFactor: num(d.pf),
  }), off)
  off += h.length
  const b = toDevices(branches, '低压配电室', 'LP', (d) => ({
    status: normStatus(d.breaker),
    voltage: num(d.u),
    current: num(d.i),
    powerKw: num(d.p),
    loadPercent: num(d.loadPct),
    powerFactor: num(d.pf),
  }), off)
  return summarize([...t, ...u, ...h, ...b])
}

/** 柴发并机: units (中压机组, 电压单位 kV)。 */
function mapGenset(raw: RawItem): PowerSystemSummary {
  const units = (raw?.units as RawItem[]) ?? []
  const devices = toDevices(units, '柴发机房', 'DG', (d) => {
    const p = num(d.p)
    return {
      voltage: num(d.u) != null ? Number((num(d.u)! * 1000).toFixed(0)) : null,
      current: num(d.i),
      powerKw: p,
      // 机组额定按 2500kW 估算负载率, 仅在有功率读数时计算
      loadPercent: p != null ? Number(((p / 2500) * 100).toFixed(1)) : null,
      powerFactor: num(d.pf),
    }
  })
  return summarize(devices)
}

/** 燃油: 主油罐 + 日用油箱 + 油泵 (以油位作为负载率维度)。 */
function mapFuel(raw: RawItem): PowerSystemSummary {
  const main = (raw?.mainTanks as RawItem[]) ?? []
  const day = (raw?.dayTanks as RawItem[]) ?? []
  const pumps = (raw?.pumps as RawItem[]) ?? []
  const m = toDevices(main, '室外油库', 'MT', (d) => ({
    status: normStatus(d.leak === '正常' ? '运行' : d.leak),
    fuelLevel: num(d.level),
    loadPercent: num(d.level),
  }))
  const dt = toDevices(day, '日用油间', 'DT', (d) => ({
    status: normStatus(d.leak === '正常' ? '运行' : d.leak),
    fuelLevel: num(d.level),
    loadPercent: num(d.level),
  }), m.length)
  const p = toDevices(pumps, '油泵房', 'P', (d) => ({
    status: normStatus(d.state),
  }), m.length + dt.length)
  return summarize([...m, ...dt, ...p])
}

/** 电池: groups (以 SOC 作为负载率维度)。 */
function mapBattery(raw: RawItem): PowerSystemSummary {
  const groups = (raw?.groups as RawItem[]) ?? []
  const devices = toDevices(groups, '电池室', 'BAT', (d) => ({
    name: String(d.id ?? ''),
    voltage: num(d.u),
    current: num(d.i),
    loadPercent: num(d.soc),
  }))
  return summarize(devices)
}

// ---- API 调用 ----

function emptySummary(): PowerSystemSummary {
  return { total: 0, online: 0, avgLoadPercent: null, avgVoltage: null, avgCurrent: null, devices: [] }
}

function fetchMapped(
  url: string,
  mapper: (raw: RawItem) => PowerSystemSummary,
): Promise<PowerSystemSummary> {
  return request
    .get<unknown, RawItem>(url)
    .then((raw) => mapper(raw ?? {}))
    .catch(() => emptySummary())
}

export function getPowerHv(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/hv', mapHv)
}

export function getPowerLv(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/lv', mapLv)
}

export function getPowerGenset(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/genset', mapGenset)
}

export function getPowerFuel(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/fuel', mapFuel)
}

export function getPowerBattery(): Promise<PowerSystemSummary> {
  return fetchMapped('/api/power/battery', mapBattery)
}

export function getPowerOverview(): Promise<PowerOverview> {
  return Promise.all([
    getPowerHv(),
    getPowerLv(),
    getPowerGenset(),
    getPowerFuel(),
    getPowerBattery(),
  ]).then(([hv, lv, genset, fuel, battery]) => {
    const all = [hv, lv, genset, fuel, battery]
    const devices = all.flatMap((s) => s.devices)
    return {
      totalEquipment: all.reduce((s, x) => s + x.total, 0),
      onlineCount: all.reduce((s, x) => s + x.online, 0),
      faultCount: devices.filter((d) => d.status === 'fault').length,
      warningCount: devices.filter((d) => d.status === 'warning').length,
      hv,
      lv,
      genset,
      fuel,
      battery,
    }
  })
}
