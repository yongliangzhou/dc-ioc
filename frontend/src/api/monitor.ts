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

// ==================== 网络监控详细类型 ====================

// ---- 交换机 ----
export interface SwitchPortView {
  name: string
  alias: string
  status: string
  speed_mbps: number
  in_bps: number
  out_bps: number
  in_util_pct: number
  out_util_pct: number
  in_errors: number
  out_errors: number
  in_discards: number
  tx_power_dbm?: number
  rx_power_dbm?: number
  optical_alarm?: string
}
export interface SwitchTrunkView {
  id: string
  members: string[]
  mode: string
  status: string
  util_pct: number
  traffic_bps: number
}
export interface SwitchStackView {
  enabled: boolean
  topo: string
  members: number
  master: string
  status: string
}
export interface SwitchView {
  id: string
  name: string
  ip: string
  model: string
  role: string
  location: string
  status: string
  cpu_pct: number
  mem_pct: number
  temp_c: number
  uptime_days: number
  total_ports: number
  up_ports: number
  down_ports: number
  ports: SwitchPortView[]
  trunks: SwitchTrunkView[]
  stack: SwitchStackView | null
}
export interface PingTargetView {
  target: string
  name: string
  category: string
  rtt_min_ms: number
  rtt_avg_ms: number
  rtt_max_ms: number
  loss_pct: number
  jitter_ms: number
  status: string
}
export interface BwTopView {
  rank: number
  name: string
  device: string
  direction: string
  util_pct: number
  traffic_bps: number
  capacity_mbps: number
  alert: boolean
}
export interface NetworkSwitchSummary {
  total: number
  online: number
  offline: number
  totalPorts: number
  upPorts: number
  downPorts: number
  overallPortRate: number
  totalTrafficBps: number
  avgCpu: number
  avgMem: number
  switches: SwitchView[]
  pingTargets: PingTargetView[]
  avgPingRttMs: number
  avgPingLossPct: number
  worstPingTarget: string
  bwTopN: BwTopView[]
}

// ---- 路由器 ----
export interface RouterProtocolView {
  name: string
  peer_total?: number
  neighbor_total?: number
  area?: string | number
  peer_up?: number
  neighbor_up?: number
  state: string
  routes: number
  desc: string
  flake?: number
}
export interface RouterView {
  id: string
  name: string
  ip: string
  model: string
  role: string
  location: string
  status: string
  cpu_pct: number
  mem_pct: number
  temp_c: number
  uptime_days: number
  throughput_bps: number
  sessions: number
  bgp_state: string
  ospf_neighbors: number
  routes_total: number
  protocols: RouterProtocolView[]
}
export interface NetworkRouterSummary {
  total: number
  online: number
  routers: RouterView[]
  avgThroughputBps: number
  totalSessions: number
  bgpState: string
  routesTotal: number
}

// ---- 防火墙 ----
export interface FwPolicyHitView {
  name: string
  hits: number
}
export interface FirewallView {
  id: string
  name: string
  ip: string
  model: string
  location: string
  status: string
  cpu_pct: number
  mem_pct: number
  temp_c: number
  uptime_days: number
  concurrent_sessions: number
  session_rate: number
  policy_total: number
  policy_hit_top: FwPolicyHitView[]
  throughput_bps: number
  threat_blocked: number
  vpn_tunnels: number
}
export interface NetworkFirewallSummary {
  total: number
  online: number
  firewalls: FirewallView[]
  concurrentSessions: number
  policyTotal: number
  threatBlocked: number
  vpnTunnels: number
}

