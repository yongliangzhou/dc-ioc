import request from './request'

// ---- 后端类型 (从 Java MonitorDtos 映射) ----

export interface NetworkDeviceView {
  id: number
  code: string
  name: string
  roomName: string
  status: string
  pingMs: number | null
  bwUtilization: number | null
  portCount: number
  uplinkPort: number
  firmwareVersion: string | null
  commissionedOn: string | null
  healthScore: number | null
}

export interface NetworkSystemSummary {
  total: number
  online: number
  avgPingMs: number | null
  avgBwUtilization: number | null
  devices: NetworkDeviceView[]
}

export interface NetworkOverview {
  totalEquipment: number
  onlineCount: number
  faultCount: number
  warningCount: number
  avgPingMs: number | null
  avgBwUtilization: number | null
  switchs: NetworkSystemSummary
  routers: NetworkSystemSummary
  firewalls: NetworkSystemSummary
  wireless: NetworkSystemSummary
}

// ---- API 调用 ----

export function getNetworkOverview(): Promise<NetworkOverview> {
  return request.get('/api/network/overview')
}

export function getNetworkSwitch(): Promise<NetworkSystemSummary> {
  return request.get('/api/network/switch')
}

export function getNetworkRouter(): Promise<NetworkSystemSummary> {
  return request.get('/api/network/router')
}

export function getNetworkFirewall(): Promise<NetworkSystemSummary> {
  return request.get('/api/network/firewall')
}

export function getNetworkWireless(): Promise<NetworkSystemSummary> {
  return request.get('/api/network/wireless')
}
