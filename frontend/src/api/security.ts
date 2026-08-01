import request from './request'

// ---- 后端返回的真实结构 (与 generator cctv / acs / ids / fire 对齐) ----
// cctv(): { total, online, offline, nvr, zones:[{id,cams,offline}], ai, events:[{ts,zone,desc,lv}] }
// acs():  { doors, online, openAbnormal, todayEvents, denied, visitors, areas:[{id,auth,doors}], events:[{ts,door,person,act,lv}] }
// ids():  { perimeter:{type,zones,armed,alarm}, indoor:{ir,glass,armed,state}, events:[{ts,zone,desc,lv}] }
// fire(): { hostState, loops, points, faultPoints, detectors:[{type,n,fault}], events:[{ts,desc,lv}] }

export interface SecurityDeviceView {
  id: number
  code: string
  name: string
  roomName: string
  status: string
  lastEvent: string | null
  lastEventTime: string | null
  commissionedOn: string | null
  healthScore: number | null
}

export interface SecuritySystemSummary {
  total: number
  online: number
  eventsToday: number
  alertsToday: number
  devices: SecurityDeviceView[]
}

export interface SecurityOverview {
  totalEquipment: number
  onlineCount: number
  faultCount: number
  warningCount: number
  cctv: SecuritySystemSummary
  acs: SecuritySystemSummary
  ids: SecuritySystemSummary
  fire: SecuritySystemSummary
}

interface RawItem {
  [k: string]: unknown
}

interface RawEvent {
  ts?: unknown
  zone?: unknown
  door?: unknown
  desc?: unknown
  act?: unknown
  person?: unknown
  lv?: unknown
}

function num(v: unknown, fallback = 0): number {
  const n = Number(v)
  return Number.isFinite(n) ? n : fallback
}

/** 统计事件中的告警条数 (lv 为 r/红=严重, a/琥珀=警告)。 */
function countAlerts(events: RawEvent[]): number {
  return events.filter((e) => {
    const lv = String(e.lv ?? '').toLowerCase()
    return lv === 'r' || lv === 'a' || lv === 'crit' || lv === 'warn'
  }).length
}

/** 取最近一条事件的描述与时间, 挂到设备行上展示。 */
function lastEventOf(events: RawEvent[], match?: (e: RawEvent) => boolean): {
  lastEvent: string | null
  lastEventTime: string | null
} {
  const list = match ? events.filter(match) : events
  const e = list[0]
  if (!e) return { lastEvent: null, lastEventTime: null }
  const desc = e.desc ?? e.act ?? e.person
  return {
    lastEvent: desc != null ? String(desc) : null,
    lastEventTime: e.ts != null ? String(e.ts) : null,
  }
}

/** 视频监控: 以安防分区作为设备行, 展示各区摄像机在线情况。 */
function mapCctv(raw: RawItem): SecuritySystemSummary {
  const zones = (raw?.zones as RawItem[]) ?? []
  const events = (raw?.events as RawEvent[]) ?? []
  const devices: SecurityDeviceView[] = zones.map((z, i) => {
    const cams = num(z.cams)
    const offline = num(z.offline)
    const zoneId = String(z.id ?? `Z-${i + 1}`)
    return {
      id: i + 1,
      code: `${cams - offline}/${cams} 在线`,
      name: zoneId,
      roomName: zoneId,
      status: offline === 0 ? 'online' : offline >= cams ? 'fault' : 'warning',
      ...lastEventOf(events, (e) => String(e.zone ?? '') === zoneId),
      commissionedOn: null,
      healthScore: null,
    }
  })
  const total = num(raw?.total, devices.reduce((s, _d, i) => s + num(zones[i]?.cams), 0))
  const online = num(raw?.online, total - num(raw?.offline))
  return { total, online, eventsToday: events.length, alertsToday: countAlerts(events), devices }
}

/** 门禁: 以授权区域作为设备行。 */
function mapAcs(raw: RawItem): SecuritySystemSummary {
  const areas = (raw?.areas as RawItem[]) ?? []
  const events = (raw?.events as RawEvent[]) ?? []
  const devices: SecurityDeviceView[] = areas.map((a, i) => {
    const areaId = String(a.id ?? `A-${i + 1}`)
    return {
      id: i + 1,
      code: `${num(a.doors)} 门 / ${a.auth ?? '-'}`,
      name: areaId,
      roomName: areaId,
      status: 'online',
      ...lastEventOf(events, (e) => String(e.door ?? '').includes(areaId)),
      commissionedOn: null,
      healthScore: null,
    }
  })
  const total = num(raw?.doors)
  return {
    total,
    online: num(raw?.online, total),
    eventsToday: num(raw?.todayEvents, events.length),
    alertsToday: num(raw?.denied, countAlerts(events)),
    devices,
  }
}

