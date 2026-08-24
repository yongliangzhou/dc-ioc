/* ================= 数据中心 IOC — 前端模拟数据层 (Mock 兜底) =================
 * 移植自 dc-ioc/js/data.js。当后端不可达 (网络错误) 时, 由 request 层兜底返回,
 * 使驾驶舱各业务域页在脱离后端时仍展示"之前的模拟数据"。
 * 业务域视图直接消费 DC.* (camelCase); 驾驶舱概览由 dashboardOverview() 输出 snake_case。
 * ========================================================================== */

import { THING_MODELS } from '@/constants/thingModels'
import type { ThingModel } from '@/api/thingModel'
import type { RecognizeResp, ServerItem, UCell, UConflict, UPositionView } from '@/types'
import type { FaultImpactReq, FaultImpactResp, FaultSourceList, FaultSourceNode } from '@/types'
import type {
  AlarmEngineState,
  AlarmEvent,
  AlarmHistoryQuery,
  AlarmHistoryResponse,
  AlarmRuleDef,
  Cabinet,
  CabinetMetrics,
  DeviceListResponse,
  Equipment,
  EquipmentMetrics,
  ExternalDeviceView,
  MetricHistoryResponse,
  MetricQuality,
  MetricRecordView,
  MetricRealtimeResponse,
  Paginated,
  ThingModelDef,
  KnowledgeItem,
} from '@/types'

/* v2 演示设备列表 (与 @/api 中 DemoDeviceItem/DemoDeviceList 同构, 本地定义避免循环依赖) */
interface DemoDeviceItem {
  device_id: string
  name: string
  model: string
  ip: string
  protocol: string
  online: boolean
  last_seen?: string | null
  metric_count: number
}
interface DemoDeviceList {
  total: number
  online: number
  offline: number
  total_metrics: number
  items: DemoDeviceItem[]
}

const rnd = (a: number, b: number, f = 1) => +(a + Math.random() * (b - a)).toFixed(f)
const pick = <T>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)]
const series = (n: number, a: number, b: number) => Array.from({ length: n }, () => rnd(a, b))

// 状态/故障/保护项 (name + 状态或数值 + 严重级别)
interface StatusItem {
  name: string
  state?: string
  value?: string
  level: string
}

// Mock 接口查询参数
interface MockQuery {
  domain?: string
  protocol?: string
  room?: string
  page?: number | string
  size?: number | string
  [k: string]: unknown
}

/* 柴发并机机组 — 补齐进线/出线三相电参量、开关分合、故障与保护装置 */
function buildGensetUnits() {
  const states = ['运行', '运行', '运行', '运行', '运行', '备用', '维保', '运行']
  const PROT = [
    '过速保护',
    '低油压保护',
    '高水温保护',
    '过电流保护',
    '过电压保护',
    '欠电压保护',
    '逆功率保护',
    '接地故障保护',
    '差动保护',
    '失磁保护',
    '启动失败保护',
    '紧急停机',
  ]
  return states.map((st, i) => {
    const running = st === '运行'
    const breaker = running ? '合闸' : '分闸'
    const incomer = running ? '合闸' : '分闸'
    let ua = 0,
      ub = 0,
      uc = 0,
      u = 0,
      ia = 0,
      ib = 0,
      ic = 0,
      iAvg = 0,
      p = 0,
      q = 0,
      pf = 0,
      freq = 0,
      energy = 0,
      rpm = 0,
      waterT = 0,
      oilP = 0
    let faults: StatusItem[] = []
    let prots: StatusItem[] = []
    if (running) {
      const load = rnd(62, 95, 0)
      const uBase = rnd(10.4, 10.6, 2)
      ua = +(uBase + rnd(-0.05, 0.05, 2)).toFixed(2)
      ub = +(uBase + rnd(-0.05, 0.05, 2)).toFixed(2)
      uc = +(uBase + rnd(-0.05, 0.05, 2)).toFixed(2)
      u = +((ua + ub + uc) / 3).toFixed(2)
      p = Math.round(((2500 * load) / 100) * rnd(0.96, 1.04))
      pf = +rnd(0.82, 0.92, 2).toFixed(2)
      q = Math.round(p * Math.tan(Math.acos(pf)))
      freq = +rnd(49.9, 50.1, 1).toFixed(2)
      const iBase = Math.round(p / (Math.sqrt(3) * uBase * pf))
      ia = iBase + rnd(-6, 6, 0)
      ib = iBase + rnd(-6, 6, 0)
      ic = iBase + rnd(-6, 6, 0)
      iAvg = Math.round((ia + ib + ic) / 3)
      energy = rnd(18600, 64200, 0)
      rpm = 1500 + rnd(-3, 3, 0)
      waterT = rnd(82, 92, 0)
      oilP = +rnd(3.6, 5.2, 1).toFixed(1)
      prots = PROT.map((n) => ({ name: n, state: '投入', level: 'g' }))
    } else if (st === '维保') {
      waterT = rnd(38, 46, 0)
      energy = rnd(16000, 30000, 0)
      faults = [
        { name: '维保中', value: '待检', level: 'a' },
        { name: '启动电池', value: '电压偏低', level: 'a' },
      ]
      prots = PROT.map((n) => {
        if (n === '过速保护') return { name: n, state: '退出', level: 'a' }
        if (n === '启动失败保护') return { name: n, state: '试验', level: 'b' }
        return { name: n, state: '投入', level: 'g' }
      })
    } else {
      waterT = rnd(38, 46, 0)
      energy = rnd(20000, 40000, 0)
      prots = PROT.map((n) => ({ name: n, state: '投入', level: 'g' }))
    }
    return {
      id: `DG-${String(i + 1).padStart(2, '0')}`,
      state: st,
      breaker,
      incomer,
      ua,
      ub,
      uc,
      u,
      ia,
      ib,
      ic,
      i: iAvg,
      p,
      q,
      pf,
      freq,
      energy,
      rpm,
      waterT,
      oilP,
      battU: +rnd(25.6, 27.2, 1).toFixed(1),
      heater: '投入',
      startCnt: rnd(42, 88, 0),
      runHrs: rnd(220, 480, 0),
      faults,
      protections: prots,
    }
  })
}

/* 燃油监控 — 补齐油位四段开关、阀门分合、油泵告警、保护装置 */
function buildFuel() {
  const sw = (level: number) => {
    const thr: [string, string, number, 'g' | 'a' | 'r' | 'b'][] = [
      ['低低位 LL', 'LL', 5, 'r'],
      ['低位 L', 'L', 12, 'a'],
      ['高位 H', 'H', 88, 'a'],
      ['高高位 HH', 'HH', 95, 'r'],
    ]
    return thr.map(([name, th, t, sev]) => {
      const trig =
        ((th === 'LL' || th === 'L') && level <= t) || ((th === 'H' || th === 'HH') && level >= t)
      return { name, th, state: trig ? '闭合' : '断开', level: trig ? sev : 'g' } as const
    })
  }
  const MAIN_PROT = [
    '高液位保护',
    '低液位保护',
    '低低位联锁停泵',
    '渗漏检测保护',
    '静电接地保护',
    '温度高保护',
    '高低液位联锁',
  ]
  const DAY_PROT = ['高液位保护', '低液位保护', '渗漏检测保护', '温度高保护', '进油阀联锁']
  const PUMP_PROT = [
    '过载保护',
    '短路保护',
    '干转保护',
    '轴承温度高保护',
    '密封泄漏保护',
    '出口过压保护',
  ]
  const mainProts = (level: number) =>
    MAIN_PROT.map((n) =>
      n === '高液位保护' && level >= 88
        ? { name: n, state: '动作', level: 'a' as const }
        : { name: n, state: '投入', level: 'g' },
    )

  const mainTanks = [
    {
      id: '地埋主油罐 #1',
      cap: 50000,
      level: 86,
      t: 21.3,
      water: '无',
      leak: '正常',
      valves: [
        { name: '进油阀', state: '闭合', level: 'g' },
        { name: '出油阀', state: '开启', level: 'g' },
      ],
      switches: sw(86),
      protections: mainProts(86),
    },
    {
      id: '地埋主油罐 #2',
      cap: 50000,
      level: 90,
      t: 21.1,
      water: '无',
      leak: '正常',
      valves: [
        { name: '进油阀', state: '闭合', level: 'g' },
        { name: '出油阀', state: '开启', level: 'g' },
      ],
      switches: sw(90),
      protections: mainProts(90),
    },
  ]
  const dayTanks = Array.from({ length: 8 }, (_, i) => {
    const lv = rnd(78, 96, 0)
    return {
      id: `日用油箱 DT-${i + 1}`,
      cap: 1000,
      level: lv,
      leak: '正常',
      valve: { name: '进油阀', state: '开启', level: 'g' },
      switches: sw(lv),
      protections: DAY_PROT.map((n) => ({ name: n, state: '投入', level: 'g' })),
    }
  })
  const pumpStates: [string, string, string][] = [
    ['输油泵 P-1', '运行', '自动'],
    ['输油泵 P-2', '运行', '自动'],
    ['输油泵 P-3(备)', '待机', '自动'],
  ]
  const pumps = pumpStates.map(([pid, st, mode], idx) => {
    const alarms = ['轴承温度', '电机电流', '密封泄漏', '出口压力'].map((n) => ({
      name: n,
      value: '正常',
      level: 'g',
    }))
    if (idx === 1) alarms[0] = { name: '轴承温度', value: '偏高 78℃', level: 'a' as const }
    const prots = PUMP_PROT.map((n) => ({ name: n, state: '投入', level: 'g' }))
    if (idx === 1) {
      const p = prots.find((x) => x.name === '轴承温度高保护')
      if (p) {
        p.state = '动作'
        p.level = 'a' as const
      }
    }
    return { id: pid, state: st, mode, alarms, protections: prots }
  })
  return {
    mainTanks,
    dayTanks,
    pumps,
    endurance: 11.6,
    contract: '2h 应急供油合同 ×2 家',
    pipeline: { pressure: 0.32, state: '正常', tracing: '伴热正常' },
  }
}

/* 电池监控 — 单体级电压/温度/内阻 + 总电压/充放电电流状态 */
function buildBattery() {
  const specs: [string, string, number, number, number][] = [
    ['UPS-A 电池组1', '铅酸 12V×40×4串', 40, 13.6, 100],
    ['UPS-A 电池组2', '铅酸 12V×40×4串', 40, 13.6, 100],
    ['UPS-B 电池组1', '铅酸 12V×40×4串', 40, 13.6, 100],
    ['HVDC-01 电池组', '磷酸铁锂 240V', 80, 3.35, 98],
    ['HVDC-02 电池组', '磷酸铁锂 240V', 80, 3.35, 99],
    ['HVDC-03 电池组', '磷酸铁锂 240V', 80, 3.35, 97],
  ]
  const groups = specs.map(([gid, gtype, ncell, vbase, soc]) => {
    const isLi = gtype.includes('磷酸铁锂')
    const cells = Array.from({ length: ncell }, (_, c) => {
      let u: number,
        ir: number,
        t: number,
        level: 'g' | 'a' | 'r' | 'b' = 'g'
      if (isLi) {
        u = +(vbase + rnd(-0.08, 0.08, 3)).toFixed(3)
        ir = +rnd(0.25, 0.55, 2).toFixed(2)
        t = +rnd(23, 28, 1).toFixed(1)
      } else {
        u = +(vbase + rnd(-0.15, 0.15, 2)).toFixed(2)
        ir = +rnd(5.0, 8.5, 2).toFixed(2)
        t = +rnd(22, 27, 1).toFixed(1)
      }
      if ((isLi && ir > 0.5) || (!isLi && ir > 8.0)) level = 'a'
      return { no: `#${String(c + 1).padStart(2, '0')}`, u, t, ir, level }
    })
    if (gid === 'HVDC-03 电池组') {
      cells[27].ir = 0.62
      cells[27].level = 'a'
    }
    const totalU = +cells.reduce((a, c) => a + c.u, 0).toFixed(1)
    const maxT = Math.max(...cells.map((c) => c.t))
    const worst = cells.reduce((w, c) => (c.ir > w.ir ? c : w), cells[0])
    const irConcl = gid === 'HVDC-03 电池组' ? '偏高' : '正常'
    return {
      id: gid,
      type: gtype,
      soc,
      u: totalU,
      i: +rnd(0.1, 0.4, 2).toFixed(2),
      cdState: '浮充',
      maxT,
      worstCell: `${worst.no} ${worst.u}V`,
      ir: irConcl,
      state: '浮充',
      cells,
    }
  })
  const cellAlarms = [
    { g: 'HVDC-03 电池组', cell: '#28', item: '内阻偏高 (+18%)', lv: '预警', ts: '07-21 03:12' },
  ]
  return { groups, backupMin: 15, lastDischarge: '2026-06-30 核容放电 30% · 通过', cellAlarms }
}

