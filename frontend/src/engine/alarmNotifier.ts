import { reactive } from 'vue'
import type { Alarm } from '@/types'

/**
 * 告警实时通知引擎（单例）
 * - 弹窗（最高层级，不遮挡）+ 声音（Web Audio 合成）+ 浏览器消息推送
 * - 智能分级 + 场景化根因/排查/修复匹配
 * - 由 realtimeLinkage.tick() 在侦测到新增告警时调用 notifyNew()
 */

// ---------- 场景库：根因分析 / 排查步骤 / 修复方案 ----------
export interface AlarmScenario {
  key: string
  /** 关键词命中（sys 或 desc 包含其一即匹配） */
  keywords: string[]
  rootCause: string
  steps: string[]
  fix: string
  /** 知识库搜索建议词，用于一键跳转 */
  kbQuery: string
}

export const ALARM_SCENARIOS: AlarmScenario[] = [
  {
    key: 'network',
    keywords: ['网络', '丢包', '延迟', 'packet', 'ping', 'link', '链路', '断连', '离线', 'net'],
    rootCause: '网络链路异常：可能是交换机端口故障、物理线路中断、上游路由震荡或防火墙策略导致。',
    steps: [
      '确认告警设备网口状态与指示灯（link/act）',
      '在采集网关 ping 设备 IP，测量丢包率与 RTT',
      '检查上联交换机对应端口错误计数、CRC 错包',
      '核对最近是否变更过 VLAN / 防火墙策略',
    ],
    fix: '复位/更换故障端口或网线；若上联故障联系网络组切换冗余链路；恢复后确认遥测数据回传稳定。',
    kbQuery: '网络故障 丢包 链路中断 排查',
  },
  {
    key: 'cpu',
    keywords: ['cpu', '负载', '过载', 'load', '处理器', '占用率'],
    rootCause: 'CPU 负载过高：可能因突发流量、死循环进程、采集任务堆积或业务高峰导致算力耗尽。',
    steps: [
      '登录主机 / top 查看占用最高的进程',
      '确认是否为采集器或规则引擎进程异常堆积',
      '检查是否有定时任务在同一窗口并发执行',
      '观察 5/15 分钟负载均值判断是否持续高位',
    ],
    fix: '终止异常进程或扩容；优化采集轮询间隔；若为业务高峰则横向扩容并补充监控阈值。',
    kbQuery: 'CPU 过载 负载高 进程 排查',
  },
  {
    key: 'disk',
    keywords: ['磁盘', '存储', '空间', '容量', 'disk', 'storage', 'inode', '满'],
    rootCause: '磁盘空间不足：日志/遥测数据持续写入未清理，或异常进程产生大量临时文件。',
    steps: [
      'df -h 定位占用率最高的挂载点',
      'du -sh * 找出大目录（多为 logs / data）',
      '检查采集落盘与归档策略是否生效',
      '确认是否有 core dump 或异常临时文件',
    ],
    fix: '清理过期日志与冷数据归档；调整滚动日志保留周期；必要时扩容磁盘或挂载新卷。',
    kbQuery: '磁盘空间不足 容量 清理 日志',
  },
  {
    key: 'temp',
    keywords: ['温度', '过热', '制冷', 'temp', '温度高', '空调', 'crac', 'cold'],
    rootCause: '温度/制冷异常：机房空调出力不足、冷通道阻塞、设备散热不良或环境温度越限。',
    steps: [
      '查看机房温湿度曲线与 CRAC 出水/回水温度',
      '确认冷通道是否封堵、出风口是否被遮挡',
      '检查设备风扇转速与进风温度',
      '核对近期负载是否突增导致产热上升',
    ],
    fix: '调整空调设定或开启备用机组；清理风道；若为设备级过热则降载并安排检修。',
    kbQuery: '温度高 制冷不足 空调 机房',
  },
  {
    key: 'power',
    keywords: ['电压', '供电', 'ups', 'power', '掉电', '断电', '过载', '电流', '电池'],
    rootCause: '供电/电气异常：市电波动、UPS 切换、负载电流越限或电池健康度下降。',
    steps: [
      '查看 UPS 输入/输出电压、电池余量与健康度',
      '核对配电柜三相电流是否平衡越限',
      '确认是否为计划性倒闸或外部市电波动',
      '检查 PDU 支路电流与断路器状态',
    ],
    fix: '切换备用回路或启动发电机；均衡三相负载；电池劣化则安排更换并复核供电冗余。',
    kbQuery: '供电异常 UPS 电压 掉电 排查',
  },
  {
    key: 'water',
    keywords: ['漏水', '水位', '渗水', 'water', 'leak', '浸水', '液位'],
    rootCause: '水患风险：管道渗漏、冷凝水积聚或防汛措施失效导致机房进水。',
    steps: [
      '现场确认漏水点与传感器位置是否一致',
      '关闭相关进水阀并排查管道接口',
      '检查冷凝水排水是否通畅',
      '评估对下方设备的浸水风险并隔离',
    ],
    fix: '封堵漏点、排水并烘干；启用防汛挡水板；受损设备断电检修后再上电。',
    kbQuery: '漏水 水患 防汛 机房 处理',
  },
]