/** 防入侵: 周界与室内探测汇总为两条设备行。 */
function mapIds(raw: RawItem): SecuritySystemSummary {
  const per = (raw?.perimeter as RawItem) ?? {}
  const indoor = (raw?.indoor as RawItem) ?? {}
  const events = (raw?.events as RawEvent[]) ?? []
  const perZones = num(per.zones)
  const perArmed = num(per.armed)
  const perAlarm = num(per.alarm)
  const irCount = num(indoor.ir)
  const glassCount = num(indoor.glass)
  const devices: SecurityDeviceView[] = [
    {
      id: 1,
      code: `${perArmed}/${perZones} 布防`,
      name: String(per.type ?? '周界探测'),
      roomName: '园区周界',
      status: perAlarm > 0 ? 'fault' : 'online',
      ...lastEventOf(events),
      commissionedOn: null,
      healthScore: null,
    },
    {
      id: 2,
      code: `红外 ${irCount} / 玻璃破碎 ${glassCount}`,
      name: String(indoor.armed ?? '室内探测'),
      roomName: '楼内区域',
      status: 'online',
      lastEvent: indoor.state != null ? String(indoor.state) : null,
      lastEventTime: null,
      commissionedOn: null,
      healthScore: null,
    },
  ]
  const total = perZones + irCount + glassCount
  return {
    total,
    online: total - perAlarm,
    eventsToday: events.length,
    alertsToday: perAlarm + countAlerts(events),
    devices,
  }
}

/** 消防: 以探测器类型作为设备行。 */
function mapFire(raw: RawItem): SecuritySystemSummary {
  const detectors = (raw?.detectors as RawItem[]) ?? []
  const events = (raw?.events as RawEvent[]) ?? []
  const devices: SecurityDeviceView[] = detectors.map((d, i) => {
    const fault = num(d.fault)
    const n = num(d.n)
    return {
      id: i + 1,
      code: `${n - fault}/${n} 正常`,
      name: String(d.type ?? `探测器-${i + 1}`),
      roomName: `${num(raw?.loops)} 回路`,
      status: fault === 0 ? 'online' : 'warning',
      lastEvent: fault > 0 ? `${fault} 个故障点` : null,
      lastEventTime: null,
      commissionedOn: null,
      healthScore: null,
    }
  })
  const total = num(raw?.points)
  const faultPoints = num(raw?.faultPoints)
  return {
    total,
    online: total - faultPoints,
    eventsToday: events.length,
    alertsToday: faultPoints + countAlerts(events),
    devices,
  }
}

// ---- API 调用 ----

function emptySummary(): SecuritySystemSummary {
  return { total: 0, online: 0, eventsToday: 0, alertsToday: 0, devices: [] }
}

function fetchMapped(
  url: string,
  mapper: (raw: RawItem) => SecuritySystemSummary,
): Promise<SecuritySystemSummary> {
  return request
    .get<unknown, RawItem>(url)
    .then((raw) => mapper(raw ?? {}))
    .catch(() => emptySummary())
}

export function getSecurityCctv(): Promise<SecuritySystemSummary> {
  return fetchMapped('/api/security/cctv', mapCctv)
}

export function getSecurityAcs(): Promise<SecuritySystemSummary> {
  return fetchMapped('/api/security/acs', mapAcs)
}

export function getSecurityIds(): Promise<SecuritySystemSummary> {
  return fetchMapped('/api/security/ids', mapIds)
}

export function getSecurityFire(): Promise<SecuritySystemSummary> {
  return fetchMapped('/api/security/fire', mapFire)
}

export function getSecurityOverview(): Promise<SecurityOverview> {
  return Promise.all([
    getSecurityCctv(),
    getSecurityAcs(),
    getSecurityIds(),
    getSecurityFire(),
  ]).then(([cctv, acs, ids, fire]) => {
    const all = [cctv, acs, ids, fire]
    const devices = all.flatMap((s) => s.devices)
    return {
      totalEquipment: all.reduce((s, x) => s + x.total, 0),
      onlineCount: all.reduce((s, x) => s + x.online, 0),
      faultCount: devices.filter((d) => d.status === 'fault').length,
      warningCount: devices.filter((d) => d.status === 'warning').length,
      cctv,
      acs,
      ids,
      fire,
    }
  })
}