export const DC = {
  name: '华东-杭州 EC1 数据中心',
  buildings: 2,
  rooms: 12,
  racks: 3600,
  itDesign: 36,

  /* ---------- 全局 KPI ---------- */
  kpi: {
    pue: 1.247,
    wue: 1.62,
    itLoad: 24.6,
    totalLoad: 30.7,
    coolLoad: 4.9,
    availability: 99.9995,
    alarms: { crit: 1, warn: 6, info: 14 },
    freeCoolHours: 4382,
  },

  /* ---------- 暖通 · 冷源系统 ---------- */
  chillerPlant: {
    mode: '部分自然冷 (预冷模式)',
    modes: ['完全电制冷', '部分自然冷 (预冷模式)', '完全自然冷'],
    outdoorT: 18.4,
    outdoorRH: 62,
    wetBulb: 14.1,
    supplyT: 15.2,
    returnT: 20.8,
    targetSupplyT: 15.0,
    flow: 2860,
    coolingCap: 18.6,
    plr: 68,
    storageTank: { level: 92, dischargeMin: 15, mode: '保冷备用', capacity: 3000 },
    chillers: [
      {
        id: 'CH-01',
        state: '运行',
        load: 78,
        cop: 6.42,
        evapT: 14.9,
        condT: 29.3,
        current: 76,
        runHrs: 12480,
      },
      {
        id: 'CH-02',
        state: '运行',
        load: 72,
        cop: 6.31,
        evapT: 15.1,
        condT: 29.6,
        current: 71,
        runHrs: 11923,
      },
      {
        id: 'CH-03',
        state: '待机',
        load: 0,
        cop: 0,
        evapT: '-',
        condT: '-',
        current: 0,
        runHrs: 10102,
      },
      {
        id: 'CH-04',
        state: '检修',
        load: 0,
        cop: 0,
        evapT: '-',
        condT: '-',
        current: 0,
        runHrs: 13877,
      },
    ],
    towers: [
      { id: 'CT-01', state: '运行', fanHz: 38, outT: 19.2 },
      { id: 'CT-02', state: '运行', fanHz: 38, outT: 19.4 },
      { id: 'CT-03', state: '运行', fanHz: 35, outT: 19.1 },
      { id: 'CT-04', state: '待机', fanHz: 0, outT: '-' },
    ],
    pumps: {
      chw: [
        { id: 'CHWP-01', state: '运行', hz: 42, kw: 55 },
        { id: 'CHWP-02', state: '运行', hz: 42, kw: 54 },
        { id: 'CHWP-03', state: '待机', hz: 0, kw: 0 },
      ],
      cw: [
        { id: 'CWP-01', state: '运行', hz: 44, kw: 75 },
        { id: 'CWP-02', state: '运行', hz: 44, kw: 74 },
        { id: 'CWP-03', state: '待机', hz: 0, kw: 0 },
      ],
    },
    hex: [
      {
        id: 'HEX-01',
        state: '投入',
        eff: 93,
        priIn: 16.8,
        priOut: 14.6,
        secIn: 13.2,
        secOut: 15.9,
      },
      {
        id: 'HEX-02',
        state: '投入',
        eff: 92,
        priIn: 16.9,
        priOut: 14.7,
        secIn: 13.3,
        secOut: 16.0,
      },
    ],
    valves: [
      { id: 'V-101 冷机侧电动阀', pos: 100, state: '开' },
      { id: 'V-201 板换侧电动阀', pos: 100, state: '开' },
      { id: 'V-301 蓄冷罐放冷阀', pos: 0, state: '关' },
      { id: 'V-401 旁通调节阀', pos: 18, state: '调节' },
    ],
    staging: {
      rule: '供水温度 > 设定+1.0℃ 持续 5min 加机；PLR < 45% 持续 15min 减机',
      lastAction: '10:42 CH-02 自动加机(负载爬升)',
      next: '—',
    },
    tempTrend: series(48, 14.6, 15.8),
    loadTrend: series(48, 55, 80),
  },

  /* ---------- 暖通 · 空调末端 ---------- */
  crac: {
    summary: {
      total: 96,
      running: 78,
      standby: 14,
      fault: 2,
      maint: 2,
      avgSupply: 18.3,
      avgReturn: 27.9,
    },
    rooms: Array.from({ length: 12 }, (_, i) => ({
      id: `包间 R${String(i + 1).padStart(2, '0')}`,
      coldAisle: rnd(21.5, 24.5),
      hotAisle: rnd(31, 36),
      rh: rnd(42, 58, 0),
      cracRun: pick([6, 7, 8]),
      cracN: 8,
      state: '正常',
    })),
    units: Array.from({ length: 10 }, (_, i) => ({
      id: `CRAC-${String(i + 1).padStart(2, '0')}`,
      room: `R${String((i % 5) + 1).padStart(2, '0')}`,
      type: i % 3 === 0 ? '列间空调' : '房间级精密空调',
      state: i === 7 ? '故障' : i === 4 ? '待机' : '运行',
      supplyT: i === 7 ? '-' : rnd(17.5, 19.5),
      returnT: i === 7 ? '-' : rnd(26, 30),
      fan: i === 7 || i === 4 ? 0 : rnd(60, 90, 0),
      valve: i === 7 || i === 4 ? 0 : rnd(35, 85, 0),
    })),
    fresh: [
      { id: 'FAU-01', state: '运行', supplyT: 20.1, rh: 55, co2: 520, filterDp: 86 },
      { id: 'FAU-02', state: '运行', supplyT: 20.3, rh: 54, co2: 545, filterDp: 92 },
      { id: 'FAU-03', state: '待机', supplyT: '-', rh: '-', co2: '-', filterDp: 44 },
    ],
    humid: [
      { id: 'HUM-01 恒湿机', state: '运行', rh: 51, mode: '加湿' },
      { id: 'HUM-02 恒湿机', state: '运行', rh: 49, mode: '除湿' },
      { id: 'HUM-03 恒湿机', state: '待机', rh: '-', mode: '-' },
    ],
    funcRooms: [
      { id: '电池室 A', t: 24.2, rh: 48 },
      { id: '电池室 B', t: 24.6, rh: 47 },
      { id: 'UPS 室', t: 25.1, rh: 45 },
      { id: '网络汇聚间', t: 23.8, rh: 50 },
      { id: '消防控制室', t: 25.4, rh: 52 },
      { id: '柴发机房', t: 28.9, rh: 55 },
    ],
  },

  /* ---------- 电力 · 10KV 中压 ---------- */
  hv: {
    scheme: '两路市电 + 母联备自投 (单母线分段)',
    incomers: [
      {
        id: '10KV 1# 进线',
        src: '城东 220KV 变电站',
        state: '合闸',
        breaker: '合闸',
        ua: 10.41,
        ub: 10.43,
        uc: 10.42,
        u: 10.42,
        ia: 388,
        ib: 383,
        ic: 387,
        i: 386,
        p: 6.62,
        q: 1.93,
        pf: 0.96,
        freq: 50.01,
        energy: 142860,
      },
      {
        id: '10KV 2# 进线',
        src: '城西 220KV 变电站',
        state: '合闸',
        breaker: '合闸',
        ua: 10.37,
        ub: 10.39,
        uc: 10.38,
        u: 10.38,
        ia: 374,
        ib: 369,
        ic: 372,
        i: 371,
        p: 6.35,
        q: 1.85,
        pf: 0.95,
        freq: 49.99,
        energy: 138420,
      },
    ],
    busTie: {
      id: '10KV 母联 QF-M',
      state: '分闸(热备用)',
      autoSwitch: '投入',
      mode: '备自投·自动',
    },
    ats: {
      logic: '任一进线失压 → 延时 2.5s 确认 → 跳故障进线 → 合母联 (先分后合)',
      lastTest: '2026-07-05 全停演练通过',
      switchTime: '1.82s',
    },
    feeders: [
      {
        id: 'F-01',
        load: '1# 变压器',
        state: '合闸',
        breaker: '合闸',
        ua: 10.41,
        ub: 10.42,
        uc: 10.43,
        ia: 124,
        ib: 120,
        ic: 122,
        p: 2.05,
        pf: 0.95,
        energy: 42150,
      },
      {
        id: 'F-02',
        load: '2# 变压器',
        state: '合闸',
        breaker: '合闸',
        ua: 10.4,
        ub: 10.41,
        uc: 10.42,
        ia: 120,
        ib: 117,
        ic: 118,
        p: 1.98,
        pf: 0.94,
        energy: 40780,
      },
      {
        id: 'F-03',
        load: '3# 变压器',
        state: '合闸',
        breaker: '合闸',
        ua: 10.42,
        ub: 10.43,
        uc: 10.44,
        ia: 128,
        ib: 124,
        ic: 126,
        p: 2.12,
        pf: 0.96,
        energy: 43890,
      },
      {
        id: 'F-04',
        load: '4# 变压器',
        state: '合闸',
        breaker: '合闸',
        ua: 10.39,
        ub: 10.4,
        uc: 10.41,
        ia: 116,
        ib: 112,
        ic: 114,
        p: 1.92,
        pf: 0.93,
        energy: 39620,
      },
      {
        id: 'F-05',
        load: '冷机房变',
        state: '合闸',
        breaker: '合闸',
        ua: 10.38,
        ub: 10.39,
        uc: 10.4,
        ia: 98,
        ib: 95,
        ic: 96,
        p: 1.61,
        pf: 0.92,
        energy: 33140,
      },
      {
        id: 'F-06',
        load: '备用',
        state: '分闸',
        breaker: '分闸',
        ua: 10.4,
        ub: 10.41,
        uc: 10.42,
        ia: 0,
        ib: 0,
        ic: 0,
        p: 0,
        pf: 0,
        energy: 0,
      },
    ],
    transformers: [
      {
        id: '1# 变压器 2500kVA',
        feeder: 'F-01',
        state: '运行',
        load: 61,
        uHigh: 10.42,
        iHigh: 122,
        uLow: 0.398,
        iLow: 1860,
        windingT: 78,
        oilT: 62,
        ambT: 26.5,
        humidity: 48,
        tap: 5,
        fan: '运行',
        signals: [
          { name: '运行状态', value: '运行', level: 'g' },
          { name: '高压断路器', value: '合闸', level: 'g' },
          { name: '低压断路器', value: '合闸', level: 'g' },
          { name: '轻瓦斯', value: '无', level: 'g' },
          { name: '重瓦斯', value: '无', level: 'g' },
          { name: '绕组超温', value: '无', level: 'g' },
          { name: '压力释放', value: '无', level: 'g' },
          { name: '冷却风机', value: '运行', level: 'g' },
          { name: '有载调压', value: '自动 5档', level: 'b' },
        ],
      },
      {
        id: '2# 变压器 2500kVA',
        feeder: 'F-02',
        state: '运行',
        load: 58,
        uHigh: 10.41,
        iHigh: 118,
        uLow: 0.397,
        iLow: 1795,
        windingT: 76,
        oilT: 60,
        ambT: 26.2,
        humidity: 47,
        tap: 5,
        fan: '运行',
        signals: [
          { name: '运行状态', value: '运行', level: 'g' },
          { name: '高压断路器', value: '合闸', level: 'g' },
          { name: '低压断路器', value: '合闸', level: 'g' },
          { name: '轻瓦斯', value: '无', level: 'g' },
          { name: '重瓦斯', value: '无', level: 'g' },
          { name: '绕组超温', value: '无', level: 'g' },
          { name: '压力释放', value: '无', level: 'g' },
          { name: '冷却风机', value: '运行', level: 'g' },
          { name: '有载调压', value: '自动 5档', level: 'b' },
        ],
      },
      {
        id: '3# 变压器 2500kVA',
        feeder: 'F-03',
        state: '运行',
        load: 63,
        uHigh: 10.43,
        iHigh: 126,
        uLow: 0.399,
        iLow: 1910,
        windingT: 81,
        oilT: 64,
        ambT: 26.8,
        humidity: 49,
        tap: 4,
        fan: '运行',
        signals: [
          { name: '运行状态', value: '运行', level: 'g' },
          { name: '高压断路器', value: '合闸', level: 'g' },
          { name: '低压断路器', value: '合闸', level: 'g' },
          { name: '轻瓦斯', value: '无', level: 'g' },
          { name: '重瓦斯', value: '无', level: 'g' },
          { name: '绕组超温', value: '预警', level: 'a' },
          { name: '压力释放', value: '无', level: 'g' },
          { name: '冷却风机', value: '运行', level: 'g' },
          { name: '有载调压', value: '自动 4档', level: 'b' },
        ],
      },
      {
        id: '4# 变压器 2500kVA',
        feeder: 'F-04',
        state: '运行',
        load: 55,
        uHigh: 10.4,
        iHigh: 114,
        uLow: 0.396,
        iLow: 1670,
        windingT: 74,
        oilT: 59,
        ambT: 26.1,
        humidity: 46,
        tap: 6,
        fan: '运行',
        signals: [
          { name: '运行状态', value: '运行', level: 'g' },
          { name: '高压断路器', value: '合闸', level: 'g' },
          { name: '低压断路器', value: '合闸', level: 'g' },
          { name: '轻瓦斯', value: '无', level: 'g' },
          { name: '重瓦斯', value: '无', level: 'g' },
          { name: '绕组超温', value: '无', level: 'g' },
          { name: '压力释放', value: '无', level: 'g' },
          { name: '冷却风机', value: '运行', level: 'g' },
          { name: '有载调压', value: '自动 6档', level: 'b' },
        ],
      },
      {
        id: '冷机房变 1600kVA',
        feeder: 'F-05',
        state: '运行',
        load: 52,
        uHigh: 10.39,
        iHigh: 96,
        uLow: 0.395,
        iLow: 1380,
        windingT: 71,
        oilT: 57,
        ambT: 27.3,
        humidity: 51,
        tap: 5,
        fan: '运行',
        signals: [
          { name: '运行状态', value: '运行', level: 'g' },
          { name: '高压断路器', value: '合闸', level: 'g' },
          { name: '低压断路器', value: '合闸', level: 'g' },
          { name: '轻瓦斯', value: '无', level: 'g' },
          { name: '重瓦斯', value: '无', level: 'g' },
          { name: '绕组超温', value: '无', level: 'g' },
          { name: '压力释放', value: '无', level: 'g' },
          { name: '冷却风机', value: '运行', level: 'g' },
          { name: '有载调压', value: '自动 5档', level: 'b' },
        ],
      },
    ],
    quality: { thdU: 2.1, thdI: 3.4, unbalance: 0.8 },
  },

  /* ---------- 电力 · 0.4KV 低压 ---------- */
  lv: {
    transformers: [
      {
        id: 'T1 2500KVA',
        load: 61,
        t: 78,
        state: '运行',
        u: 0.398,
        i: 1860,
        p: 1455,
        q: 430,
        pf: 0.96,
        freq: 50.02,
        energy: 28940,
        thdu: 2.3,
        thdi: 4.1,
      },
      {
        id: 'T2 2500KVA',
        load: 58,
        t: 76,
        state: '运行',
        u: 0.397,
        i: 1795,
        p: 1380,
        q: 410,
        pf: 0.96,
        freq: 50.01,
        energy: 27620,
        thdu: 2.2,
        thdi: 4.0,
      },
      {
        id: 'T3 2500KVA',
        load: 63,
        t: 81,
        state: '运行',
        u: 0.399,
        i: 1910,
        p: 1505,
        q: 450,
        pf: 0.96,
        freq: 50.02,
        energy: 30110,
        thdu: 2.5,
        thdi: 4.3,
      },
      {
        id: 'T4 2500KVA',
        load: 55,
        t: 74,
        state: '运行',
        u: 0.396,
        i: 1670,
        p: 1295,
        q: 380,
        pf: 0.96,
        freq: 50.0,
        energy: 25900,
        thdu: 2.1,
        thdi: 3.9,
      },
    ],
    upsGroups: [
      {
        id: 'UPS-A 组 (2N)',
        n: '4×600KVA',
        load: 47,
        uIn: 380,
        uOut: 380,
        mode: '在线双变换',
        bypass: '正常',
        state: '正常',
        iIn: 720,
        iOut: 700,
        p: 268,
        pf: 0.98,
        freq: 50.01,
        energyIn: 6420,
        thdu: 1.6,
        thdi: 3.2,
      },
      {
        id: 'UPS-B 组 (2N)',
        n: '4×600KVA',
        load: 45,
        uIn: 381,
        uOut: 380,
        mode: '在线双变换',
        bypass: '正常',
        state: '正常',
        iIn: 690,
        iOut: 672,
        p: 255,
        pf: 0.98,
        freq: 50.02,
        energyIn: 6110,
        thdu: 1.5,
        thdi: 3.0,
      },
    ],
    hvdc: [
      {
        id: 'HVDC-01',
        u: 243.2,
        load: 52,
        modN: 40,
        modRun: 26,
        state: '正常',
        i: 530,
        p: 126,
        pf: 0.99,
        energy: 2980,
        thdi: 2.8,
      },
      {
        id: 'HVDC-02',
        u: 242.8,
        load: 49,
        modN: 40,
        modRun: 24,
        state: '正常',
        i: 499,
        p: 119,
        pf: 0.99,
        energy: 2810,
        thdi: 2.6,
      },
      {
        id: 'HVDC-03',
        u: 243.5,
        load: 54,
        modN: 40,
        modRun: 27,
        state: '正常',
        i: 551,
        p: 131,
        pf: 0.99,
        energy: 3120,
        thdi: 2.9,
      },
    ],
    ats: [
      {
        id: 'ATS-01 制冷动力',
        state: '常用侧',
        mode: '自动',
        lastSw: '2026-06-18 演练',
        uIn: 381,
        uOut: 380,
        pf: 0.95,
        p: 320,
      },
      {
        id: 'ATS-02 应急照明',
        state: '常用侧',
        mode: '自动',
        lastSw: '2026-06-18 演练',
        uIn: 380,
        uOut: 379,
        pf: 0.92,
        p: 58,
      },
      {
        id: 'ATS-03 消防负荷',
        state: '常用侧',
        mode: '自动',
        lastSw: '2026-05-22 演练',
        uIn: 382,
        uOut: 381,
        pf: 0.9,
        p: 88,
      },
      {
        id: 'ATS-04 安防负荷',
        state: '常用侧',
        mode: '自动',
        lastSw: '2026-05-22 演练',
        uIn: 380,
        uOut: 380,
        pf: 0.93,
        p: 42,
      },
    ],
    busbars: Array.from({ length: 8 }, (_, i) => ({
      id: `母排 BB-${String(i + 1).padStart(2, '0')}`,
      load: rnd(38, 68, 0),
      i: rnd(800, 1500, 0),
      state: '正常',
      u: 0.398,
      pf: 0.95,
      energy: rnd(8000, 16000, 0),
      thdu: rnd(2, 3, 1),
    })),
    branches: [
      {
        id: 'LP-A01',
        name: 'A 栋 IT 机柜排 1',
        breaker: '合闸',
        rated: 630,
        ua: 228,
        ub: 230,
        uc: 229,
        u: 229,
        ia: 412,
        ib: 398,
        ic: 405,
        i: 405,
        freq: 50.02,
        p: 268,
        q: 76,
        pf: 0.96,
        energy: 5210,
        thdu: 2.4,
        thdi: 5.1,
        loadPct: 64,
      },
      {
        id: 'LP-A02',
        name: 'A 栋 IT 机柜排 2',
        breaker: '合闸',
        rated: 630,
        ua: 229,
        ub: 231,
        uc: 230,
        u: 230,
        ia: 396,
        ib: 388,
        ic: 391,
        i: 392,
        freq: 50.01,
        p: 255,
        q: 72,
        pf: 0.95,
        energy: 4980,
        thdu: 2.3,
        thdi: 5.3,
        loadPct: 62,
      },
      {
        id: 'LP-B01',
        name: 'B 栋 IT 机柜排 1',
        breaker: '合闸',
        rated: 630,
        ua: 227,
        ub: 229,
        uc: 228,
        u: 228,
        ia: 428,
        ib: 414,
        ic: 421,
        i: 421,
        freq: 50.02,
        p: 272,
        q: 80,
        pf: 0.96,
        energy: 5330,
        thdu: 2.5,
        thdi: 5.0,
        loadPct: 67,
      },
      {
        id: 'LP-B02',
        name: 'B 栋 IT 机柜排 2',
        breaker: '合闸',
        rated: 630,
        ua: 230,
        ub: 228,
        uc: 229,
        u: 229,
        ia: 380,
        ib: 372,
        ic: 375,
        i: 376,
        freq: 50.0,
        p: 242,
        q: 68,
        pf: 0.94,
        energy: 4730,
        thdu: 2.2,
        thdi: 5.4,
        loadPct: 59,
      },
      {
        id: 'LP-C01',
        name: '制冷机组 A',
        breaker: '合闸',
        rated: 400,
        ua: 226,
        ub: 228,
        uc: 227,
        u: 227,
        ia: 296,
        ib: 288,
        ic: 292,
        i: 292,
        freq: 49.99,
        p: 188,
        q: 70,
        pf: 0.93,
        energy: 3680,
        thdu: 2.8,
        thdi: 7.2,
        loadPct: 73,
      },
      {
        id: 'LP-C02',
        name: '制冷机组 B',
        breaker: '合闸',
        rated: 400,
        ua: 229,
        ub: 227,
        uc: 228,
        u: 228,
        ia: 281,
        ib: 274,
        ic: 277,
        i: 277,
        freq: 50.01,
        p: 179,
        q: 66,
        pf: 0.92,
        energy: 3510,
        thdu: 2.9,
        thdi: 7.5,
        loadPct: 69,
      },
      {
        id: 'LP-D01',
        name: '应急照明 / 消防',
        breaker: '合闸',
        rated: 160,
        ua: 230,
        ub: 231,
        uc: 229,
        u: 230,
        ia: 98,
        ib: 92,
        ic: 95,
        i: 95,
        freq: 50.0,
        p: 58,
        q: 22,
        pf: 0.91,
        energy: 980,
        thdu: 1.9,
        thdi: 3.1,
        loadPct: 59,
      },
      {
        id: 'LP-D02',
        name: '安防 / 弱电',
        breaker: '合闸',
        rated: 160,
        ua: 231,
        ub: 229,
        uc: 230,
        u: 230,
        ia: 72,
        ib: 69,
        ic: 70,
        i: 70,
        freq: 50.01,
        p: 42,
        q: 16,
        pf: 0.9,
        energy: 760,
        thdu: 1.8,
        thdi: 2.9,
        loadPct: 44,
      },
      {
        id: 'LP-E01',
        name: '备用回路',
        breaker: '分闸',
        rated: 250,
        ua: 230,
        ub: 230,
        uc: 230,
        u: 230,
        ia: 0,
        ib: 0,
        ic: 0,
        i: 0,
        freq: 50.0,
        p: 0,
        q: 0,
        pf: 0,
        energy: 0,
        thdu: 0,
        thdi: 0,
        loadPct: 0,
      },
    ],
    spds: [
      {
        id: '配电间 A 进线柜 SPD',
        state: '正常',
        level: 'g',
        leakI: 0.08,
        count: 2,
        status: '正常',
      },
      {
        id: '配电间 B 进线柜 SPD',
        state: '正常',
        level: 'g',
        leakI: 0.11,
        count: 1,
        status: '正常',
      },
      { id: 'UPS 室 A SPD', state: '正常', level: 'g', leakI: 0.05, count: 0, status: '正常' },
      { id: 'UPS 室 B SPD', state: '劣化', level: 'a', leakI: 0.62, count: 7, status: '报警' },
      { id: '制冷机房 SPD', state: '正常', level: 'g', leakI: 0.09, count: 3, status: '正常' },
      { id: '弱电井 SPD', state: '正常', level: 'g', leakI: 0.04, count: 0, status: '正常' },
    ],
  },

  /* ---------- 电力 · 柴发并机 ---------- */
  genset: {
    scheme: '8 台 2500KW 高压柴发 · N+1 并机',
    busState: '市电失电 · 柴发并机带载 (6/8)',
    autoMode: '自动 (市电失电 15s 内首台建压, 60s 内并机带载)',
    units: buildGensetUnits(),
    lastTest: {
      date: '2026-07-12',
      type: '带载并机测试 (加载 50%)',
      result: '通过',
      duration: '2h',
    },
    parallelSteps: [
      '市电失压确认',
      '首台启动建压',
      '同期并机',
      '分级加载',
      '带载运行',
      '市电恢复反并',
      '冷却停机',
    ],
    stepActive: 4,
  },

  /* ---------- 电力 · 燃油监控 ---------- */
  fuel: buildFuel(),

  /* ---------- 电力 · 电池监控 ---------- */
  battery: buildBattery(),

  /* ---------- 安防 · 视频监控 ---------- */
  cctv: {
    total: 486,
    online: 482,
    offline: 4,
    nvr: { total: 12, ok: 12, storeDays: 92, required: 90 },
    zones: [
      { id: '园区周界', cams: 64, offline: 0 },
      { id: '大堂/门厅', cams: 22, offline: 0 },
      { id: '走廊/通道', cams: 118, offline: 1 },
      { id: '机房包间', cams: 192, offline: 2 },
      { id: '动力机房', cams: 58, offline: 1 },
      { id: '柴发/油罐区', cams: 32, offline: 0 },
    ],
    ai: ['周界入侵检测', '人员徘徊识别', '未戴安全帽识别', '离岗检测'],
    events: [
      { ts: '13:52', zone: '园区周界-东', desc: 'AI 周界检测: 小动物触发, 已自动过滤', lv: 'info' },
      { ts: '11:20', zone: '走廊 C2', desc: '摄像机 CAM-C2-07 视频丢失', lv: 'warn' },
      { ts: '09:47', zone: '机房 R03', desc: '人员徘徊识别: 已联动复核, 为巡检人员', lv: 'info' },
    ],
  },

  /* ---------- 安防 · 门禁 ---------- */
  acs: {
    doors: 268,
    online: 266,
    openAbnormal: 1,
    todayEvents: 1642,
    denied: 12,
    visitors: 9,
    areas: [
      { id: '一级区 · 园区/大堂', auth: '刷卡', doors: 24 },
      { id: '二级区 · 办公/走廊', auth: '刷卡+密码', doors: 86 },
      { id: '三级区 · 机房包间', auth: '刷卡+指纹', doors: 118 },
      { id: '四级区 · 动力/网络核心', auth: '刷卡+人脸+双人互锁', doors: 40 },
    ],
    events: [
      { ts: '14:05', door: 'R06 包间北门', person: '王强(运维)', act: '刷卡+指纹通过', lv: 'info' },
      { ts: '13:41', door: 'UPS 室 A', person: '李敏(厂商)', act: '访客授权通过·陪同', lv: 'info' },
      {
        ts: '12:58',
        door: 'R11 包间南门',
        person: '未授权卡',
        act: '拒绝 · 已联动视频复核',
        lv: 'warn',
      },
      { ts: '11:33', door: '油罐区大门', person: '—', act: '门磁异常开启 > 60s', lv: 'crit' },
    ],
  },

  /* ---------- 安防 · 防入侵 ---------- */
  ids: {
    perimeter: { type: '电子围栏 + 振动光纤', zones: 16, armed: 16, alarm: 0 },
    indoor: { ir: 84, glass: 36, armed: '夜间自动布防', state: '白天撤防(重点区布防)' },
    linkage: '报警 → 联动摄像机预置位 + 声光 + IOC 弹窗',
    events: [
      {
        ts: '02:14',
        zone: '周界 Z-07',
        desc: '振动光纤扰动, AI 判定树枝刮碰, 自动消警',
        lv: 'info',
      },
      {
        ts: '昨日 23:40',
        zone: '周界 Z-03',
        desc: '电子围栏触网报警, 保安 3min 到场, 无异常',
        lv: 'warn',
      },
    ],
  },

  /* ---------- 消防 ---------- */
  fire: {
    hostState: '正常运行',
    loops: 8,
    points: 5860,
    faultPoints: 2,
    detectors: [
      { type: '感烟探测器', n: 3120, fault: 1 },
      { type: '感温探测器', n: 1480, fault: 1 },
      { type: '极早期(VESDA)', n: 96, fault: 0 },
      { type: '手报/声光', n: 420, fault: 0 },
      { type: '气体灭火控制盘', n: 46, fault: 0 },
      { type: '防火门监控', n: 268, fault: 0 },
    ],
    gas: { zones: 46, ready: 46, released: 0, agent: '七氟丙烷' },
    vesda: Array.from({ length: 6 }, (_, i) => ({
      id: `VESDA R${String(i * 2 + 1).padStart(2, '0')}`,
      level: pick(['正常', '正常', '正常', '轻微']),
      val: rnd(0.001, 0.018, 3),
    })),
    qieFei: {
      desc: '确认火警 → 切除非消防电源(切非) → 联动气灭 → 应急照明投入',
      state: '自动允许',
      lastDrill: '2026-06-28 消防演练通过',
    },
    emergency: { lights: 1240, ok: 1236, batteryOk: 99.2, evacSigns: 386 },
    events: [
      { ts: '07-20 16:02', desc: 'R08 VESDA 轻微烟雾预警, 现场复核为清洁扬尘', lv: 'warn' },
      { ts: '07-18 10:00', desc: '月度消防联动测试: 切非/气灭启动回路校验通过', lv: 'info' },
    ],
  },

  /* ---------- 智能运营 · 数字孪生 ---------- */
  twin: {
    platform: 'Raptor / 方舟自动化运营平台',
    coverage: { points: 128500, mapped: 99.6, models: 42, refreshMs: 800 },
    layers: ['园区', '楼栋', '楼层', '包间', '机柜', '设备'],
    scenes: [
      { id: '全停演练推演', state: '已编排', last: '2026-07-05' },
      { id: '冷源故障切换推演', state: '已编排', last: '2026-06-20' },
      { id: '市电失电-柴发接管推演', state: '已编排', last: '2026-06-12' },
    ],
    autoOps: [
      { id: '冷机群控寻优', state: '闭环运行', saving: '3.8%' },
      { id: '末端空调联动调优', state: '闭环运行', saving: '2.4%' },
      { id: '无人巡检机器人', state: '运行 · 2 台', saving: '—' },
    ],
  },

  /* ---------- 智能运营 · 容量 ---------- */
  capacity: {
    dims: [
      { id: '机柜空间', used: 3212, total: 3600, unit: '架' },
      { id: '电力容量', used: 24.6, total: 36, unit: 'MW' },
      { id: '制冷容量', used: 26.1, total: 40, unit: 'MW' },
      { id: '承重容量', used: 68, total: 100, unit: '%' },
      { id: '网络端口', used: 41200, total: 57600, unit: '口' },
    ],
    rooms: Array.from({ length: 12 }, (_, i) => ({
      id: `R${String(i + 1).padStart(2, '0')}`,
      racks: 300,
      used: rnd(240, 296, 0),
      powerPct: rnd(55, 88, 0),
      coolPct: rnd(50, 82, 0),
    })),
    forecast: '按当前上架速率, 电力容量预计 14 个月后达 85% 预警线',
  },

  /* ---------- 智能运营 · 告警 ---------- */
  alarms: {
    convergence: { raw: 1284, converged: 63, rate: 95.1 },
    rules: ['同源合并', '拓扑根因分析', '抖动抑制', '维保屏蔽窗口'],
    trend: [
      {
        id: 'CH-02 冷凝器趋近温度缓升',
        pred: '预计 21 天后越限',
        conf: 87,
        sug: '安排冷凝器在线清洗',
      },
      {
        id: 'HVDC-03 #28 单体内阻上升',
        pred: '预计 30 天内达更换阈值',
        conf: 82,
        sug: '备件申领, 择机更换',
      },
      {
        id: 'CT-03 风机振动幅值缓升',
        pred: '预计 45 天后达注意值',
        conf: 74,
        sug: '下次月检加测振动频谱',
      },
    ],
    active: [
      {
        lv: 'crit',
        sys: '安防-门禁',
        desc: '油罐区大门 门磁异常开启 > 60s',
        ts: '11:33',
        state: '处理中',
        owner: '保安班组',
      },
      {
        lv: 'warn',
        sys: '暖通-末端',
        desc: 'CRAC-08 风机故障停机, 备机自动投入',
        ts: '10:18',
        state: '已派单',
        owner: '暖通班组',
      },
      {
        lv: 'warn',
        sys: '电力-电池',
        desc: 'HVDC-03 电池 #28 内阻偏高',
        ts: '03:12',
        state: '观察中',
        owner: '电气班组',
      },
      {
        lv: 'warn',
        sys: '安防-视频',
        desc: 'CAM-C2-07 视频丢失',
        ts: '11:20',
        state: '已派单',
        owner: '弱电班组',
      },
      {
        lv: 'warn',
        sys: '消防',
        desc: 'R08 VESDA 轻微预警(已复核)',
        ts: '07-20',
        state: '已闭环',
        owner: '消控室',
      },
      {
        lv: 'warn',
        sys: '暖通-冷源',
        desc: 'CH-02 冷凝趋近温度趋势预警',
        ts: '07-19',
        state: '计划检修',
        owner: '暖通班组',
      },
      {
        lv: 'info',
        sys: '电力-10KV',
        desc: '2# 进线电压轻微波动(合格范围内)',
        ts: '13:05',
        state: '自动消警',
        owner: '—',
      },
    ],
    sla: { mttaMin: 2.1, mttrMin: 38, autoCloseRate: 71 },
  },

  /* ---------- 智能运营 · 电量预测与节能 ---------- */
  energy: {
    todayKwh: 512300,
    monthKwh: 11.82,
    yearKwh: 78.4,
    pueTrend: series(30, 1.22, 1.31).map((v) => +v.toFixed(3)),
    loadForecast: Array.from({ length: 24 }, (_, h) => ({
      h,
      actual: h <= 14 ? rnd(23.2, 25.4) : null,
      pred: rnd(23.0, 25.8),
    })),
    aiSaving: {
      enabled: true,
      algo: '冷源 AI 寻优 + 负载预测联动',
      monthSaveKwh: 286000,
      saveRate: 3.1,
    },
    breakdown: [
      { id: 'IT 负载', kw: 24600, pct: 80.1 },
      { id: '制冷系统', kw: 4900, pct: 16.0 },
      { id: '供配电损耗', kw: 780, pct: 2.5 },
      { id: '照明及其他', kw: 420, pct: 1.4 },
    ],
    carbon: { greenPct: 34, pv: '屋顶光伏 2.1MWp', monthCO2: 5620 },
  },

  /* ---------- 运维作业 · 工单 ---------- */
  tickets: {
    stats: { open: 6, doing: 4, pending: 2, done: 128 },
    list: [
      {
        id: 'WO-260723-018',
        title: '油罐区大门门磁异常处置',
        sys: '安防',
        lv: 'crit',
        state: '处理中',
        owner: '保安班组',
        created: '07-23 11:33',
        sla: '1h',
        progress: 60,
      },
      {
        id: 'WO-260723-017',
        title: 'CRAC-08 风机更换',
        sys: '暖通',
        lv: 'warn',
        state: '处理中',
        owner: '暖通班组',
        created: '07-23 10:18',
        sla: '4h',
        progress: 45,
      },
      {
        id: 'WO-260723-015',
        title: 'CAM-C2-07 视频链路检修',
        sys: '弱电',
        lv: 'warn',
        state: '待处理',
        owner: '弱电班组',
        created: '07-23 11:20',
        sla: '8h',
        progress: 10,
      },
      {
        id: 'WO-260721-042',
        title: 'HVDC-03 #28 电池更换备件申领',
        sys: '电力',
        lv: 'warn',
        state: '待处理',
        owner: '电气班组',
        created: '07-21 03:12',
        sla: '72h',
        progress: 25,
      },
      {
        id: 'WO-260719-033',
        title: 'CH-02 冷凝器在线清洗',
        sys: '暖通',
        lv: 'info',
        state: '处理中',
        owner: '暖通班组',
        created: '07-19 09:00',
        sla: '计划',
        progress: 70,
      },
      {
        id: 'WO-260723-012',
        title: 'R08 VESDA 误报复核闭环',
        sys: '消防',
        lv: 'info',
        state: '已完成',
        owner: '消控室',
        created: '07-20 16:02',
        sla: '已闭环',
        progress: 100,
      },
    ],
  },

  /* ---------- 运维作业 · 巡检 ---------- */
  inspect: {
    today: { plan: 24, done: 18, abnormal: 2, rate: 75 },
    robot: { units: 2, running: 2, coverage: 96, findings: 3 },
    routes: [
      {
        id: '冷冻机房日巡',
        freq: '每 4h',
        last: '12:30',
        next: '16:30',
        items: 42,
        state: '进行中',
      },
      {
        id: '高低压配电巡检',
        freq: '每班',
        last: '08:15',
        next: '20:15',
        items: 68,
        state: '已完成',
      },
      {
        id: '电池室专项巡检',
        freq: '每日',
        last: '09:40',
        next: '明日',
        items: 36,
        state: '已完成',
      },
      {
        id: '柴发机房巡检',
        freq: '每周',
        last: '07-22',
        next: '07-29',
        items: 55,
        state: '已完成',
      },
      { id: '消防设施巡检', freq: '每日', last: '10:00', next: '明日', items: 48, state: '已完成' },
      {
        id: '安防周界巡逻',
        freq: '每 2h',
        last: '13:00',
        next: '15:00',
        items: 24,
        state: '进行中',
      },
    ],
    findings: [
      {
        ts: '12:48',
        route: '冷冻机房日巡',
        item: 'CH-02 冷凝器压差偏高',
        lv: 'warn',
        action: '已转工单 WO-260719-033',
      },
      {
        ts: '13:22',
        route: '安防周界巡逻',
        item: 'Z-05 段照明灯珠损坏 2 处',
        lv: 'info',
        action: '记录待修',
      },
    ],
  },

  /* ---------- 运维作业 · 维保 ---------- */
  maintain: {
    stats: { plan: 42, done: 38, overdue: 1, thisWeek: 6 },
    plans: [
      {
        id: 'PM-CH',
        equip: '冷水机组',
        cycle: '季度',
        last: '2026-05-10',
        next: '2026-08-10',
        vendor: '厂商+自维',
        state: '正常',
      },
      {
        id: 'PM-UPS',
        equip: 'UPS 系统',
        cycle: '半年',
        last: '2026-04-18',
        next: '2026-10-18',
        vendor: '厂商',
        state: '正常',
      },
      {
        id: 'PM-DG',
        equip: '柴发机组',
        cycle: '月度带载',
        last: '2026-07-12',
        next: '2026-08-12',
        vendor: '自维',
        state: '正常',
      },
      {
        id: 'PM-BAT',
        equip: '蓄电池组',
        cycle: '半年核容',
        last: '2026-06-30',
        next: '2026-12-30',
        vendor: '自维',
        state: '正常',
      },
      {
        id: 'PM-FIRE',
        equip: '消防系统',
        cycle: '月度联动',
        last: '2026-07-18',
        next: '2026-08-18',
        vendor: '第三方',
        state: '正常',
      },
      {
        id: 'PM-CRAC',
        equip: '精密空调',
        cycle: '季度',
        last: '2026-06-05',
        next: '2026-09-05',
        vendor: '自维',
        state: '临期',
      },
      {
        id: 'PM-ATS',
        equip: 'ATS/备自投',
        cycle: '半年演练',
        last: '2026-01-20',
        next: '2026-07-20',
        vendor: '厂商',
        state: '逾期',
      },
    ],
    spares: [
      { id: '冷机压缩机油滤', stock: 12, min: 6, state: '充足' },
      { id: '精密空调风机', stock: 3, min: 4, state: '预警' },
      { id: 'HVDC 整流模块', stock: 5, min: 3, state: '充足' },
      { id: '铅酸电池单体 12V', stock: 24, min: 20, state: '充足' },
      { id: '感烟探测器', stock: 40, min: 30, state: '充足' },
    ],
  },

  /* ---------- 运维作业 · 演练 ---------- */
  drill: {
    stats: { year: 12, done: 8, pass: 8, next: '2026-08-05 全停演练' },
    plans: [
      {
        id: 1,
        code: 'DR-01',
        name: '市电全停-柴发接管演练',
        type: '电力',
        date: '2026-08-05',
        state: '已编排',
        result: '—',
        level: '一级',
        scope: '全园区供电',
        duration: 120,
        steps: [
          { title: '发布演练指令并隔离市电', minutes: 10, desc: '调度中心下令, 拉开进线开关' },
          { title: '柴发自启并带载', minutes: 15, desc: '确认柴发频率/电压正常, 逐级送电' },
          { title: '关键负荷验证', minutes: 20, desc: 'UPS/冷却/消防电源核相' },
        ],
      },
      {
        id: 2,
        code: 'DR-02',
        name: '冷源系统故障切换演练',
        type: '暖通',
        date: '2026-06-20',
        state: '已完成',
        result: '通过',
        level: '二级',
        scope: '冷源机房',
        duration: 90,
        steps: [{ title: '主冷机停机', minutes: 10, desc: '切换至备用冷机' }],
      },
      {
        id: 3,
        code: 'DR-03',
        name: '母联备自投切换演练',
        type: '电力',
        date: '2026-07-05',
        state: '已完成',
        result: '通过',
        level: '二级',
        scope: '10kV 母线',
        duration: 60,
        steps: [],
      },
      {
        id: 4,
        code: 'DR-04',
        name: '气体灭火联动演练',
        type: '消防',
        date: '2026-06-28',
        state: '已完成',
        result: '通过',
        level: '三级',
        scope: '机房区',
        duration: 45,
        steps: [],
      },
      {
        id: 5,
        code: 'DR-05',
        name: '周界入侵应急演练',
        type: '安防',
        date: '2026-05-16',
        state: '已完成',
        result: '通过',
        level: '三级',
        scope: '园区周界',
        duration: 30,
        steps: [],
      },
      {
        id: 6,
        code: 'DR-06',
        name: 'UPS 切旁路演练',
        type: '电力',
        date: '2026-09-12',
        state: '计划中',
        result: '—',
        level: '二级',
        scope: 'UPS 室',
        duration: 60,
        steps: [],
      },
    ],
  },

  /* ---------- 运维作业 · 排班 ---------- */
  shift: {
    teams: ['暖通班组', '电气班组', '弱电班组', '消控室', '保安班组'],
    today: { onDuty: 14, dayShift: 9, nightShift: 5, leader: '张伟 (值班经理)' },
    roster: Array.from({ length: 28 }, (_, i) => ({
      day: i + 1,
      day1: ['A 组', 'B 组', 'C 组'][i % 3],
      night: ['C 组', 'A 组', 'B 组'][i % 3],
    })),
  },

  /* ---------- 运维作业 · 知识库 ---------- */
  knowledge: {
    stats: { sop: 186, drawing: 420, manual: 92, emergency: 34 },
    cats: [
      { id: '应急预案', n: 34, hot: '市电全停应急处置预案 v3.2' },
      { id: '运行 SOP', n: 186, hot: '冷源加减机操作规程' },
      { id: '设备手册', n: 92, hot: 'HVDC 整流模块检修手册' },
      { id: '竣工图纸', n: 420, hot: '10KV 供配电系统单线图' },
      { id: '故障案例库', n: 148, hot: '精密空调高压报警典型案例' },
      { id: '培训资料', n: 76, hot: '弱电高级运维工程师认证课件' },
    ],
    recent: [
      { title: '市电全停应急处置预案', ver: 'v3.2', date: '2026-07-10', by: '运维部' },
      { title: '冷源 AI 群控参数配置指南', ver: 'v1.4', date: '2026-06-28', by: '能效组' },
      { title: '蓄电池核容放电作业指导书', ver: 'v2.1', date: '2026-06-15', by: '电气班组' },
    ],
  },

  /* ---------- 运维作业 · 风险 ---------- */
  risk: {
    matrix: [
      {
        id: 'R-01',
        risk: 'ATS 半年演练逾期',
        cat: '电力',
        prob: 3,
        impact: 4,
        level: '高',
        ctrl: '已排 07-25 补做演练',
        owner: '电气班组',
      },
      {
        id: 'R-02',
        risk: '精密空调备件库存不足',
        cat: '备件',
        prob: 3,
        impact: 3,
        level: '中',
        ctrl: '紧急补货中',
        owner: '物资组',
      },
      {
        id: 'R-03',
        risk: 'HVDC-03 电池老化',
        cat: '电力',
        prob: 2,
        impact: 4,
        level: '中',
        ctrl: '监测+择机更换',
        owner: '电气班组',
      },
      {
        id: 'R-04',
        risk: '夏季冷源高负荷运行',
        cat: '暖通',
        prob: 3,
        impact: 3,
        level: '中',
        ctrl: '蓄冷罐+错峰策略',
        owner: '暖通班组',
      },
      {
        id: 'R-05',
        risk: '油罐区物理安防薄弱点',
        cat: '安防',
        prob: 2,
        impact: 3,
        level: '低',
        ctrl: '增设摄像机+门磁',
        owner: '保安班组',
      },
    ],
    stats: { high: 1, mid: 3, low: 1, closed: 22 },
  },
}