// ---- 无线 ----
export interface RadioView {
  status: string
  channel: number
  tx_power_dbm: number
  users: number
  util_pct: number
}
export interface WirelessView {
  id: string
  name: string
  location: string
  status: string
  model: string
  ip: string
  radio_2g: RadioView
  radio_5g: RadioView
  users_total: number
  rx_rssi_dbm: number
  noise_floor_dbm: number
  uptime_days: number
}
export interface NetworkWirelessSummary {
  total: number
  online: number
  users: number
  aps: WirelessView[]
  avgRssi: number
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
  total_switches?: number
  online_switches?: number
  offline_switches?: number
  total_ports?: number
  up_ports?: number
  down_ports?: number
  overall_port_rate?: number
  total_traffic_bps?: number
  avg_cpu_pct?: number
  avg_mem_pct?: number
  switches?: RawSwitch[]
  ping_targets?: Array<{
    target: string
    name?: string
    category?: string
    rtt_min_ms?: number
    rtt_avg_ms?: number
    rtt_max_ms?: number
    loss_pct?: number
    jitter_ms?: number
    status?: string
  }>
  avg_ping_rtt_ms?: number
  avg_ping_loss_pct?: number
  worst_ping_target?: { target: string; rtt_ms?: number; loss_pct?: number; status?: string } | null
  bw_topn?: Array<{
    rank?: number
    name?: string
    device?: string
    direction?: string
    util_pct?: number
    traffic_bps?: number
    capacity_mbps?: number
    alert?: boolean
  }>
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
  fallbackBw: number | null,
): NetworkSystemSummary {
  const online = devices.filter((d) => d.status === 'running').length
  const pings = devices.map((d) => d.pingMs).filter((v): v is number => v != null)
  const bws = devices.map((d) => d.bwUtilization).filter((v): v is number => v != null)
  const avgPing =
    pings.length > 0
      ? Number((pings.reduce((a, b) => a + b, 0) / pings.length).toFixed(1))
      : fallbackPing
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
  const switchSummary = buildSummary(
    switches,
    null,
    Number(raw.overall_port_rate?.toFixed(1)) ?? null,
  )

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

  const routerSummary = buildSummary(
    routers,
    switchSummary.avgPingMs,
    switchSummary.avgBwUtilization,
  )
  const firewallSummary = buildSummary(
    firewalls,
    switchSummary.avgPingMs,
    switchSummary.avgBwUtilization,
  )
  const wirelessSummary = buildSummary(
    wireless,
    switchSummary.avgPingMs,
    switchSummary.avgBwUtilization,
  )

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

// ---- 详细视图 (子系统完整数据) ----
function mapSwitchDetailed(raw: RawOverview): NetworkSwitchSummary {
  const switches: SwitchView[] = (raw.switches ?? []).map((sw: any) => ({
    id: sw.id,
    name: sw.name,
    ip: sw.ip,
    model: sw.model,
    role: sw.role,
    location: sw.location,
    status: sw.status,
    cpu_pct: Number(sw.cpu_pct) || 0,
    mem_pct: Number(sw.mem_pct) || 0,
    temp_c: Number(sw.temp_c) || 0,
    uptime_days: Number(sw.uptime_days) || 0,
    total_ports: Number(sw.total_ports) || 0,
    up_ports: Number(sw.up_ports) || 0,
    down_ports: Number(sw.down_ports) || 0,
    ports: (sw.ports ?? []).map((p: any) => ({
      name: p.name,
      alias: p.alias,
      status: p.status,
      speed_mbps: Number(p.speed_mbps) || 0,
      in_bps: Number(p.in_bps) || 0,
      out_bps: Number(p.out_bps) || 0,
      in_util_pct: Number(p.in_util_pct) || 0,
      out_util_pct: Number(p.out_util_pct) || 0,
      in_errors: Number(p.in_errors) || 0,
      out_errors: Number(p.out_errors) || 0,
      in_discards: Number(p.in_discards) || 0,
      tx_power_dbm: p.tx_power_dbm,
      rx_power_dbm: p.rx_power_dbm,
      optical_alarm: p.optical_alarm,
    })),
    trunks: (sw.trunks ?? []).map((t: any) => ({
      id: t.id,
      members: t.members ?? [],
      mode: t.mode,
      status: t.status,
      util_pct: Number(t.util_pct) || 0,
      traffic_bps: Number(t.traffic_bps) || 0,
    })),
    stack: sw.stack
      ? {
          enabled: true,
          topo: sw.stack.topo,
          members: sw.stack.members,
          master: sw.stack.master,
          status: sw.stack.status,
        }
      : null,
  }))
  const online = switches.filter((s) => s.status === 'online').length
  return {
    total: switches.length,
    online,
    offline: switches.length - online,
    totalPorts: Number(raw.total_ports) || 0,
    upPorts: Number(raw.up_ports) || 0,
    downPorts: Number(raw.down_ports) || 0,
    overallPortRate: Number(raw.overall_port_rate) || 0,
    totalTrafficBps: Number(raw.total_traffic_bps) || 0,
    avgCpu: Number(raw.avg_cpu_pct) || 0,
    avgMem: Number(raw.avg_mem_pct) || 0,
    switches,
    pingTargets: (raw.ping_targets ?? []).map((p: any) => ({
      target: p.target,
      name: p.name,
      category: p.category,
      rtt_min_ms: Number(p.rtt_min_ms) || 0,
      rtt_avg_ms: Number(p.rtt_avg_ms) || 0,
      rtt_max_ms: Number(p.rtt_max_ms) || 0,
      loss_pct: Number(p.loss_pct) || 0,
      jitter_ms: Number(p.jitter_ms) || 0,
      status: p.status,
    })),
    avgPingRttMs: Number(raw.avg_ping_rtt_ms) || 0,
    avgPingLossPct: Number(raw.avg_ping_loss_pct) || 0,
    worstPingTarget: String(raw.worst_ping_target ?? ''),
    bwTopN: (raw.bw_topn ?? []).map((b: any) => ({
      rank: Number(b.rank),
      name: b.name,
      device: b.device,
      direction: b.direction,
      util_pct: Number(b.util_pct) || 0,
      traffic_bps: Number(b.traffic_bps) || 0,
      capacity_mbps: Number(b.capacity_mbps) || 0,
      alert: Boolean(b.alert),
    })),
  }
}
function mapRouterDetailed(raw: any): NetworkRouterSummary {
  const routers: RouterView[] = (raw.routers ?? []).map((r: any) => ({
    id: r.id,
    name: r.name,
    ip: r.ip,
    model: r.model,
    role: r.role,
    location: r.location,
    status: r.status,
    cpu_pct: Number(r.cpu_pct) || 0,
    mem_pct: Number(r.mem_pct) || 0,
    temp_c: Number(r.temp_c) || 0,
    uptime_days: Number(r.uptime_days) || 0,
    throughput_bps: Number(r.throughput_bps) || 0,
    sessions: Number(r.sessions) || 0,
    bgp_state: r.bgp_state,
    ospf_neighbors: Number(r.ospf_neighbors) || 0,
    routes_total: Number(r.routes_total) || 0,
    protocols: (r.protocols ?? []).map((p: any) => ({
      name: p.name,
      peer_total: p.peer_total,
      neighbor_total: p.neighbor_total,
      area: p.area,
      peer_up: p.peer_up,
      neighbor_up: p.neighbor_up,
      state: p.state,
      routes: Number(p.routes) || 0,
      desc: p.desc,
      flake: Number(p.flake) || 0,
    })),
  }))
  const online = routers.filter((r) => r.status === 'online').length
  return {
    total: routers.length,
    online,
    routers,
    avgThroughputBps: routers.length
      ? routers.reduce((s, r) => s + r.throughput_bps, 0) / routers.length
      : 0,
    totalSessions: routers.reduce((s, r) => s + r.sessions, 0),
    bgpState: routers.length ? routers[0].bgp_state : '-',
    routesTotal: routers.reduce((s, r) => s + r.routes_total, 0),
  }
}
function mapFirewallDetailed(raw: any): NetworkFirewallSummary {
  const firewalls: FirewallView[] = (raw.firewalls ?? []).map((f: any) => ({
    id: f.id,
    name: f.name,
    ip: f.ip,
    model: f.model,
    location: f.location,
    status: f.status,
    cpu_pct: Number(f.cpu_pct) || 0,
    mem_pct: Number(f.mem_pct) || 0,
    temp_c: Number(f.temp_c) || 0,
    uptime_days: Number(f.uptime_days) || 0,
    concurrent_sessions: Number(f.concurrent_sessions) || 0,
    session_rate: Number(f.session_rate) || 0,
    policy_total: Number(f.policy_total) || 0,
    policy_hit_top: (f.policy_hit_top ?? []).map((p: any) => ({
      name: p.name,
      hits: Number(p.hits) || 0,
    })),
    throughput_bps: Number(f.throughput_bps) || 0,
    threat_blocked: Number(f.threat_blocked) || 0,
    vpn_tunnels: Number(f.vpn_tunnels) || 0,
  }))
  const online = firewalls.filter((f) => f.status === 'online').length
  return {
    total: firewalls.length,
    online,
    firewalls,
    concurrentSessions: firewalls.reduce((s, f) => s + f.concurrent_sessions, 0),
    policyTotal: firewalls.reduce((s, f) => s + f.policy_total, 0),
    threatBlocked: firewalls.reduce((s, f) => s + f.threat_blocked, 0),
    vpnTunnels: firewalls.reduce((s, f) => s + f.vpn_tunnels, 0),
  }
}
function mapWirelessDetailed(raw: any): NetworkWirelessSummary {
  const aps: WirelessView[] = (raw.wireless ?? []).map((w: any) => ({
    id: w.id,
    name: w.name,
    location: w.location,
    status: w.status,
    model: w.model,
    ip: w.ip,
    radio_2g: {
      status: w.radio_2g?.status ?? 'up',
      channel: Number(w.radio_2g?.channel) || 0,
      tx_power_dbm: Number(w.radio_2g?.tx_power_dbm) || 0,
      users: Number(w.radio_2g?.users) || 0,
      util_pct: Number(w.radio_2g?.util_pct) || 0,
    },
    radio_5g: {
      status: w.radio_5g?.status ?? 'up',
      channel: Number(w.radio_5g?.channel) || 0,
      tx_power_dbm: Number(w.radio_5g?.tx_power_dbm) || 0,
      users: Number(w.radio_5g?.users) || 0,
      util_pct: Number(w.radio_5g?.util_pct) || 0,
    },
    users_total: Number(w.users_total) || 0,
    rx_rssi_dbm: Number(w.rx_rssi_dbm) || 0,
    noise_floor_dbm: Number(w.noise_floor_dbm) || 0,
    uptime_days: Number(w.uptime_days) || 0,
  }))
  const online = aps.filter((a) => a.status === 'online').length
  return {
    total: aps.length,
    online,
    users: aps.reduce((s, a) => s + a.users_total, 0),
    aps,
    avgRssi: aps.length
      ? Number((aps.reduce((s, a) => s + a.rx_rssi_dbm, 0) / aps.length).toFixed(1))
      : 0,
  }
}

export function getNetworkSwitchesDetailed(): Promise<NetworkSwitchSummary> {
  return request
    .get<unknown, RawOverview>('/api/network/overview')
    .then((raw) => mapSwitchDetailed(raw ?? ({} as RawOverview)))
    .catch(() => mapSwitchDetailed({}))
}
export function getNetworkRoutersDetailed(): Promise<NetworkRouterSummary> {
  return request
    .get<unknown, any>('/api/network/overview')
    .then((raw) => mapRouterDetailed(raw ?? {}))
    .catch(() => mapRouterDetailed({}))
}
export function getNetworkFirewallsDetailed(): Promise<NetworkFirewallSummary> {
  return request
    .get<unknown, any>('/api/network/overview')
    .then((raw) => mapFirewallDetailed(raw ?? {}))
    .catch(() => mapFirewallDetailed({}))
}
export function getNetworkWirelessDetailed(): Promise<NetworkWirelessSummary> {
  return request
    .get<unknown, any>('/api/network/overview')
    .then((raw) => mapWirelessDetailed(raw ?? {}))
    .catch(() => mapWirelessDetailed({}))
}
