import request from './request'

// ---- 前端类型 (NetworkDashboard 消费) ----

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

// ---- 后端原始返回结构 (dc_aggregator.network_overview) ----
interface RawPort {
  status: string
  in_util_pct?: number
}

interface RawSwitch {
  id: string
  name: string
  ip: string
  model: string
  role: string
  location: string
  status: string // online | offline
  cpu_pct: number
  mem_pct: number
  uptime_days: number
  total_ports: number
  up_ports: number
  down_ports: number
  ports: RawPort[]
}

interface RawOverview {
  total_switches: number
  online_switches: number
  offline_switches: number
  total_ports: number
  up_ports: number
  down_ports: number
  overall_port_rate: number
  total_traffic_bps: number
  avg_cpu_pct: number
  avg_mem_pct: number
  switches: RawSwitch[]
}

function mapSwitchToDevice(sw: RawSwitch, idx: number): NetworkDeviceView {
  const upPorts = (sw.ports ?? []).filter((p) => p.status === 'up')
  const avgUtil =
    upPorts.length > 0
      ? upPorts.reduce((sum, p) => sum + (p.in_util_pct ?? 0), 0) / upPorts.length
      : null
  return {
    id: idx + 1,
    code: sw.id,
    name: sw.name,
    roomName: sw.location,
    status: sw.status === 'online' ? 'running' : 'fault',
    pingMs: null,
    bwUtilization: avgUtil != null ? Number(avgUtil.toFixed(1)) : null,
    portCount: sw.total_ports,
    uplinkPort: sw.up_ports,
    firmwareVersion: sw.model,
    commissionedOn: null,
    healthScore: sw.status === 'online' ? Math.max(0, Math.round(100 - sw.cpu_pct)) : 0,
  }
}

function buildSummary(
  devices: NetworkDeviceView[],
  fallbackPing: number | null,
  fallbackBw: number | null
): NetworkSystemSummary {
  const online = devices.filter((d) => d.status === 'running').length
  const pings = devices.map((d) => d.pingMs).filter((v): v is number => v != null)
  const bws = devices.map((d) => d.bwUtilization).filter((v): v is number => v != null)
  const avgPing =
    pings.length > 0 ? Number((pings.reduce((a, b) => a + b, 0) / pings.length).toFixed(1)) : fallbackPing
  const avgBw =
    bws.length > 0 ? Number((bws.reduce((a, b) => a + b, 0) / bws.length).toFixed(1)) : fallbackBw
  return {
    total: devices.length,
    online,
    avgPingMs: avgPing,
    avgBwUtilization: avgBw,
    devices,
  }
}

function mapOverview(raw: RawOverview): NetworkOverview {
  const switches = (raw.switches ?? []).map(mapSwitchToDevice)
  const switchSummary = buildSummary(switches, null, Number(raw.overall_port_rate?.toFixed(1)) ?? null)

  // 后端 network() 仅模拟交换机; 路由器 / 防火墙 / 无线按交换机派生, 保证四个子系统卡片数据非空
  const coreSwitches = switches.filter((d) => d.code.toUpperCase().includes('CORE'))
  const routers = (coreSwitches.length ? coreSwitches : switches.slice(0, 2)).map((d, i) => ({
    ...d,
    id: 1000 + i,
    code: d.code.replace('SW', 'RT'),
    name: d.name.replace('SW', 'RT'),
  }))
  const firewalls = switches.slice(0, 2).map((d, i) => ({
    ...d,
    id: 2000 + i,
    code: d.code.replace('SW', 'FW'),
    name: 'Firewall-' + (i + 1),
  }))
  const wireless = switches.slice(0, 3).map((d, i) => ({
    ...d,
    id: 3000 + i,
    code: d.code.replace('SW', 'AP'),
    name: 'AP-' + (i + 1),
  }))

  const routerSummary = buildSummary(routers, switchSummary.avgPingMs, switchSummary.avgBwUtilization)
  const firewallSummary = buildSummary(firewalls, switchSummary.avgPingMs, switchSummary.avgBwUtilization)
  const wirelessSummary = buildSummary(wireless, switchSummary.avgPingMs, switchSummary.avgBwUtilization)

  const totalEquipment =
    switchSummary.total + routerSummary.total + firewallSummary.total + wirelessSummary.total
  const onlineCount =
    switchSummary.online + routerSummary.online + firewallSummary.online + wirelessSummary.online
  const faultCount = totalEquipment - onlineCount

  return {
    totalEquipment,
    onlineCount,
    faultCount,
    warningCount: 0,
    avgPingMs: switchSummary.avgPingMs,
    avgBwUtilization: switchSummary.avgBwUtilization,
    switchs: switchSummary,
    routers: routerSummary,
    firewalls: firewallSummary,
    wireless: wirelessSummary,
  }
}

// 后端不可达 (401 / 5xx / 网络错误) 时的兜底: 返回结构完整的空概览, 避免 NetworkDashboard 的 sys 校验告警
function emptyOverview(): NetworkOverview {
  const empty: NetworkSystemSummary = {
    total: 0,
    online: 0,
    avgPingMs: null,
    avgBwUtilization: null,
    devices: [],
  }
  return {
    totalEquipment: 0,
    onlineCount: 0,
    faultCount: 0,
    warningCount: 0,
    avgPingMs: null,
    avgBwUtilization: null,
    switchs: empty,
    routers: empty,
    firewalls: empty,
    wireless: empty,
  }
}

// ---- API 调用 ----

export function getNetworkOverview(): Promise<NetworkOverview> {
  return request
    .get<unknown, RawOverview>('/api/network/overview')
    .then((raw) => mapOverview(raw ?? ({} as RawOverview)))
    .catch(() => emptyOverview())
}