/** 驾驶舱总览 (与后端 dashboard_overview 输出一致的 snake_case)。 */
export function dashboardOverview() {
  const k = DC.kpi
  const total = 48 * 60 // 模拟: 机柜*服务器 + 其他设备
  const online = Math.round(total * 0.993)
  return {
    total_devices: total,
    online_devices: online,
    online_rate: +((online / total) * 100).toFixed(2),
    today_alarms: k.alarms.crit + k.alarms.warn + k.alarms.info,
    pue: k.pue,
    wue: k.wue,
    it_load_mw: k.itLoad,
    total_load_mw: k.totalLoad,
    cool_load_mw: k.coolLoad,
    availability: k.availability,
    free_cool_hours: k.freeCoolHours,
    alarms: { crit: k.alarms.crit, warn: k.alarms.warn, info: k.alarms.info },
  }
}

/* ================= 外部设备接入 / 设备遥测 模拟数据 (兜底) =================
 * 当后端 (采集器契约 /api/external/*) 不可达时, 由 mockForUrl 动态派生:
 *   - 已注册设备列表    GET /api/external/devices
 *   - 物模型列表        GET /api/external/thing-models
 *   - 设备最近测点      GET /api/external/devices/{id}/metrics
 *   - 实时快照          GET /api/external/devices/{id}/metrics/realtime
 *   - 历史趋势          GET /api/external/devices/{id}/metrics/history
 * 测点模板与前端 THING_MODELS 的 metric_name/unit 保持一致, 使 DeviceMonitor 能正确匹配物模型。
 */

