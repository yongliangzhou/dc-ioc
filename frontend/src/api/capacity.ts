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

export function getCapacityOverview(): Promise<CapacityOverview> {
  return request.get('/api/ops/capacity').then((r: any) => r.data)
}