const GENERIC: AlarmScenario = {
  key: 'generic',
  keywords: [],
  rootCause: '未能自动匹配具体场景，需结合设备类型与指标进一步定位。',
  steps: [
    '确认告警指标当前实测值与阈值',
    '查看该设备/系统近期趋势与关联告警',
    '核对是否近期有变更或重启操作',
    '必要时联系对应系统负责人现场核实',
  ],
  fix: '定位异常根因后按对应预案处置，并补充处理记录沉淀经验。',
  kbQuery: '',
}

export function matchScenario(a: Alarm): AlarmScenario {
  const text = `${a.system} ${a.message}`.toLowerCase()
  for (const s of ALARM_SCENARIOS) {
    if (s.keywords.some((k) => text.includes(k.toLowerCase()))) return s
  }
  return GENERIC
}

// ---------- 通知状态 ----------
export interface AlarmNotificationItem {
  id: string
  alarmId: string
  alarm: Alarm
  scenario: AlarmScenario
  ts: number
  read: boolean
}

const state = reactive<{
  items: AlarmNotificationItem[]
  soundOn: boolean
  notifyOn: boolean
}>({ items: [], soundOn: true, notifyOn: true })

let seq = 0
let audioCtx: AudioContext | null = null

function fingerprint(a: Alarm): string {
  // Alarm 无 id，用 system+message+time 组合；time 可能为空则用序号兜底
  return `${a.system}|${a.message}|${a.time ?? ''}`
}

/** 申请浏览器通知权限 */
export function requestNotificationPermission() {
  if (!('Notification' in window)) return
  if (Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {})
  }
}

/** Web Audio 合成告警音：crit 三连高音，warn 单声中音 */
function beep(level: Alarm['level']) {
  if (!state.soundOn) return
  try {
    const Ctx = (window.AudioContext ||
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext) as typeof AudioContext
    if (!Ctx) return
    if (!audioCtx) audioCtx = new Ctx()
    if (audioCtx.state === 'suspended') audioCtx.resume()
    const now = audioCtx.currentTime
    const freq = level === 'crit' ? 880 : 560
    const bursts = level === 'crit' ? 3 : 1
    for (let i = 0; i < bursts; i++) {
      const t = now + i * 0.28
      const osc = audioCtx.createOscillator()
      const gain = audioCtx.createGain()
      osc.type = 'square'
      osc.frequency.value = freq
      gain.gain.setValueAtTime(0.0001, t)
      gain.gain.exponentialRampToValueAtTime(0.18, t + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.2)
      osc.connect(gain).connect(audioCtx.destination)
      osc.start(t)
      osc.stop(t + 0.22)
    }
  } catch {
    /* 音频不可用则静默 */
  }
}

function pushBrowserNotification(item: AlarmNotificationItem) {
  if (!state.notifyOn) return
  if (!('Notification' in window) || Notification.permission !== 'granted') return
  try {
    const n = new Notification(`[${item.alarm.level.toUpperCase()}] ${item.alarm.system} 告警`, {
      body: item.alarm.message,
      tag: item.id,
      requireInteraction: item.alarm.level === 'crit',
    })
    n.onclick = () => {
      window.focus()
      window.location.hash = '#/ops/alarms'
      n.close()
    }
  } catch {
    /* 通知不可用则忽略 */
  }
}

/** 由 realtimeLinkage 在检测到新增告警时调用 */
export function notifyNew(alarm: Alarm, force = false) {
  const id = `an_${++seq}`
  // alarm 实际为后端 RtAlarm（含 id 字段），类型层面 Alarm 无 id，故用指纹兜底
  const alarmId = (alarm as { id?: string }).id ?? fingerprint(alarm)
  const item: AlarmNotificationItem = {
    id,
    alarmId,
    alarm,
    scenario: matchScenario(alarm),
    ts: Date.now(),
    read: false,
  }
  state.items.unshift(item)
  if (state.items.length > 8) state.items.pop()

  // 智能分级：crit 强制弹窗 + 声音 + 推送；warn 弹窗 + 声音；info 仅角标
  if (alarm.level === 'crit' || force) {
    beep('crit')
    pushBrowserNotification(item)
  } else if (alarm.level === 'warn') {
    beep('warn')
    pushBrowserNotification(item)
  }
  // info 级不弹窗、不发声，仅进入通知列表
}

export function useAlarmNotifier() {
  return {
    items: state.items,
    soundOn: state.soundOn,
    notifyOn: state.notifyOn,
    setSound: (v: boolean) => (state.soundOn = v),
    setNotify: (v: boolean) => (state.notifyOn = v),
    dismiss: (id: string) => {
      const i = state.items.findIndex((x) => x.id === id)
      if (i >= 0) state.items.splice(i, 1)
    },
    clear: () => (state.items.length = 0),
    markRead: (id: string) => {
      const it = state.items.find((x) => x.id === id)
      if (it) it.read = true
    },
    unreadCount: () => state.items.filter((x) => !x.read).length,
  }
}