interface MockMetricSpec {
  name: string
  unit: string
  base: number
  amp: number
  /** 随机游走: 噪声幅度 (每步漂移标准差) */
  noise?: number
  /** 均值回归系数 (趋向 base 的速度) */
  reversion?: number
  /** 偶发越限概率 (每步) — 用于演示越限联动 */
  excProb?: number
  /** 越限目标值 */
  excTarget?: number
  /** 越限持续步数 */
  excHold?: number
  /** 小数位 */
  decimals?: number
}

// 测点基线/波动 (name/unit 须与 THING_MODELS 对应)
// noise/reversion 控制随机游走的平滑度; exc* 控制偶发越限以驱动越限联动告警
const CATEGORY_METRICS: Record<string, MockMetricSpec[]> = {
  chiller: [
    {
      name: 'supply_temp',
      unit: '℃',
      base: 15.2,
      amp: 0.6,
      noise: 0.3,
      reversion: 0.08,
      excProb: 0.05,
      excTarget: 19.5,
      excHold: 40,
      decimals: 1,
    },
    {
      name: 'return_temp',
      unit: '℃',
      base: 21.0,
      amp: 0.8,
      noise: 0.4,
      reversion: 0.08,
      excProb: 0.02,
      excTarget: 23.5,
      excHold: 30,
      decimals: 1,
    },
    {
      name: 'power_kw',
      unit: 'kW',
      base: 520,
      amp: 40,
      noise: 15,
      reversion: 0.07,
      excProb: 0.04,
      excTarget: 615,
      excHold: 40,
      decimals: 0,
    },
    { name: 'cpu_usage', unit: '%', base: 38, amp: 8, noise: 4, reversion: 0.06, decimals: 0 },
  ],
  crac: [
    {
      name: 'supply_temp',
      unit: '℃',
      base: 18.2,
      amp: 0.8,
      noise: 0.4,
      reversion: 0.08,
      excProb: 0.02,
      excTarget: 19.5,
      excHold: 20,
      decimals: 1,
    },
    {
      name: 'return_temp',
      unit: '℃',
      base: 27.0,
      amp: 1.0,
      noise: 0.5,
      reversion: 0.08,
      excProb: 0.05,
      excTarget: 34,
      excHold: 40,
      decimals: 1,
    },
    { name: 'power_kw', unit: 'kW', base: 65, amp: 10, noise: 5, reversion: 0.07, decimals: 0 },
    { name: 'cpu_usage', unit: '%', base: 41, amp: 7, noise: 4, reversion: 0.06, decimals: 0 },
  ],
  ups: [
    {
      name: 'power_kw',
      unit: 'kW',
      base: 312,
      amp: 20,
      noise: 10,
      reversion: 0.07,
      excProb: 0.04,
      excTarget: 505,
      excHold: 40,
      decimals: 0,
    },
    { name: 'cpu_usage', unit: '%', base: 22, amp: 5, noise: 3, reversion: 0.06, decimals: 0 },
  ],
}

// 设备 ID 前缀 → 类别 (未知设备兜底)
const PREFIX_CATEGORY: Record<string, string> = { ch: 'chiller', cr: 'crac', up: 'ups' }

function specsFor(category?: string, deviceId = ''): MockMetricSpec[] {
  if (category && CATEGORY_METRICS[category]) return CATEGORY_METRICS[category]
  if (deviceId) {
    const p = (deviceId.split('-')[0] || '').toLowerCase()
    return CATEGORY_METRICS[PREFIX_CATEGORY[p] ?? 'chiller']
  }
  return CATEGORY_METRICS.chiller
}

/** 随机游走状态: 以 deviceId::metric 为键, 记录上一值与越限保持步数 */
const extWalk = new Map<string, { last: number; hold: number; holdTarget: number }>()

/**
 * 一阶惯性随机游走: 基于上一值向基线回归 + 噪声;
 * 偶发越限 (excProb) 时把值推向 excTarget 并维持 excHold 步, 让阈值联动可被持续窗口捕获。
 */
function walkVal(spec: MockMetricSpec, key: string): number {
  let st = extWalk.get(key)
  if (!st) {
    st = { last: spec.base, hold: 0, holdTarget: spec.base }
    extWalk.set(key, st)
  }
  const noise = spec.noise ?? spec.amp
  const rev = spec.reversion ?? 0.06
  if (st.hold > 0) {
    st.hold--
    st.last = st.last + (st.holdTarget - st.last) * 0.25 + (Math.random() * 2 - 1) * noise * 0.4
  } else {
    if (spec.excProb && Math.random() < spec.excProb) {
      st.hold = spec.excHold ?? 20
      st.holdTarget = spec.excTarget ?? spec.base
    }
    st.last = st.last + (spec.base - st.last) * rev + (Math.random() * 2 - 1) * noise
  }
  const dec = spec.decimals ?? (spec.unit === 'kW' ? 0 : 1)
  return +st.last.toFixed(dec)
}

// 预置已注册设备 (模拟采集器已上报)
interface MockRegDevice {
  device_id: string
  name: string
  model: string
  ip: string
  sn: string
  vendor: string
  domain: string
  category: string
  protocol: string
  location: string
  online: boolean
}
const MOCK_REGISTERED: MockRegDevice[] = [
  {
    device_id: 'CHILLER-01',
    name: '1#冷水机组',
    model: 'Carrier-19XR',
    ip: '10.20.1.11',
    sn: 'CH-SN-0001',
    vendor: 'Carrier',
    domain: 'hvac_source',
    category: 'chiller',
    protocol: 'modbus',
    location: 'R01',
    online: true,
  },
  {
    device_id: 'CHILLER-02',
    name: '2#冷水机组',
    model: 'Carrier-19XR',
    ip: '10.20.1.12',
    sn: 'CH-SN-0002',
    vendor: 'Carrier',
    domain: 'hvac_source',
    category: 'chiller',
    protocol: 'modbus',
    location: 'R01',
    online: true,
  },
  {
    device_id: 'CRAC-01',
    name: 'A区精密空调',
    model: 'Emerson-DX',
    ip: '10.20.2.21',
    sn: 'CR-SN-0021',
    vendor: 'Emerson',
    domain: 'hvac_terminal',
    category: 'crac',
    protocol: 'snmp',
    location: 'R02',
    online: true,
  },
  {
    device_id: 'CRAC-02',
    name: 'B区精密空调',
    model: 'Emerson-DX',
    ip: '10.20.2.22',
    sn: 'CR-SN-0022',
    vendor: 'Emerson',
    domain: 'hvac_terminal',
    category: 'crac',
    protocol: 'snmp',
    location: 'R03',
    online: false,
  },
  {
    device_id: 'UPS-A',
    name: 'UPS A组',
    model: 'Vertiv-Liebert',
    ip: '10.20.3.31',
    sn: 'UP-SN-0031',
    vendor: 'Vertiv',
    domain: 'power_lv',
    category: 'ups',
    protocol: 'snmp',
    location: 'R04',
    online: true,
  },
  {
    device_id: 'UPS-B',
    name: 'UPS B组',
    model: 'Vertiv-Liebert',
    ip: '10.20.3.32',
    sn: 'UP-SN-0032',
    vendor: 'Vertiv',
    domain: 'power_lv',
    category: 'ups',
    protocol: 'snmp',
    location: 'R04',
    online: true,
  },
]

function buildDeviceView(d: MockRegDevice): ExternalDeviceView {
  const specs = specsFor(d.category, d.device_id)
  const last = d.online
    ? new Date(Date.now() - Math.floor(Math.random() * 8000))
    : new Date(Date.now() - 1000 * 60 * 35)
  return {
    device_id: d.device_id,
    ip: d.ip,
    sn: d.sn,
    model: d.model,
    name: d.name,
    vendor: d.vendor,
    domain: d.domain,
    category: d.category,
    location: d.location,
    protocol: d.protocol,
    tags: [],
    metric_count: specs.length,
    online: d.online,
    last_seen: last.toISOString(),
    registered_at: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
  }
}

function findReg(deviceId: string): MockRegDevice | null {
  return MOCK_REGISTERED.find((d) => d.device_id === deviceId) ?? null
}

function externalDevicesMock(params?: MockQuery): DeviceListResponse {
  let items = MOCK_REGISTERED.map(buildDeviceView)
  if (params?.domain) items = items.filter((i) => i.domain === params.domain)
  if (params?.protocol) items = items.filter((i) => i.protocol === params.protocol)
  const online = items.filter((i) => i.online).length
  const totalMetrics = items.reduce((s, i) => s + i.metric_count, 0)
  return {
    total: items.length,
    online,
    offline: items.length - online,
    total_metrics: totalMetrics,
    items,
  }
}

/** v2 演示设备列表 (从已注册设备映射, 供 /api/demo/devices 兜底) */
function demoDevicesMock(params?: MockQuery): DemoDeviceList {
  const base = externalDevicesMock(params)
  const items: DemoDeviceItem[] = base.items.map((d) => ({
    device_id: d.device_id,
    name: d.name ?? d.device_id,
    model: d.model,
    ip: d.ip,
    protocol: d.protocol ?? '—',
    online: d.online,
    last_seen: d.last_seen,
    metric_count: d.metric_count,
  }))
  return {
    total: base.total,
    online: base.online,
    offline: base.offline,
    total_metrics: base.total_metrics,
    items,
  }
}

function thingModelsMock(): ThingModelDef[] {
  return THING_MODELS.map((m) => ({
    category: m.category,
    category_label: m.name,
    domain: m.domain,
    protocol: m.protocol,
    metrics: m.metrics.map((mt) => ({ metric_name: mt.name, unit: mt.unit, description: mt.desc })),
  }))
}

/**
 * 物模型管理页 (/api/thing-models) 离线兜底。
 * 后端不可达时, 由 THING_MODELS 派生完整 ThingModel 结构 (含 items),
 * 使管理页列表与详情都能正常渲染, 避免 "加载物模型失败"。
 */
let _adminTmCache: ThingModel[] | null = null
function thingModelsAdminMock(): ThingModel[] {
  if (_adminTmCache) return _adminTmCache
  _adminTmCache = THING_MODELS.map((m, idx) => ({
    id: idx + 1,
    modelKey: `${m.category}_model`,
    name: m.name,
    category: m.category,
    domain: m.domain,
    protocol: m.protocol,
    vendor: '',
    description: `${m.name} 物模型 (离线演示数据)`,
    items: m.metrics.map((mt, i) => ({
      id: idx * 100 + i + 1,
      thingModelId: idx + 1,
      itemType: 'property' as const,
      identifier: mt.name,
      name: mt.name,
      dataType: 'float' as const,
      unit: mt.unit,
      desc: mt.desc ?? '',
      extra: {},
    })),
    createdAt: new Date(Date.now() - 1000 * 60 * 60 * 24 * (idx + 1)).toISOString(),
    updatedAt: new Date(Date.now() - 1000 * 60 * 60 * (idx + 1)).toISOString(),
  }))
  return _adminTmCache
}

function thingModelAdminOneMock(id: number): ThingModel | undefined {
  return thingModelsAdminMock().find((m) => m.id === id)
}

// ---------- U 位识别离线兜底 (RFID 实测 + 电子工单台账多源融合) ----------
const U_BRANDS = ['Dell', 'HPE', 'Inspur', 'Huawei', 'Lenovo']
const U_BUSINESS = ['核心交易', '大数据分析', 'AI 训练', '中间件', '存储集群', '网关']

