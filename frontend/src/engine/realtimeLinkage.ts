/**
 * 实时越限联动引擎 — 前端纯展示 + 启停 (v2)
 *
 * 规则配置与阈值评估已统一迁移至后端 (backend/app/services/alarm_engine.py):
 * - 规则列表:   GET  /api/alarm-rules          (后端 DEFAULT_RULES 展开)
 * - 活动告警:   GET  /api/alarm-rules/active   (后端评估外部设备遥测产生)
 * - 规则启停:   PATCH /api/alarm-rules/{id}/status  (admin/operator)
 * - 确认/关单:  POST /api/alarm-rules/active/{id}/ack | /resolve
 *
 * 本模块不再在浏览器内执行阈值评估 (原 evaluateRule + realtimeAllMock 已移除),
 * 仅周期轮询后端活动告警并提供 启停/确认/关单 操作代理, 保持原有响应式接口
 * (rules / active / running / start / stop / ack / resolve / toggleRule) 不变,
 * 告警中心等消费方无需感知迁移。
 */
import { reactive } from 'vue'
import type { Alarm, AlarmRuleDef } from '@/types'
import {
  getAlarmRules,
  getActiveAlarms,
  ackActiveAlarm,
  resolveActiveAlarm,
  toggleAlarmRule,
} from '@/api'
import { notifyNew } from '@/engine/alarmNotifier'

/** 联动产生的活动告警 (在 Alarm 基础上附加定位字段) */
export interface RtAlarm extends Alarm {
  id: string
  ruleId: string
  deviceId: string
  metric: string
  value: number
  threshold: number
  unit?: string
  rt: true
}

/** 联动规则 = 规则定义 (由后端下发, 类型与 AlarmRuleDef 一致) */
type LinkRule = AlarmRuleDef

function toClock(iso: string): string {
  try {
    const d = new Date(iso)
    const p = (n: number) => String(n).padStart(2, '0')
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`
  } catch {
    return iso
  }
}

// 后端活动告警原始形状 (动态 JSON, 字段以 unknown 呈现)
type RawAlarm = Record<string, unknown>

/** 后端活动告警 -> 前端 RtAlarm 形状映射 */
function mapAlarm(a: RawAlarm): RtAlarm {
  return {
    id: String(a.id ?? `${a.device_id}:${a.metric_name}:${a.level}`),
    ruleId: `${a.category}:${a.metric_name}`,
    deviceId: String(a.device_id ?? ''),
    metric: String(a.metric_name ?? ''),
    value: Number(a.value ?? 0),
    threshold: Number(a.threshold ?? 0),
    unit: String(a.unit ?? ''),
    lv: (a.level === 'crit' ? 'crit' : a.level === 'warn' ? 'warn' : 'info') as Alarm['lv'],
    sys: String(a.system ?? '其他'),
    desc: String(a.desc ?? ''),
    state: String(a.state ?? '待确认'),
    ts: toClock(String(a.ts ?? new Date().toISOString())),
    owner: String(a.owner || '—'),
    rt: true,
  }
}

class RealtimeLinkage {
  rules: LinkRule[] = []
  active: RtAlarm[] = []
  running = false

  private timer = 0
  private rulesLoaded = false
  private initialized = false

  /** 启动全局引擎 (幂等) — 仅启动轮询, 评估在后端 */
  start(intervalMs = 5000) {
    if (this.running) return
    this.running = true
    this.initialized = false
    void this.refreshRules()
    void this.tick()
    // 轮询间隔下限 3s, 避免高频打后端
    this.timer = window.setInterval(() => void this.tick(), Math.max(3000, intervalMs))
  }

  stop() {
    this.running = false
    if (this.timer) clearInterval(this.timer)
    this.timer = 0
  }

  /** 拉取后端规则配置 (启停状态以后端为准) */
  async refreshRules() {
    try {
      const rules = await getAlarmRules()
      if (Array.isArray(rules)) {
        this.rules = rules as LinkRule[]
        this.rulesLoaded = true
      }
    } catch {
      /* 后端不可达: 保持现有列表 (可能为空), 不做本地评估降级 */
    }
  }

  /** 轮询后端活动联动告警 (纯展示) */
  private async tick() {
    try {
      const res = await getActiveAlarms()
      const list = Array.isArray(res?.items) ? res.items : []
      const mapped = list.map((a) => mapAlarm(a as unknown as RawAlarm))
      const acked = new Set(this.active.filter((a) => a.state === '已确认').map((a) => a.id))
      const next = mapped.map((a) =>
        acked.has(a.id) && a.state === '待确认' ? { ...a, state: '已确认' } : a,
      )

      // 检测新增告警 -> 实时通知（首轮快照不弹窗，避免存量轰炸）
      if (this.initialized) {
        const prevIds = new Set(this.active.map((a) => a.id))
        for (const a of next) {
          if (!prevIds.has(a.id)) notifyNew(a)
        }
      } else {
        this.initialized = true
      }

      this.active = next
      if (!this.rulesLoaded) void this.refreshRules()
    } catch {
      /* 后端不可达: 保持上次快照 */
    }
  }

  /** 确认联动告警 (乐观更新 + 后端同步) */
  ack(id: string) {
    const a = this.active.find((x) => x.id === id)
    if (a) a.state = '已确认'
    void ackActiveAlarm(id).catch(() => {})
  }

  /** 关单: 本地移除 + 后端同步 */
  resolve(id: string) {
    this.active = this.active.filter((x) => x.id !== id)
    void resolveActiveAlarm(id).catch(() => {})
  }

  /** 启停联动规则 (乐观翻转 + 后端同步, 失败回滚) */
  toggleRule(id: string) {
    const r = this.rules.find((x) => String(x.id) === id)
    if (!r) return
    const prev = r.status
    const next = prev === 'enabled' ? ('silenced' as const) : ('enabled' as const)
    r.status = next
    r.updated = new Date().toISOString().slice(0, 16)
    toggleAlarmRule(id, next).catch(() => {
      r.status = prev // 后端拒绝 (如权限不足) 时回滚
    })
  }
}

/** 单例: 响应式代理, 供告警中心等视图直接消费 */
export const realtimeLinkage = reactive(new RealtimeLinkage())
