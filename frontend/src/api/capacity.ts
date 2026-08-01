import request from './request'

// ===== Capacity 容量管理 =====

export interface RoomCapacityView {
  roomName: string
  powerUtilization: number | null
  coolingUtilization: number | null
  spaceUtilization: number | null
  rackUtilization: number | null
}

export interface CapacityOverview {
  rooms: RoomCapacityView[]
  overallPowerUtilization: number
  overallCoolingUtilization: number
  overallSpaceUtilization: number
  overallRackUtilization: number
}

// ---- 后端/模拟原始结构: generated.capacity() ----
interface RawDim {
  id?: string
  name?: string
  used?: number
  total?: number
  unit?: string
}
interface RawRoom {
  id?: string
  name?: string
  racks?: number
  used?: number
  powerPct?: number
  coolPct?: number
  powerUtilization?: number
  coolingUtilization?: number
  spaceUtilization?: number
  rackUtilization?: number
}
interface RawCapacity {
  dims?: RawDim[]
  rooms?: RawRoom[]
  forecast?: string
}

function pctOf(used?: number, total?: number): number | null {
  if (used == null || !total) return null
  return Number(((used / total) * 100).toFixed(1))
}

function mapCapacity(raw: RawCapacity): CapacityOverview {
  const dims = raw.dims ?? []
  const dim = (key: string) => dims.find((d) => (d.id ?? d.name ?? '').includes(key))
  const powerDim = dim('电力') ?? dim('供电')
  const coolDim = dim('制冷')
  const spaceDim = dim('机柜') ?? dim('空间')

  const rooms: RoomCapacityView[] = (raw.rooms ?? []).map((r) => {
    const rackUtil = r.rackUtilization ?? (r.racks ? pctOf(r.used, r.racks) : null)
    return {
      roomName: r.name ?? r.id ?? '未知机房',
      powerUtilization: r.powerUtilization ?? r.powerPct ?? null,
      coolingUtilization: r.coolingUtilization ?? r.coolPct ?? null,
      spaceUtilization: r.spaceUtilization ?? rackUtil,
      rackUtilization: r.rackUtilization ?? rackUtil,
    }
  })

  const avg = (arr: (number | null)[]): number => {
    const vals = arr.filter((v): v is number => v != null)
    return vals.length ? Number((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1)) : 0
  }

  return {
    rooms,
    overallPowerUtilization: powerDim ? (pctOf(powerDim.used, powerDim.total) ?? 0) : avg(rooms.map((r) => r.powerUtilization)),
    overallCoolingUtilization: coolDim ? (pctOf(coolDim.used, coolDim.total) ?? 0) : avg(rooms.map((r) => r.coolingUtilization)),
    overallSpaceUtilization: spaceDim ? (pctOf(spaceDim.used, spaceDim.total) ?? 0) : avg(rooms.map((r) => r.spaceUtilization)),
    overallRackUtilization: avg(rooms.map((r) => r.rackUtilization)),
  }
}

export function getCapacityOverview(): Promise<CapacityOverview> {
  return request.get<unknown, RawCapacity>('/api/ops/capacity').then(mapCapacity)
}