function genServersForCabinet(cabinetId: number, uTotal = 42): ServerItem[] {
  const rnd = (n: number) => {
    const x = Math.sin((cabinetId * 7 + 3) * 999 + n * 13.13) * 10000
    return x - Math.floor(x)
  }
  const servers: ServerItem[] = []
  let sid = cabinetId * 100
  let u = 1 + Math.floor(rnd(1) * 2)
  const n = 6 + Math.floor(rnd(2) * 6)
  const drift = cabinetId % 5 === 0
  let drifted = false
  for (let i = 0; i < n; i++) {
    if (u > uTotal - 1) break
    const h = [1, 1, 2, 2, 4][Math.floor(rnd(i + 3) * 5)]
    let height = h
    if (u + height - 1 > uTotal) height = uTotal - u + 1
    if (height < 1) break
    let uStart = u
    let uEnd = u + height - 1
    if (drift && !drifted && i === Math.max(2, Math.floor(n / 2))) {
      uStart += 1
      uEnd += 1
      drifted = true
    }
    sid += 1
    servers.push({
      id: sid,
      cabinetId,
      assetNo: `AS${String(cabinetId).padStart(3, '0')}-${String(sid).padStart(4, '0')}`,
      hostname: `node-${String(cabinetId).padStart(3, '0')}-${String(i + 1).padStart(2, '0')}`,
      ip: `10.${(cabinetId / 250) % 250 | 0}.${cabinetId % 250}.${i + 1}`,
      brand: U_BRANDS[Math.floor(rnd(i + 4) * U_BRANDS.length)],
      model: `R${4 + Math.floor(rnd(i + 5) * 6)}40`,
      uStart,
      uEnd,
      uHeight: uEnd - uStart + 1,
      cpuModel: 'Xeon Gold 6348',
      cpuCount: rnd(i + 6) > 0.5 ? 4 : 2,
      cpuCores: [48, 64, 96][Math.floor(rnd(i + 7) * 3)],
      memoryGb: [256, 512, 1024][Math.floor(rnd(i + 8) * 3)],
      diskDesc: `${2 + Math.floor(rnd(i + 9) * 7)}x${[960, 1920][Math.floor(rnd(i + 10)) * 2]}GB SSD`,
      business: U_BUSINESS[Math.floor(rnd(i + 11) * U_BUSINESS.length)],
      status: rnd(i + 12) > 0.75 ? '离线' : '在线',
      source: 'rfid',
    })
    u = uEnd + 1 + (rnd(i + 13) > 0.6 ? 1 : 0)
  }
  return servers
}

function genLedgerForCabinet(cabinetId: number, uTotal = 42): ServerItem[] {
  const rfid = genServersForCabinet(cabinetId, uTotal)
  const ledger = rfid.map((s) => ({ ...s, source: 'ledger' as const }))
  if (cabinetId % 5 === 0 && ledger.length) {
    const first = ledger[0]
    ledger.push({
      ...first,
      id: cabinetId * 1000 + 1,
      assetNo: `AS${String(cabinetId).padStart(3, '0')}-L000`,
      hostname: `node-${String(cabinetId).padStart(3, '0')}-L`,
      ip: '10.0.0.0',
      brand: 'Lenovo',
      model: 'SR650',
      uStart: first.uStart,
      uEnd: first.uStart,
      uHeight: 1,
      cpuModel: 'Xeon Silver 4310',
      cpuCores: 24,
      business: '网关',
      status: '在线',
      source: 'ledger',
    })
  }
  return ledger
}

function buildUCells(
  rfid: ServerItem[],
  ledger: ServerItem[],
  uTotal: number,
): { cells: UCell[]; conflicts: UConflict[] } {
  const cells: UCell[] = Array.from({ length: uTotal }, (_, k) => ({
    u: k + 1,
    status: 'empty' as const,
    sources: [],
    deviceRefs: [],
    confidence: 1,
    note: '',
  }))
  const conflicts: UConflict[] = []

  for (const s of rfid) {
    for (let u = s.uStart; u <= s.uEnd; u++) {
      if (u >= 1 && u <= uTotal) {
        const c = cells[u - 1]
        c.status = 'occupied'
        if (!c.sources.includes('rfid')) c.sources.push('rfid')
        if (!c.deviceRefs.includes(s.id)) c.deviceRefs.push(s.id)
      }
    }
  }
  const ledgerByAsset = new Map<string, ServerItem>()
  for (const s of ledger) {
    ledgerByAsset.set(s.assetNo, s)
    for (let u = s.uStart; u <= s.uEnd; u++) {
      if (u >= 1 && u <= uTotal) {
        const c = cells[u - 1]
        if (!c.sources.includes('ledger')) c.sources.push('ledger')
        if (!c.deviceRefs.includes(s.id)) c.deviceRefs.push(s.id)
      }
    }
  }
  // RFID 内部区间重叠
  const ranges: Array<[number, number, string]> = []
  for (const s of rfid) {
    for (const [lo, hi, asset] of ranges) {
      if (!(s.uEnd < lo || s.uStart > hi)) {
        conflicts.push({
          u: Math.max(s.uStart, lo),
          type: 'range_overlap',
          detail: `RFID 实测区间重叠: ${asset} 与 ${s.assetNo}`,
          assetNos: [asset, s.assetNo],
          severity: 'crit',
        })
      }
    }
    ranges.push([s.uStart, s.uEnd, s.assetNo])
  }
  // 台账与实测不符
  const rfidByAsset = new Map(rfid.map((s) => [s.assetNo, s]))
  for (const [asset, ls] of ledgerByAsset) {
    const rs = rfidByAsset.get(asset)
    if (rs && (ls.uStart !== rs.uStart || ls.uEnd !== rs.uEnd)) {
      const lo = Math.max(ls.uStart, rs.uStart)
      const hi = Math.min(ls.uEnd, rs.uEnd)
      for (let u = Math.max(1, lo); u <= Math.min(uTotal, hi); u++) cells[u - 1].status = 'conflict'
      conflicts.push({
        u: ls.uStart,
        type: 'ledger_mismatch',
        detail: `台账规划 U${ls.uStart}-${ls.uEnd} 与 RFID 实测 U${rs.uStart}-${rs.uEnd} 不符: ${asset}`,
        assetNos: [asset],
        severity: 'warn',
      })
    }
  }
  // 台账多出设备与现场已占重叠
  const rfidSet = new Set<number>()
  for (const s of rfid) for (let u = s.uStart; u <= s.uEnd; u++) rfidSet.add(u)
  for (const s of ledger) {
    if (!rfidByAsset.has(s.assetNo)) {
      for (let u = s.uStart; u <= s.uEnd; u++) {
        if (rfidSet.has(u) && u >= 1 && u <= uTotal) {
          cells[u - 1].status = 'conflict'
          conflicts.push({
            u,
            type: 'reservation_clash',
            detail: `台账登记设备 ${s.assetNo} 位于已占用 U${u}`,
            assetNos: [s.assetNo],
            severity: 'warn',
          })
        }
      }
    }
  }
  for (const c of cells) {
    if (c.status === 'conflict') c.confidence = 0.4
    else if (c.sources.includes('rfid') && c.sources.includes('ledger')) c.confidence = 0.95
    else if (c.status === 'occupied') c.confidence = 0.8
    else c.confidence = 1
  }
  return { cells, conflicts }
}

function uPositionMock(cabinetId: number): UPositionView {
  const cab = CABINETS.find((c) => c.id === cabinetId)
  const uTotal = (cab?.u_total as number) ?? 42
  const rfid = genServersForCabinet(cabinetId, uTotal)
  const ledger = genLedgerForCabinet(cabinetId, uTotal)
  const { cells, conflicts } = buildUCells(rfid, ledger, uTotal)
  const occupied = cells.filter((c) => c.status === 'occupied' || c.status === 'conflict').length
  return {
    cabinetId,
    code: cab?.code ?? String(cabinetId),
    room: cab?.room ?? '',
    row: (cab as any)?.row ?? '',
    uTotal,
    cells,
    conflicts,
    occupiedU: occupied,
    emptyU: uTotal - occupied,
    conflictU: cells.filter((c) => c.status === 'conflict').length,
    generatedAt: new Date().toISOString(),
  }
}

function recognizeUPositionMock(cabinetId: number): RecognizeResp {
  const cab = CABINETS.find((c) => c.id === cabinetId)
  const uTotal = (cab?.u_total as number) ?? 42
  const rfid = genServersForCabinet(cabinetId, uTotal)
  const ledger = genLedgerForCabinet(cabinetId, uTotal)
  const { cells, conflicts } = buildUCells(rfid, ledger, uTotal)
  const occupied = cells.filter((c) => c.status === 'occupied' || c.status === 'conflict').length
  const conf = cells.filter((c) => c.status === 'occupied').map((c) => c.confidence)
  const avg = conf.length ? conf.reduce((a, b) => a + b, 0) / conf.length : 1
  return {
    cabinetId,
    code: cab?.code ?? String(cabinetId),
    room: cab?.room ?? '',
    uTotal,
    sources: [
      { key: 'ledger', name: '电子工单 / 资产台账', confidence: 0.92, count: ledger.length },
      { key: 'rfid', name: 'RFID / 资产标签', confidence: 0.88, count: rfid.length },
    ],
    cells,
    conflicts,
    summary: {
      totalU: uTotal,
      occupied,
      empty: uTotal - occupied,
      conflict: cells.filter((c) => c.status === 'conflict').length,
      avgConfidence: Number(avg.toFixed(3)),
      ledgerCount: ledger.length,
      rfidCount: rfid.length,
    },
    recognizedAt: new Date().toISOString(),
  }
}

// ---- 故障影响分析离线兜底 (复用 DC 供电/制冷节点 + 简化 BFS 传播) ----
const _FI_CRIT_CATS = new Set([
  'hv_incomer', 'hv_isolator', 'hv_breaker', 'transformer', 'ups', 'hvdc',
  'lv_feeder', 'ats', 'bus_tie', 'chiller', 'chw_pump', 'cooling_tower',
  'hex', 'sec_pump', 'crac',
])
const _FI_BIZ = [
  { business: '核心交易系统', sla: '99.999%', cats: ['server', 'switch', 'router'], note: '金融核心交易, 双路供电+2N制冷, 中断即资损' },
  { business: '客户门户/网银', sla: '99.95%', cats: ['server', 'switch'], note: '对外服务, 可用性敏感' },
  { business: '大数据/AI 平台', sla: '99.9%', cats: ['server', 'gpu'], note: '离线/近线计算, 短时中断可容忍' },
  { business: '办公协同/邮箱', sla: '99.5%', cats: ['server'], note: '内部办公, 低优先级' },
  { business: '视频监控平台', sla: '99.9%', cats: ['nvr', 'switch'], note: '安防录像, 断链影响合规留存' },
]

const _FI_SOURCES: FaultSourceNode[] = [
  { id: 1, label: '冷水机组 A', kind: '冷水机组', domain: 'hvac_source', category: 'chiller', status: '运行', health: 60, loadPct: 76, redundancy: 'N+1', roomCode: '制冷站', riskHint: '健康分偏低 60' },
  { id: 2, label: '冷水机组 B', kind: '冷水机组', domain: 'hvac_source', category: 'chiller', status: '运行', health: 60, loadPct: 71, redundancy: 'N+1', roomCode: '制冷站', riskHint: '健康分偏低 60' },
  { id: 7, label: '变压器 T1', kind: '变压器', domain: 'power_source', category: 'transformer', status: '运行', health: 72, loadPct: 68, redundancy: '2N', roomCode: '配电室', riskHint: '健康分偏低 72' },
  { id: 9, label: 'UPS 主机', kind: 'UPS', domain: 'power_source', category: 'ups', status: '运行', health: 80, loadPct: 45, redundancy: '2N', roomCode: '配电室', riskHint: null },
  { id: 11, label: '精密空调 CRAC-01', kind: '精密空调', domain: 'hvac_terminal', category: 'crac', status: '故障', health: 60, loadPct: 0, redundancy: 'N+1', roomCode: 'A01', riskHint: '状态异常:故障' },
  { id: 12, label: '精密空调 CRAC-02', kind: '精密空调', domain: 'hvac_terminal', category: 'crac', status: '运行', health: 85, loadPct: 52, redundancy: 'N+1', roomCode: 'A01', riskHint: null },
]

function faultImpactSourcesMock(): FaultSourceList {
  const nodes = _FI_SOURCES.slice().sort((a, b) => (a.riskHint ? 0 : 1) - (b.riskHint ? 0 : 1) || a.health - b.health)
  return { generatedAt: new Date().toISOString(), source: 'mock', nodes, edges: [] }
}

function faultImpactAnalyzeMock(req: FaultImpactReq): FaultImpactResp {
  const scope = req.scope || { power: true, cool: true, network: true, business: true }
  const failed = new Set((req.faultIds || []).filter((x) => x != null))
  const faultNodes = _FI_SOURCES.filter((n) => failed.has(n.id))
  const affected = new Set(failed)
  // 简化传播: 任何供电/制冷链路节点故障 -> 机房级 IT 设备受影响
  const linkHit = faultNodes.some((n) => _FI_CRIT_CATS.has(n.category))
  const itBiz: Array<{ id: number; label: string; category: string; health: number }> = []
  if (scope.business !== false && linkHit) {
    let i = 0
    for (const room of ['A01', 'A02', 'B01']) {
      for (const cat of ['server', 'server', 'server', 'switch', 'gpu']) {
        i++
        const id = 100000 + i
        itBiz.push({ id, label: `${room}-${cat}-${i}`, category: cat, health: 78 })
        affected.add(id)
      }
    }
  }
  const nodes: FaultImpactResp['nodes'] = [
    ...faultNodes.map((n) => ({ id: n.id, label: n.label, kind: n.kind, domain: n.domain, category: n.category, status: n.status, health: n.health, roomCode: n.roomCode, state: 'fault' as const, hop: 0, critical: _FI_CRIT_CATS.has(n.category), business: null, slaRisk: null })),
    ...itBiz.map((d, idx) => {
      const biz = _FI_BIZ.find((b) => b.cats.includes(d.category))
      return { id: d.id, label: d.label, kind: d.category, domain: 'it', category: d.category, status: '在线', health: d.health, roomCode: 'A01', state: 'affected' as const, hop: 1, critical: false, business: biz?.business ?? null, slaRisk: biz ? 'medium' : null }
    }),
  ]
  const bizCount = scope.business !== false && linkHit ? _FI_BIZ.filter((b) => b.cats.includes('server')).length : 0
  const businesses: FaultImpactResp['businesses'] = (scope.business !== false && linkHit)
    ? _FI_BIZ.map((b) => ({
        business: b.business, criticalDevices: b.cats.includes('server') ? 1 : 0,
        affectedDevices: itBiz.filter((d) => b.cats.includes(d.category)).length,
        severity: b.cats.includes('server') ? 'high' : 'medium', sla: b.sla, note: b.note,
      })).filter((x) => x.affectedDevices > 0)
    : []
  const severity = !failed.size ? 'low' : (linkHit || businesses.length ? (linkHit && businesses.some((b) => b.severity === 'critical') ? 'critical' : 'high') : (affected.size > 0 ? 'medium' : 'low'))
  return {
    faultIds: Array.from(failed),
    generatedAt: new Date().toISOString(),
    nodes,
    edges: nodes.filter((n) => n.state === 'affected').map((n) => ({ source: faultNodes[0]?.id ?? 0, target: n.id, type: 'it_feed', label: '机房级冷量/电力丧失' })),
    mitigations: [],
    affectedIds: Array.from(affected).filter((x) => !failed.has(x)),
    summary: { severity, faultCount: failed.size, affectedCount: affected.size - failed.size, criticalPaths: faultNodes.filter((n) => _FI_CRIT_CATS.has(n.category)).length, slaRisk: businesses.length ? 'high' : (linkHit ? 'medium' : 'low'), bizCount },
    businesses,
    suggestion: faultNodes.length
      ? `故障源 ${faultNodes.length} 个: ${faultNodes.map((n) => n.label).join('、')}。${linkHit ? '已冲击关键供电/制冷节点, 优先切换冗余链路。' : ''}${businesses.length ? `业务域「${businesses[0].business}」(SLA ${businesses[0].sla}) 受影响最重, 建议立即启动容灾切换。` : '未直接波及核心业务域, 按常规工单处置。'}`
      : '未选择故障源, 请指定一个或多个候选故障节点后分析。',
  }
}

// ---- 应急演练离线兜底 (内存 CRUD, 与后端契约一致: 数字 id + steps/level/scope/duration) ----
let _memDrills: any[] = (DC.drill as any).plans.map((p: any) => ({ ...p }))
let _memDrillSeq = _memDrills.length + 1
let _memRecords: any[] = [
  { id: 1, planId: 2, planName: '冷源系统故障切换演练', date: '2026-06-20', participants: 8, startAt: '09:00', endAt: '10:30', score: 92, result: '通过', note: '切换耗时达标' },
  { id: 2, planId: 3, planName: '母联备自投切换演练', date: '2026-07-05', participants: 6, startAt: '14:00', endAt: '15:00', score: 88, result: '通过', note: '备自投动作正常' },
  { id: 3, planId: 1, planName: '市电全停-柴发接管演练', date: '2026-08-05', participants: 12, startAt: '10:00', endAt: '12:00', score: 0, result: '—', note: '待执行' },
]
let _memRecSeq = _memRecords.length + 1

function drillListMock(kw = '', type = ''): { stats: any; plans: any[] } {
  let plans = _memDrills.slice()
  if (kw) plans = plans.filter((p) => (p.name + p.code).includes(kw))
  if (type) plans = plans.filter((p) => p.type === type)
  const stats = {
    year: plans.length,
    done: plans.filter((p) => p.state === '已完成').length,
    pass: plans.filter((p) => p.result === '通过').length,
    next: (plans.find((p) => p.state !== '已完成')?.date + ' ' + plans.find((p) => p.state !== '已完成')?.name) || '—',
  }
  return { stats, plans }
}

function drillMutations(method: string, u: string, data: any): any {
  // POST /api/ops/drill  -> 新建
  if (method === 'POST' && u === '/api/ops/drill') {
    const id = _memDrillSeq++
    const code = data.code || `DR-${String(id).padStart(3, '0')}`
    const plan = { id, code, name: data.name || '', type: data.type || '电力', date: data.date || '', state: data.state || '计划中', result: data.result || '—', note: data.note || '', level: data.level || '—', scope: data.scope || '', duration: data.duration || 0, steps: data.steps || [] }
    _memDrills.push(plan)
    return plan as any
  }
  // PUT /api/ops/drill/:id
  if (method === 'PUT') {
    const m = u.match(/^\/api\/ops\/drill\/(\d+)$/)
    if (m) {
      const id = Number(m[1])
      const p = _memDrills.find((x) => x.id === id)
      if (p) Object.assign(p, { ...data, id })
      return p as any
    }
  }
  // DELETE /api/ops/drill/:id
  if (method === 'DELETE') {
    const m = u.match(/^\/api\/ops\/drill\/(\d+)$/)
    if (m) {
      const id = Number(m[1])
      _memDrills = _memDrills.filter((x) => x.id !== id)
      return { ok: true }
    }
  }
  // POST /api/ops/drill/records
  if (method === 'POST' && u === '/api/ops/drill/records') {
    const id = _memRecSeq++
    const rec = { id, planId: data.planId || 0, planName: data.planName || '', date: data.date || '', participants: data.participants || 0, startAt: data.startAt || '', endAt: data.endAt || '', score: data.score || 0, result: data.result || '—', note: data.note || '' }
    _memRecords.push(rec)
    return rec as any
  }
  // PUT /api/ops/drill/records/:id
  if (method === 'PUT' && u.startsWith('/api/ops/drill/records/')) {
    const id = Number(u.split('/').pop())
    const r = _memRecords.find((x) => x.id === id)
    if (r) Object.assign(r, { ...data, id })
    return r
  }
  // DELETE /api/ops/drill/records/:id
  if (method === 'DELETE' && u.startsWith('/api/ops/drill/records/')) {
    const id = Number(u.split('/').pop())
    _memRecords = _memRecords.filter((x) => x.id !== id)
    return { ok: true }
  }
  return null
}

/* =================== 租户管理 (阶段三 A · 资源运营) 离线兜底 =================== */
let _memTenants: any[] = [
  { id: 1, name: '云栖科技', code: 'TH-001', contact: '王经理', phone: '13800000001', industry: '互联网', contractNo: 'HT-2023-001', validFrom: '2023-01-01', validTo: '2026-12-31', status: 'active', rent: 120000, cabinets: 8, quotaCabinets: 10, quotaDevices: 200, quotaPowerKw: 160, quotaBandwidthMbps: 2000, usedDevices: 168, usedPowerKw: 142.6, usedBandwidthMbps: 1680, uOccupied: 264, note: '核心客户' },
  { id: 2, name: '智算网络', code: 'TH-002', contact: '李总', phone: '13800000002', industry: '人工智能', contractNo: 'HT-2023-002', validFrom: '2023-03-01', validTo: '2025-09-30', status: 'expired', rent: 200000, cabinets: 12, quotaCabinets: 12, quotaDevices: 320, quotaPowerKw: 300, quotaBandwidthMbps: 4000, usedDevices: 305, usedPowerKw: 292.4, usedBandwidthMbps: 3720, uOccupied: 396, note: '合同待续签' },
  { id: 3, name: '金信金融', code: 'TH-003', contact: '赵主管', phone: '13800000003', industry: '金融', contractNo: 'HT-2023-003', validFrom: '2023-06-01', validTo: '2027-06-30', status: 'active', rent: 150000, cabinets: 6, quotaCabinets: 10, quotaDevices: 150, quotaPowerKw: 120, quotaBandwidthMbps: 1500, usedDevices: 142, usedPowerKw: 119.8, usedBandwidthMbps: 980, uOccupied: 198, note: '等保三级' },
  { id: 4, name: '联创医疗', code: 'TH-004', contact: '孙主任', phone: '13800000004', industry: '医疗', contractNo: 'HT-2024-001', validFrom: '2024-01-15', validTo: '2026-01-14', status: 'pending', rent: 90000, cabinets: 4, quotaCabinets: 8, quotaDevices: 100, quotaPowerKw: 80, quotaBandwidthMbps: 1000, usedDevices: 61, usedPowerKw: 52.3, usedBandwidthMbps: 410, uOccupied: 132, note: '新签待启用' },
  { id: 5, name: '远图物流', code: 'TH-005', contact: '周经理', phone: '13800000005', industry: '物流', contractNo: 'HT-2024-002', validFrom: '2024-05-01', validTo: '2026-04-30', status: 'active', rent: 80000, cabinets: 5, quotaCabinets: 6, quotaDevices: 90, quotaPowerKw: 70, quotaBandwidthMbps: 900, usedDevices: 88, usedPowerKw: 68.9, usedBandwidthMbps: 870, uOccupied: 165, note: '机柜接近配额' },
]
let _memTenantSeq = 6

function _deriveHealth(t: any): 'normal' | 'warn' | 'over' {
  const WARN = 0.8
  const ratio = (used: number, quota: number) => (quota ? used / quota : 0)
  const rs = [ratio(t.cabinets || 0, t.quotaCabinets || 0), ratio(t.usedDevices || 0, t.quotaDevices || 0), ratio(t.usedPowerKw || 0, t.quotaPowerKw || 0), ratio(t.usedBandwidthMbps || 0, t.quotaBandwidthMbps || 0)]
  if (rs.some((r) => r >= 1)) return 'over'
  if (rs.some((r) => r >= WARN)) return 'warn'
  return 'normal'
}

function tenantListMock(params?: MockQuery): { tenants: any[]; total: number } {
  let list = _memTenants.slice()
  const kw = String(params?.kw ?? '').toLowerCase()
  if (kw) list = list.filter((t) => (t.name + t.code + t.contact).toLowerCase().includes(kw))
  const status = String(params?.status ?? '')
  if (status) list = list.filter((t) => t.status === status)
  return { tenants: list.map((t) => ({ ...t, health: _deriveHealth(t) })), total: list.length } as any
}

function tenantStatsMock(): any {
  const total = _memTenants.length
  const active = _memTenants.filter((t) => t.status === 'active').length
  const totalCabinets = _memTenants.reduce((s, t) => s + (t.cabinets || 0), 0)
  const totalPowerKw = Math.round(_memTenants.reduce((s, t) => s + (t.usedPowerKw || 0), 0) * 10) / 10
  let warnCount = 0
  let overCount = 0
  _memTenants.forEach((t) => {
    const h = _deriveHealth(t)
    if (h === 'over') overCount++
    else if (h === 'warn') warnCount++
  })
  return { total, active, totalCabinets, totalPowerKw, warnCount, overCount }
}

function tenantMutations(method: string, u: string, data: any): any {
  // GET 单条
  if (method === 'GET') {
    const m = u.match(/^\/api\/ops\/tenants\/(\d+)$/)
    if (m) {
      const t = _memTenants.find((x) => x.id === Number(m[1]))
      return t ? { ...t, health: _deriveHealth(t) } : null
    }
    if (u === '/api/ops/tenants/stats') return tenantStatsMock()
    if (u === '/api/ops/tenants') return tenantListMock(data)
  }
  // POST 新建
  if (method === 'POST' && u === '/api/ops/tenants') {
    const id = _memTenantSeq++
    const code = data.code || `TH-${String(id).padStart(3, '0')}`
    const t = { id, code, name: data.name || '', contact: data.contact || '', phone: data.phone || '', industry: data.industry || '', contractNo: data.contractNo || '', validFrom: data.validFrom || '', validTo: data.validTo || '', status: data.status || 'active', rent: data.rent || 0, cabinets: data.cabinets || 0, quotaCabinets: data.quotaCabinets || 0, quotaDevices: data.quotaDevices || 0, quotaPowerKw: data.quotaPowerKw || 0, quotaBandwidthMbps: data.quotaBandwidthMbps || 0, usedDevices: data.usedDevices || 0, usedPowerKw: data.usedPowerKw || 0, usedBandwidthMbps: data.usedBandwidthMbps || 0, uOccupied: data.uOccupied || 0, note: data.note || '' }
    _memTenants.push(t)
    return { ...t, health: _deriveHealth(t) }
  }
  // PUT 更新
  if (method === 'PUT') {
    const m = u.match(/^\/api\/ops\/tenants\/(\d+)$/)
    if (m) {
      const id = Number(m[1])
      const t = _memTenants.find((x) => x.id === id)
      if (t) Object.assign(t, { ...data, id })
      return t ? { ...t, health: _deriveHealth(t) } : null
    }
  }
  // DELETE 删除
  if (method === 'DELETE') {
    const m = u.match(/^\/api\/ops\/tenants\/(\d+)$/)
    if (m) {
      const id = Number(m[1])
      _memTenants = _memTenants.filter((x) => x.id !== id)
      return { ok: true }
    }
  }
  return null
}

function recentMetricsMock(deviceId: string, limit = 20): MetricRecordView[] {
  const meta = findReg(deviceId)
  const specs = specsFor(meta?.category, deviceId)
  const now = Date.now()
  const out: MetricRecordView[] = []
  for (let i = 0; i < limit; i++) {
    const spec = specs[i % specs.length]
    const age = i * 5000 // 每 5s 一条上报
    const ts = new Date(now - age).toISOString()
    const quality: MetricQuality =
      Math.random() < 0.92 ? 'good' : Math.random() < 0.5 ? 'uncertain' : 'bad'
    out.push({
      device_id: deviceId,
      ts,
      metric_name: spec.name,
      value: walkVal(spec, `${deviceId}::${spec.name}`),
      quality,
      unit: spec.unit,
      received_at: new Date(now - age + 300).toISOString(),
    })
  }
  return out
}

function realtimeMock(deviceId: string): MetricRealtimeResponse {
  const meta = findReg(deviceId)
  const specs = specsFor(meta?.category, deviceId)
  return {
    device_id: deviceId,
    ts: new Date().toISOString(),
    online: meta ? meta.online : true,
    points: specs.map((s) => ({
      metric_name: s.name,
      value: walkVal(s, `${deviceId}::${s.name}`),
      unit: s.unit,
      quality: 'good' as MetricQuality,
    })),
  }
}

/** 拉取所有在线设备的实时快照 — 同时推进随机游走, 供越限联动引擎消费 */
export function realtimeAllMock(): MetricRealtimeResponse[] {
  return MOCK_REGISTERED.filter((d) => d.online).map((d) => realtimeMock(d.device_id))
}

/** 越限联动引擎使用的设备元信息 (device_id → category) */
export const LINKAGE_DEVICES: { device_id: string; category: string; online: boolean }[] =
  MOCK_REGISTERED.map((d) => ({ device_id: d.device_id, category: d.category, online: d.online }))

function computeMinutes(start?: string, end?: string): number {
  if (start && end) {
    const ms = new Date(end).getTime() - new Date(start).getTime()
    if (!isNaN(ms) && ms > 0) return Math.max(5, Math.min(24 * 60, Math.round(ms / 60000)))
  }
  return 30
}

function historyMock(deviceId: string, minutes = 30, limit = 300): MetricHistoryResponse {
  const meta = findReg(deviceId)
  const specs = specsFor(meta?.category, deviceId)
  const unit: Record<string, string> = {}
  const series: Record<string, { ts: string; value: number; quality: MetricQuality }[]> = {}
  const points = Math.min(limit, Math.max(20, minutes))
  const now = Date.now()
  for (const s of specs) {
    unit[s.name] = s.unit
    const dec = s.decimals ?? (s.unit === 'kW' ? 0 : 1)
    const noise = s.noise ?? s.amp
    let cur = s.base
    const pts: { ts: string; value: number; quality: MetricQuality }[] = []
    for (let i = points - 1; i >= 0; i--) {
      const ts = new Date(now - i * 60000).toISOString()
      pts.push({ ts, value: +cur.toFixed(dec), quality: 'good' })
      cur = cur + (s.base - cur) * 0.08 + (Math.random() * 2 - 1) * noise
    }
    series[s.name] = pts
  }
  return { device_id: deviceId, unit, series }
}

/* ================= 告警规则引擎 / 告警历史 (兜底) ================= */

const ALARM_RULES: AlarmRuleDef[] = [
  {
    id: 1,
    category: 'hvac',
    metric: 'supply_temp',
    ruleCode: 'HVAC-SUPPLY-TEMP-HI',
    warnLo: null,
    warnHi: 18,
    critLo: null,
    critHi: 22,
    unit: '℃',
    enabled: true,
    status: 'enabled',
    source: 'DEFAULT',
  },
  {
    id: 2,
    category: 'hvac',
    metric: 'return_temp',
    ruleCode: 'HVAC-RETURN-TEMP-HI',
    warnLo: null,
    warnHi: 32,
    critLo: null,
    critHi: 38,
    unit: '℃',
    enabled: true,
    status: 'enabled',
    source: 'DEFAULT',
  },
  {
    id: 3,
    category: 'power',
    metric: 'power_kw',
    ruleCode: 'PWR-CHILLER-HI',
    warnLo: null,
    warnHi: 600,
    critLo: null,
    critHi: 680,
    unit: 'kW',
    enabled: true,
    status: 'enabled',
    source: 'DEFAULT',
  },
  {
    id: 4,
    category: 'common',
    metric: 'cpu_usage',
    ruleCode: 'CTRL-CPU-HI',
    warnLo: null,
    warnHi: 85,
    critLo: null,
    critHi: 95,
    unit: '%',
    enabled: true,
    status: 'silenced',
    source: 'DEFAULT',
  },
  {
    id: 5,
    category: 'power',
    metric: 'ups_load',
    ruleCode: 'PWR-UPS-LOAD-HI',
    warnLo: null,
    warnHi: 480,
    critLo: null,
    critHi: 520,
    unit: 'kW',
    enabled: true,
    status: 'enabled',
    source: 'DEFAULT',
  },
  {
    id: 6,
    category: 'fire',
    metric: 'fault_points',
    ruleCode: 'FIRE-FAULT',
    warnLo: 0,
    warnHi: 0,
    critLo: null,
    critHi: 1,
    unit: '个',
    enabled: true,
    status: 'enabled',
    source: 'DEFAULT',
  },
  {
    id: 7,
    category: 'security',
    metric: 'door_abnormal',
    ruleCode: 'SEC-DOOR-ABN',
    warnLo: 0,
    warnHi: 0,
    critLo: null,
    critHi: 1,
    unit: '次',
    enabled: false,
    status: 'disabled',
    source: 'DEFAULT',
  },
  {
    id: 8,
    category: 'hvac',
    metric: 'supply_temp_dev',
    ruleCode: 'HVAC-SUPPLY-DEV',
    warnLo: -12,
    warnHi: 12,
    critLo: -20,
    critHi: 20,
    unit: '%',
    enabled: true,
    status: 'enabled',
    source: 'DEFAULT',
  },
]

function alarmRulesMock(): AlarmRuleDef[] {
  return ALARM_RULES.map((r) => ({ ...r }))
}

function alarmEngineStateMock(): AlarmEngineState {
  return {
    totalRules: ALARM_RULES.length,
    enabledCount: ALARM_RULES.filter((r) => r.enabled).length,
    triggeredCount: 0,
    silencedCount: ALARM_RULES.filter((r) => r.status === 'silenced').length,
  }
}

function genAlarmEvents(): AlarmEvent[] {
  const evs: AlarmEvent[] = []
  for (let i = 0; i < 42; i++) {
    const r = ALARM_RULES[i % ALARM_RULES.length]
    const ageMin = Math.floor(Math.random() * 60 * 24 * 7)
    const triggeredAt = new Date(Date.now() - ageMin * 60000).toISOString()
    const roll = Math.random()
    let status: AlarmEvent['status'] = 'active'
    let acknowledgedAt: string | undefined
    let acknowledgedBy: string | undefined
    let resolvedAt: string | undefined
    let resolvedBy: string | undefined
    let note: string | undefined
    if (roll > 0.6) {
      status = 'resolved'
      acknowledgedAt = new Date(Date.now() - ageMin * 60000 + 120000).toISOString()
      acknowledgedBy = '值班员'
      resolvedAt = new Date(Date.now() - ageMin * 60000 + 300000).toISOString()
      resolvedBy = Math.random() > 0.5 ? '系统' : '值班员'
      note = '已处置并闭环'
    } else if (roll > 0.3) {
      status = 'acknowledged'
      acknowledgedAt = new Date(Date.now() - ageMin * 60000 + 90000).toISOString()
      acknowledgedBy = '值班员'
    }
    const ref = r.critHi ?? r.warnHi ?? 0
    const value = +(ref + (Math.random() * 2 - 1) * 2).toFixed(1)
    const level: AlarmEvent['level'] = r.critHi != null ? 'crit' : 'warn'
    const message = `${r.category} · ${r.metric} 触发 (${r.metric}=${value}${r.unit ?? ''})`
    evs.push({
      id: `EVT-${String(1000 + i)}`,
      ruleId: String(r.id),
      ruleName: r.ruleCode ?? r.metric,
      metric: r.metric,
      level,
      system: r.category,
      message,
      value,
      threshold: ref,
      unit: r.unit,
      status,
      triggeredAt,
      acknowledgedAt,
      acknowledgedBy,
      resolvedAt,
      resolvedBy,
      note,
      autoResolved: status === 'resolved' && Math.random() > 0.5,
      escalationCount: status === 'active' ? Math.floor(Math.random() * 3) : 0,
    })
  }
  return evs.sort((a, b) => +new Date(b.triggeredAt) - +new Date(a.triggeredAt))
}

const ALARM_EVENTS: AlarmEvent[] = genAlarmEvents()

function inWindow(iso: string, from?: string, to?: string): boolean {
  const t = +new Date(iso)
  if (from && t < +new Date(from)) return false
  if (to && t > +new Date(to)) return false
  return true
}

function alarmHistoryMock(params?: AlarmHistoryQuery): AlarmHistoryResponse {
  const p = params ?? {}
  let items = ALARM_EVENTS.filter(
    (e) =>
      (!p.system || e.system === p.system) &&
      (!p.level || e.level === p.level) &&
      (!p.status || e.status === p.status) &&
      inWindow(e.triggeredAt, p.from, p.to),
  )
  const total = items.length
  const page = p.page ?? 1
  const limit = p.limit ?? 20
  items = items.slice((page - 1) * limit, page * limit)
  const now = Date.now()
  const within = (iso: string, ms: number) => +new Date(iso) >= now - ms
  const stats = {
    total24h: ALARM_EVENTS.filter((e) => within(e.triggeredAt, 86400000)).length,
    active24h: ALARM_EVENTS.filter((e) => e.status === 'active' && within(e.triggeredAt, 86400000))
      .length,
    resolved24h: ALARM_EVENTS.filter(
      (e) => e.status === 'resolved' && e.resolvedAt && within(e.resolvedAt, 86400000),
    ).length,
    mttaMin: DC.alarms.sla.mttaMin,
    mttrMin: DC.alarms.sla.mttrMin,
    bySystem: ALARM_EVENTS.reduce<Record<string, number>>((acc, e) => {
      acc[e.system] = (acc[e.system] ?? 0) + 1
      return acc
    }, {}),
    byLevel: {
      crit: ALARM_EVENTS.filter((e) => e.level === 'crit').length,
      warn: ALARM_EVENTS.filter((e) => e.level === 'warn').length,
      info: ALARM_EVENTS.filter((e) => e.level === 'info').length,
    },
  }
  return { items, total, page, limit, stats }
}

/* ================= 机柜 / 统一设备台账 (兜底) ================= */
function genCabinets(): Cabinet[] {
  const list: Cabinet[] = []
  let id = 1
  for (let ri = 1; ri <= 12; ri++) {
    const room = `R${String(ri).padStart(2, '0')}`
    for (let j = 1; j <= 16; j++) {
      const uTotal = 42
      const uUsed = Math.floor(rnd(18, 41, 0))
      const rated = +rnd(4, 8).toFixed(1)
      const cur = +(rated * rnd(0.35, 0.95)).toFixed(1)
      const status = cur / rated > 0.9 ? '高负载' : Math.random() < 0.04 ? '告警' : '正常'
      list.push({
        id,
        idc_id: 1,
        code: `${room}-C${String(j).padStart(2, '0')}`,
        room,
        row: j % 2 ? 'B' : 'A',
        u_total: uTotal,
        u_used: uUsed,
        rated_power_kw: rated,
        current_power_kw: cur,
        status,
      })
      id++
    }
  }
  return list
}
const CABINETS: Cabinet[] = genCabinets()

function cabinetsMock(params?: MockQuery): Paginated<Cabinet> {
  let items = CABINETS
  if (params?.room) items = items.filter((c) => c.room === params.room)
  const total = items.length
  const page = Number(params?.page ?? 1)
  const size = Number(params?.size ?? 20)
  const sliced = items.slice((page - 1) * size, page * size)
  return { total, page, size, items: sliced }
}

/** 机柜测点随机游走状态 (cabinet id → 当前值) */
const cabWalk = new Map<number, { t: number; h: number; p: number }>()

function cabinetMetricsMock(id: number, params?: MockQuery): CabinetMetrics {
  const cab = CABINETS.find((c) => c.id === id)
  const minutes = Number(params?.minutes ?? 60)
  const step = Number(params?.step_sec ?? 60)
  const n = Math.max(2, Math.floor((minutes * 60) / step))
  const now = Date.now()
  const code = cab?.code ?? `CAB-${id}`
  const baseT = 22 + (id % 5)
  const baseH = 45 + (id % 8)
  const baseP = cab ? cab.current_power_kw : 5
  let cur = cabWalk.get(id) ?? { t: baseT, h: baseH, p: baseP }
  const tArr: { ts: string; value: number }[] = []
  const hArr: { ts: string; value: number }[] = []
  const pArr: { ts: string; value: number }[] = []
  for (let i = 0; i < n; i++) {
    const ts = new Date(now - (n - 1 - i) * step * 1000).toISOString()
    cur.t = cur.t + (baseT - cur.t) * 0.06 + (Math.random() * 2 - 1) * 0.5
    cur.h = cur.h + (baseH - cur.h) * 0.06 + (Math.random() * 2 - 1) * 1.5
    cur.p = cur.p + (baseP - cur.p) * 0.06 + (Math.random() * 2 - 1) * Math.max(0.4, baseP * 0.05)
    tArr.push({ ts, value: +cur.t.toFixed(1) })
    hArr.push({ ts, value: +cur.h.toFixed(1) })
    pArr.push({ ts, value: +cur.p.toFixed(2) })
  }
  cabWalk.set(id, { t: cur.t, h: cur.h, p: cur.p })
  return {
    cabinet_id: id,
    code,
    range_minutes: minutes,
    temperature: tArr,
    humidity: hArr,
    power_kw: pArr,
  }
}

interface EqSeed {
  d: string
  c: string
  n: string
  v: string
  m: string
}
const EQ_SEEDS: EqSeed[] = [
  { d: 'hvac_source', c: 'chiller', n: '冷水机组', v: 'Carrier', m: '19XR' },
  { d: 'hvac_terminal', c: 'crac', n: '精密空调', v: 'Emerson', m: 'DX' },
  { d: 'power_lv', c: 'ups', n: 'UPS 电源', v: 'Vertiv', m: 'Liebert' },
  { d: 'power_lv', c: 'transformer', n: '变压器', v: 'Siemens', m: 'SCB13' },
  { d: 'power_hv', c: 'incomer', n: '中压进线', v: 'ABB', m: 'VD4' },
  { d: 'security', c: 'camera', n: '摄像机', v: 'Hikvision', m: 'IPC' },
  { d: 'fire', c: 'detector', n: '烟感探测器', v: 'Honeywell', m: 'JTY' },
  { d: 'fuel', c: 'fuel_tank', n: '日用油箱', v: '国产品牌', m: 'DT' },
]

function genEquipment(): Equipment[] {
  const list: Equipment[] = []
  let id = 1
  for (const s of EQ_SEEDS) {
    for (let i = 1; i <= 8; i++) {
      const status = pick(['运行', '运行', '运行', '待机', '故障', '维保'])
      list.push({
        id,
        idc_id: 1,
        room_id: (i % 12) + 1,
        code: `${s.c.toUpperCase()}-${String(i).padStart(3, '0')}`,
        name: `${s.n} ${String(i).padStart(2, '0')}`,
        domain: s.d,
        category: s.c,
        vendor: s.v,
        model: s.m,
        status,
        load_pct: +rnd(20, 95).toFixed(0),
        run_hours: Math.floor(rnd(1000, 20000)),
        redundancy: pick(['N', 'N+1', '2N', '无']),
        attrs: { room: `R${String((i % 12) + 1).padStart(2, '0')}` },
      })
      id++
    }
  }
  return list
}
const EQUIPMENT: Equipment[] = genEquipment()

function equipmentMock(params?: MockQuery): Equipment[] {
  let items = EQUIPMENT
  if (params?.domain) items = items.filter((e) => e.domain === params.domain)
  if (params?.category) items = items.filter((e) => e.category === params.category)
  if (params?.status) items = items.filter((e) => e.status === params.status)
  const limit = Number(params?.limit ?? 200)
  return items.slice(0, limit)
}

function equipmentOneMock(id: number): Equipment | undefined {
  return EQUIPMENT.find((e) => e.id === id)
}

/** 设备测点随机游走状态 (equipment id → metric → 当前值) */
const eqWalk = new Map<number, Record<string, number>>()

function equipmentMetricsMock(id: number, params?: MockQuery): EquipmentMetrics {
  const eq = EQUIPMENT.find((e) => e.id === id)
  const minutes = Number(params?.minutes ?? 60)
  const step = Number(params?.step_sec ?? 60)
  const n = Math.max(2, Math.floor((minutes * 60) / step))
  const now = Date.now()
  const code = eq?.code ?? `EQ-${id}`
  const metrics = ['inlet_temp', 'outlet_temp', 'power_kw', 'cpu_usage']
  const baseFor = (m: string) =>
    m === 'inlet_temp' ? 22 : m === 'outlet_temp' ? 30 : m === 'power_kw' ? 120 : 35
  const noiseFor = (m: string) =>
    m === 'inlet_temp' ? 0.6 : m === 'outlet_temp' ? 0.8 : m === 'power_kw' ? 8 : 4
  const decFor = (m: string) => (m === 'power_kw' ? 0 : 1)
  let cur = eqWalk.get(id)
  if (!cur) {
    cur = {}
    for (const m of metrics) cur[m] = baseFor(m)
    eqWalk.set(id, cur)
  }
  const series: Record<string, { ts: string; value: number }[]> = {}
  for (const m of metrics) {
    const arr: { ts: string; value: number }[] = []
    const base = baseFor(m)
    const noise = noiseFor(m)
    for (let i = 0; i < n; i++) {
      const ts = new Date(now - (n - 1 - i) * step * 1000).toISOString()
      cur[m] = cur[m] + (base - cur[m]) * 0.06 + (Math.random() * 2 - 1) * noise
      arr.push({ ts, value: +cur[m].toFixed(decFor(m)) })
    }
    series[m] = arr
  }
  return { equipment_id: id, code, range_minutes: minutes, metrics, series }
}

/* =====================================================================
 * 内存写操作存储 (后端不可达时用于演示 CRUD / import / 保存)
 * - KEY 前缀区分域: alarm-rules / knowledge / shifts / handovers / devices / metric-defs
 * - 所有写入均持久化到内存, 同一页面刷新期间查询可回读
 * ===================================================================== */

/** 规范化 URL: 去除 query string 和 hash，保证严格匹配与 startsWith 匹配在带参场景下也命中 */
function normalizeUrl(url: string): string {
  if (!url) return url
  // 先去掉 hash，再去掉 query
  const noHash = url.split('#')[0]
  const noQuery = noHash.split('?')[0]
  return noQuery || '/'
}

interface ShiftRecord {
  id: number
  date?: string
  shiftDate?: string
  status?: string
  [key: string]: unknown
}

interface HandoverRecord {
  id: number
  shiftDate?: string
  status?: string
  [key: string]: unknown
}

interface MetricDef {
  id: number
  deviceId: string
  metricName: string
  label?: string
  unit?: string
  dataType: string
  description?: string
  enabled: boolean
  [key: string]: unknown
}

interface MockStore {
  alarmRules: AlarmRuleDef[]
  knowledge: KnowledgeItem[]
  shifts: ShiftRecord[] // 排班记录 (结构见 rdShifts)
  handovers: HandoverRecord[] // 交接班记录
  metricDefs: Record<string, MetricDef[]> // deviceId → metricDef list
}

const STORE: MockStore = {
  alarmRules: ALARM_RULES.map((r) => ({ ...r })),
  knowledge: (() => {
    // 从 DC.knowledge 派生初始条目，使列表非空
    const types = ['sop', 'drawing', 'manual', 'emergency', 'case', 'training'] as const
    const domains = ['hvac', 'power', 'security', 'network', 'fire']
    const cats = ['应急预案', '运行 SOP', '设备手册', '竣工图纸', '故障案例库', '培训资料']
    const list: KnowledgeItem[] = []
    for (let i = 0; i < 24; i++) {
      const t = types[i % types.length]
      list.push({
        id: i + 1,
        code: `KB-${String(i + 1).padStart(4, '0')}`,
        title: `${cats[i % cats.length]} #${i + 1}`,
        category: cats[i % cats.length],
        domain: domains[i % domains.length],
        type: t,
        summary: '这是知识库条目自动生成的摘要，用于演示知识库列表、搜索与审核流程。',
        content: '详细内容：操作流程、检查要点、处置步骤、注意事项等完整的文档内容。\n\n步骤1：确认环境\n步骤2：执行操作\n步骤3：验证结果',
        tags: ['演示', domains[i % domains.length]],
        relatedCategories: [cats[i % cats.length]],
        relatedDomains: [domains[i % domains.length]],
        relatedMetrics: [],
        owner: 'system',
        version: 1,
        hot: i < 3,
        reviewStatus: i % 5 === 0 ? 'pending' : 'approved',
        createdAt: new Date(Date.now() - i * 86400000).toISOString(),
        updatedAt: new Date(Date.now() - i * 86400000).toISOString(),
        steps: i % 2 ? ['确认上下文', '执行主操作', '验证结果'] : [],
      })
    }
    return list
  })(),
  shifts: (() => {
    // 未来 7 天的初始排班
    const arr: ShiftRecord[] = []
    const leaders = ['张伟', '李娜', '王强', '赵敏']
    for (let i = 0; i < 14; i++) {
      const day = new Date(Date.now() + i * 86400000).toISOString().slice(0, 10)
      arr.push({
        id: i * 2 + 1,
        date: day,
        shift: 'day',
        leader: leaders[i % leaders.length],
        members: [
          { name: leaders[i % leaders.length], role: '值班长', phone: '13800000000' },
          { name: '组员A', role: '主值', phone: '13800000001' },
        ],
        note: i % 3 === 0 ? '注意负荷高峰' : '',
        createdAt: new Date().toISOString(),
      })
      arr.push({
        id: i * 2 + 2,
        date: day,
        shift: 'night',
        leader: leaders[(i + 1) % leaders.length],
        members: [
          { name: leaders[(i + 1) % leaders.length], role: '值班长', phone: '13800000002' },
          { name: '组员B', role: '主值', phone: '13800000003' },
        ],
        note: '',
        createdAt: new Date().toISOString(),
      })
    }
    return arr
  })(),
  handovers: [],
  metricDefs: {},
}

/** 简单 ID 自增器 */
function nextIdFor(arr: { id: number }[]): number {
  return 1 + arr.reduce((m, x) => Math.max(m, Number(x.id) || 0), 0)
}

/* ---------- 告警规则写操作 ---------- */
function wrAlarmRule(method: string, url: string, data: any, cfg: any): any {
  const toggleM = url.match(/^\/api\/alarm-rules\/([^/]+)\/toggle$/)
  const silenceM = url.match(/^\/api\/alarm-rules\/([^/]+)\/silence$/)
  const idM = url.match(/^\/api\/alarm-rules\/([^/]+)$/)

  if (method === 'post' && url === '/api/alarm-rules') {
    const newOne = {
      id: nextIdFor(STORE.alarmRules),
      ruleCode: data.metric
        ? `RULE-${data.metric.toUpperCase()}-${nextIdFor(STORE.alarmRules)}`
        : `RULE-${nextIdFor(STORE.alarmRules)}`,
      status: data.enabled ? 'enabled' : 'disabled',
      source: 'USER',
      ...data,
      createdAt: new Date().toISOString(),
    } as AlarmRuleDef
    STORE.alarmRules.push(newOne)
    return { ...newOne }
  }
  if (method === 'put' && idM) {
    const id = Number(decodeURIComponent(idM[1]))
    const idx = STORE.alarmRules.findIndex((r) => Number(r.id) === id)
    if (idx < 0) throw { response: { data: { message: '规则不存在', detail: '规则不存在' } } }
    STORE.alarmRules[idx] = { ...STORE.alarmRules[idx], ...data, updatedAt: new Date().toISOString() } as any
    return { ...STORE.alarmRules[idx] }
  }
  if (method === 'delete' && idM) {
    const id = Number(decodeURIComponent(idM[1]))
    STORE.alarmRules = STORE.alarmRules.filter((r) => Number(r.id) !== id)
    return { ok: true }
  }
  if (method === 'patch' && toggleM) {
    const id = Number(decodeURIComponent(toggleM[1]))
    const r = STORE.alarmRules.find((x) => Number(x.id) === id)
    if (!r) throw { response: { data: { detail: '规则不存在' } } }
    r.enabled = !r.enabled
    r.status = r.enabled ? 'enabled' : 'disabled'
    return { ...r }
  }
  if (method === 'patch' && silenceM) {
    const id = Number(decodeURIComponent(silenceM[1]))
    const r = STORE.alarmRules.find((x) => Number(x.id) === id)
    if (!r) throw { response: { data: { detail: '规则不存在' } } }
    r.status = 'silenced'
    return { ...r }
  }
  return undefined
}

/* ---------- 知识库写操作 ---------- */
function wrKnowledge(method: string, url: string, data: any, cfg: any): any {
  const idM = url.match(/^\/api\/ops\/knowledge\/(\d+)(\/review)?$/)
  if (url === '/api/ops/knowledge/import') {
    // 文件导入: 解析文件内容 -> 生成待审核条目
    const file: File | undefined = cfg?.__file
    const count = Math.max(1, file ? Math.min(5, Math.ceil(file.size / 8192)) : 2)
    const items: KnowledgeItem[] = []
    const createdIdStart = nextIdFor(STORE.knowledge)
    for (let i = 0; i < count; i++) {
      items.push({
        id: createdIdStart + i,
        title: `导入条目 #${createdIdStart + i} (${file?.name ?? '指导书.txt'})`,
        category: '运行 SOP',
        domain: 'ops',
        type: 'manual',
        summary: `通过文件导入自动创建的知识条目，等待审核入库。(模拟解析第 ${i + 1} 段)`,
        content: file ? `已从文件 ${file.name} 解析内容 (${file.size} bytes)\n\n请在待审核列表确认后入库。` : '文件内容已解析，待审核。',
        tags: ['导入', '待审核'],
        version: '0.1',
        reviewStatus: 'pending',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      } as any)
    }
    STORE.knowledge.push(...items)
    return {
      created: count,
      skipped: 0,
      total: count,
      imported: count,
      items,
      note: `导入文件 ${file?.name ?? 'unknown'} 共 ${count} 条，已进入待审核队列`,
    }
  }
  if (method === 'post' && url === '/api/ops/knowledge') {
    const id = nextIdFor(STORE.knowledge)
    const newOne = {
      id,
      reviewStatus: 'approved',
      version: '1.0',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...data,
    } as any
    STORE.knowledge.unshift(newOne)
    return { ...newOne }
  }
  if (method === 'put' && idM && !idM[2]) {
    const id = Number(idM[1])
    const idx = STORE.knowledge.findIndex((k) => k.id === id)
    if (idx < 0) throw { response: { data: { detail: '条目不存在' } } }
    STORE.knowledge[idx] = { ...STORE.knowledge[idx], ...data, updatedAt: new Date().toISOString() }
    return { ...STORE.knowledge[idx] }
  }
  if (method === 'delete' && idM && !idM[2]) {
    const id = Number(idM[1])
    STORE.knowledge = STORE.knowledge.filter((k) => k.id !== id)
    return { ok: true }
  }
  if (method === 'post' && idM && idM[2]) {
    const id = Number(idM[1])
    const r = STORE.knowledge.find((k) => k.id === id)
    if (!r) throw { response: { data: { detail: '条目不存在' } } }
    r.reviewStatus = data.status === 'approved' ? 'approved' : 'rejected'
    ;(r as any).reviewNote = data.note || ''
    r.updatedAt = new Date().toISOString()
    return { ...r }
  }
  return undefined
}

/* ---------- 排班 / 交接写操作 ---------- */
function wrShift(method: string, url: string, data: any): any {
  // handover
  const handId = url.match(/^\/api\/ops\/shift\/handover\/(\d+)$/)
  if (url === '/api/ops/shift/handover') {
    if (method === 'post') {
      const id = nextIdFor(STORE.handovers)
      const newOne = {
        id,
        status: 'completed',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        ...data,
      }
      STORE.handovers.push(newOne)
      return { ...newOne } as any
    }
    return undefined
  }
  if (handId) {
    const id = Number(handId[1])
    if (method === 'put') {
      const idx = STORE.handovers.findIndex((h) => h.id === id)
      if (idx < 0) throw { response: { data: { detail: '交接记录不存在' } } }
      STORE.handovers[idx] = { ...STORE.handovers[idx], ...data, updatedAt: new Date().toISOString() }
      return { ...STORE.handovers[idx] }
    }
    if (method === 'delete') {
      STORE.handovers = STORE.handovers.filter((h) => h.id !== id)
      return { ok: true }
    }
  }
  // shift
  const shiftId = url.match(/^\/api\/ops\/shift\/(\d+)$/)
  if (method === 'post' && url === '/api/ops/shift') {
    const id = nextIdFor(STORE.shifts)
    const newOne = {
      id,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      ...data,
    }
    STORE.shifts.push(newOne)
    return { ...newOne } as any
  }
  if (shiftId) {
    const id = Number(shiftId[1])
    if (method === 'put') {
      const idx = STORE.shifts.findIndex((s) => s.id === id)
      if (idx < 0) throw { response: { data: { detail: '排班不存在' } } }
      STORE.shifts[idx] = { ...STORE.shifts[idx], ...data, updatedAt: new Date().toISOString() }
      return { ...STORE.shifts[idx] }
    }
    if (method === 'delete') {
      STORE.shifts = STORE.shifts.filter((s) => s.id !== id)
      return { ok: true }
    }
  }
  return undefined
}

/* ---------- 外部设备 + 测点定义写操作 ---------- */
function wrExternal(method: string, url: string, data: any): any {
  // 设备注册 / 更新 / 删除
  if (method === 'post' && url === '/api/external/devices/register') {
    const did = data.device_id
    if (MOCK_REGISTERED.find((d) => d.device_id === did)) {
      return { status: 'duplicate', device_id: did, message: '设备已存在' }
    }
    const newDev: any = {
      device_id: did,
      name: data.name ?? did,
      model: data.model ?? 'Unknown',
      ip: data.ip ?? '',
      sn: data.sn ?? '',
      vendor: data.vendor ?? '',
      domain: data.domain ?? 'unknown',
      category: data.category ?? 'chiller',
      protocol: data.protocol ?? 'modbus',
      location: data.location ?? '',
      online: true,
      registeredAt: new Date().toISOString(),
    }
    MOCK_REGISTERED.push(newDev)
    return { status: 'created', device_id: did, message: '设备注册成功' } as any
  }
  const devM = url.match(/^\/api\/external\/devices\/([^/]+)$/)
  if (devM) {
    const did = decodeURIComponent(devM[1])
    const idx = MOCK_REGISTERED.findIndex((d) => d.device_id === did)
    if (method === 'put') {
      if (idx < 0) throw { response: { data: { detail: '设备不存在' } } }
      MOCK_REGISTERED[idx] = { ...MOCK_REGISTERED[idx], ...data } as any
      return { status: 'updated', device_id: did, message: '设备已更新' }
    }
    if (method === 'delete') {
      if (idx < 0) throw { response: { data: { detail: '设备不存在' } } }
      MOCK_REGISTERED.splice(idx, 1)
      delete STORE.metricDefs[did]
      return { status: 'deleted', device_id: did, message: '设备已删除' }
    }
  }
  // 测点定义 CRUD
  const mdM = url.match(/^\/api\/external\/devices\/([^/]+)\/metric-defs(\/(\d+))?$/)
  if (mdM) {
    const did = decodeURIComponent(mdM[1])
    const mdId = mdM[3] ? Number(mdM[3]) : null
    if (!STORE.metricDefs[did]) {
      // 初始值: 从 THING_MODELS 默认派生
      const specs = specsFor(MOCK_REGISTERED.find((d) => d.device_id === did)?.category, did)
      STORE.metricDefs[did] = specs.map((s, i) => ({
        id: i + 1,
        deviceId: did,
        metricName: s.name,
        label: s.name,
        unit: s.unit,
        dataType: 'number',
        description: s.name,
        enabled: true,
      }))
    }
    const list = STORE.metricDefs[did]
    if (method === 'get') {
      // GET 由 mockForUrl 读取，这里兜底
      return list
    }
    if (method === 'post') {
      const id = nextIdFor(list)
      const newMd = { id, deviceId: did, metricName: data.metricName ?? data.label ?? '', enabled: true, dataType: 'number', ...data }
      list.push(newMd)
      return { ...newMd } as any
    }
    if (method === 'put' && mdId != null) {
      const idx = list.findIndex((m: any) => m.id === mdId)
      if (idx < 0) throw { response: { data: { detail: '测点不存在' } } }
      list[idx] = { ...list[idx], ...data }
      return { ...list[idx] }
    }
    if (method === 'delete' && mdId != null) {
      STORE.metricDefs[did] = list.filter((m: any) => m.id !== mdId)
      return { ok: true }
    }
  }
  return undefined
}

/* ---------- 写操作总入口 ---------- */
export function mockWriteForUrl(
  method: string,
  url: string,
  data: any,
  cfg?: { params?: MockQuery; __file?: File },
): unknown | undefined {
  try {
    // 关键修复: 先规范化 URL（去掉 ?query 和 #hash），保证带参请求也能命中 CRUD 兜底
    const u = normalizeUrl(url)
    // 告警规则
    if (u.startsWith('/api/alarm-rules')) return wrAlarmRule(method, u, data, cfg)
    // 知识库
    if (u.startsWith('/api/ops/knowledge')) return wrKnowledge(method, u, data, cfg)
    // 排班/交接
    if (u.startsWith('/api/ops/shift')) return wrShift(method, u, data)
    // 外部设备 + 测点
    if (u.startsWith('/api/external')) return wrExternal(method, u, data)
    // 故障影响分析 (POST 计算, 离线兜底直接返回传播结果)
    if (u === '/api/ops/fault-impact/analyze') return faultImpactAnalyzeMock(data || { faultIds: [] })
    // 应急演练 (内存 CRUD 兜底)
    if (u === '/api/ops/drill' || u.startsWith('/api/ops/drill/')) {
      const r = drillMutations(method, u, data || {})
      return r ?? { ok: true }
    }
    // 租户管理 (内存 CRUD 兜底)
    if (u === '/api/ops/tenants' || u.startsWith('/api/ops/tenants/')) {
      const r = tenantMutations(method, u, data || {})
      if (r !== null) return r
    }
  } catch (e) {
    // 模拟写操作内部校验错误 (统一抛给上层走异常分支)
    throw e
  }
  return undefined
}

/* ---------- 覆盖读操作以返回 STORE 内存 (新增/修改后能回读) ---------- */
function rdAlarmRules(): AlarmRuleDef[] {
  return STORE.alarmRules.map((r) => ({ ...r }))
}
function rdShifts(params?: MockQuery): any[] {
  let list = STORE.shifts.slice()
  if (params?.start) list = list.filter((s) => s.date >= String(params.start))
  if (params?.end) list = list.filter((s) => s.date <= String(params.end))
  return list
}
function rdHandovers(params?: MockQuery): { items: any[]; total: number } {
  let list = STORE.handovers.slice()
  if (params?.shiftDate) list = list.filter((h) => h.shiftDate === String(params.shiftDate))
  if (params?.status) list = list.filter((h) => h.status === String(params.status))
  return { items: list, total: list.length }
}
function rdKnowledge(params?: any): any {
  let list = STORE.knowledge.slice()
  if (params?.category) list = list.filter((k) => k.category === params.category)
  if (params?.q) {
    const q = String(params.q).toLowerCase()
    list = list.filter(
      (k) =>
        String(k.title).toLowerCase().includes(q) ||
        String(k.content || '').toLowerCase().includes(q) ||
        (k.tags || []).some((t: string) => t.toLowerCase().includes(q)),
    )
  }
  const total = list.length
  const page = Number(params?.page ?? 1)
  const pageSize = Number(params?.page_size ?? 20)
  const items = list.slice((page - 1) * pageSize, page * pageSize)
  return { items, total, page, page_size: pageSize }
}
function rdKnowledgeCategories(): { categories: { name: string; count: number }[]; total: number } {
  const map = new Map<string, number>()
  for (const k of STORE.knowledge) {
    if (!k.category) continue
    map.set(k.category, (map.get(k.category) ?? 0) + 1)
  }
  const categories = Array.from(map.entries()).map(([name, count]) => ({ name, count }))
  return { categories, total: categories.length }
}
function rdPendingKnowledge(): { total: number; items: KnowledgeItem[] } {
  const items = STORE.knowledge.filter((k) => k.reviewStatus === 'pending')
  return { total: items.length, items }
}
function rdMetricDefs(deviceId: string): any[] {
  if (!STORE.metricDefs[deviceId]) {
    const specs = specsFor(MOCK_REGISTERED.find((d) => d.device_id === deviceId)?.category, deviceId)
    STORE.metricDefs[deviceId] = specs.map((s, i) => ({
      id: i + 1,
      deviceId,
      metricName: s.name,
      label: s.name,
      unit: s.unit,
      dataType: 'number',
      description: s.name,
      enabled: true,
    }))
  }
  return STORE.metricDefs[deviceId].slice()
}

/**
 * 按请求 URL 返回对应的模拟数据, 供后端不可达时兜底。
 * - 业务域 GET (精确匹配) 返回旧版 DC.* 静态数据;
 * - 外部设备接入契约 (/api/external/*) 支持精确匹配与含设备 ID 的动态前缀匹配。
 * - 排班/知识库/告警规则优先从内存 STORE 回读，保证增删改后刷新可见。
 */
export function mockForUrl(url: string, cfg?: { params?: MockQuery }): unknown | undefined {
  // 关键修复: 先规范化 URL（去掉 ?query 和 #hash），带参请求也能严格命中内存回读分支
  const u = normalizeUrl(url)

  // ---- 优先走内存回读 (写操作后可见) ----
  if (u === '/api/alarm-rules') return rdAlarmRules()
  if (u === '/api/ops/shift') return rdShifts(cfg?.params)
  if (u === '/api/ops/shift/handover') return rdHandovers(cfg?.params)
  if (u === '/api/ops/knowledge') return rdKnowledge(cfg?.params)
  if (u === '/api/ops/knowledge/categories') return rdKnowledgeCategories()
  if (u === '/api/ops/knowledge/review/pending') return rdPendingKnowledge()
  const mdm = u.match(/^\/api\/external\/devices\/([^/]+)\/metric-defs$/)
  if (mdm) return rdMetricDefs(decodeURIComponent(mdm[1]))

  const table: Record<string, unknown> = {
    '/api/dashboard/overview': dashboardOverview(),
    '/api/hvac/chiller-plant': DC.chillerPlant,
    '/api/hvac/crac': DC.crac,
    '/api/power/hv': DC.hv,
    '/api/power/lv': DC.lv,
    '/api/power/genset': DC.genset,
    '/api/power/fuel': DC.fuel,
    '/api/power/battery': DC.battery,
    '/api/security/cctv': DC.cctv,
    '/api/security/acs': DC.acs,
    '/api/security/ids': DC.ids,
    '/api/security/fire': DC.fire,
    '/api/ops/twin': DC.twin,
    '/api/ops/capacity': DC.capacity,
    '/api/ops/alarms': DC.alarms,
    '/api/ops/energy': DC.energy,
    '/api/ops/tickets': DC.tickets,
    '/api/ops/inspect': DC.inspect,
    '/api/ops/maintain': DC.maintain,
    '/api/ops/drill': drillListMock(),
    '/api/ops/drill/records': { records: _memRecords, total: _memRecords.length },
    '/api/ops/tenants': tenantListMock(cfg?.params),
    '/api/ops/tenants/stats': tenantStatsMock(),
    '/api/ops/risk': DC.risk,
    '/api/ops/fault-impact/sources': faultImpactSourcesMock(),
  }
  if (u in table) return table[u]

  // ---- 租户详情 (单条) 离线兜底 ----
  if (u.startsWith('/api/ops/tenants')) {
    const r = tenantMutations('GET', u, cfg?.params)
    if (r !== null) return r
  }

  // ---- 物模型管理 (/api/thing-models) 离线兜底 (与后端 list_models 一致返回数组) ----
  if (u === '/api/thing-models') {
    const kw = String(cfg?.params?.kw ?? '').toLowerCase()
    const all = thingModelsAdminMock()
    return kw ? all.filter((m) => (m.name + m.modelKey + m.category).toLowerCase().includes(kw)) : all
  }
  const tmOne = u.match(/^\/api\/thing-models\/(\d+)$/)
  if (tmOne) return thingModelAdminOneMock(Number(tmOne[1])) ?? null

  // ---- U 位识别 (RFID 实测 + 电子工单台账多源融合) 离线兜底 ----
  if (u === '/api/servers') {
    const cabinetId = Number(cfg?.params?.cabinetId ?? cfg?.params?.cabinet_id ?? 0) || 1
    const cab = CABINETS.find((c) => c.id === cabinetId)
    const uTotal = (cab?.u_total as number) ?? 42
    return genServersForCabinet(cabinetId, uTotal)
  }
  const upMat = u.match(/^\/api\/cabinets\/(\d+)\/u-position(\/recognize)?$/)
  if (upMat) {
    const cabinetId = Number(upMat[1])
    if (upMat[2]) return recognizeUPositionMock(cabinetId)
    return uPositionMock(cabinetId)
  }

  // ---- 外部设备接入契约 (动态设备 ID) ----
  if (u.startsWith('/api/external/devices')) {
    if (u === '/api/external/devices') return externalDevicesMock(cfg?.params)
    if (u === '/api/external/thing-models') return thingModelsMock()
    // /api/external/devices/{id}/metrics[/(realtime|history)]
    const m = u.match(/^\/api\/external\/devices\/([^/]+)\/metrics(\/(realtime|history))?$/)
    if (m) {
      const deviceId = decodeURIComponent(m[1])
      const sub = m[3] // realtime | history | undefined
      const params = cfg?.params ?? {}
      if (!sub) {
        const limit = Number(params.limit ?? 20)
        return recentMetricsMock(deviceId, limit)
      }
      if (sub === 'realtime') return realtimeMock(deviceId)
      if (sub === 'history') {
        const minutes = computeMinutes(String(params.start ?? ''), String(params.end ?? ''))
        const limit = Number(params.limit ?? 300)
        return historyMock(deviceId, minutes, limit)
      }
    }
  }

  // ---- 告警规则引擎 / 告警历史 ----
  if (u === '/api/alarm-rules') return alarmRulesMock()
  if (u === '/api/alarm-rules/state') return alarmEngineStateMock()
  if (u === '/api/alarm-history') return alarmHistoryMock(cfg?.params as AlarmHistoryQuery | undefined)

  // ---- 机柜 / 统一设备台账 ----
  if (u === '/api/cabinets') return cabinetsMock(cfg?.params)
  let _m = u.match(/^\/api\/cabinets\/(\d+)\/metrics$/)
  if (_m) return cabinetMetricsMock(Number(_m[1]), cfg?.params)
  if (u === '/api/equipment') return equipmentMock(cfg?.params)
  _m = u.match(/^\/api\/equipment\/(\d+)$/)
  if (_m) return equipmentOneMock(Number(_m[1]))
  _m = u.match(/^\/api\/equipment\/(\d+)\/metrics$/)
  if (_m) return equipmentMetricsMock(Number(_m[1]), cfg?.params)

  // ---- v2 演示 / 兜底数据通道 ----
  if (u === '/api/demo/overview') return dashboardOverview()
  if (u === '/api/demo/devices') return demoDevicesMock(cfg?.params)

  return undefined
}
