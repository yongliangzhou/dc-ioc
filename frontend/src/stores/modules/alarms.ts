import { defineStore } from 'pinia'
import {
  getActiveAlarms,
  ackActiveAlarm,
  resolveActiveAlarm,
  getAlarmRules,
  toggleAlarmRule,
} from '@/api'
import type { AlarmRuleDef, AlarmEvent, Alarm, AlarmEngineState } from '@/types'

/** 后端告警摘要 -> 告警事件模型映射 */
function toAlarmEvent(a: Alarm): AlarmEvent {
  return {
    id: a.id ?? `${a.system}:${a.time}:${a.message}`.slice(0, 64),
    ruleId: '',
    ruleName: a.system,
    metric: a.system,
    level: a.level,
    system: a.system,
    message: a.message,
    value: 0,
    threshold: 0,
    unit: undefined,
    status: a.status as AlarmEvent['status'],
    triggeredAt: a.created_at ?? a.time ?? new Date().toISOString(),
    autoResolved: false,
    escalationCount: 0,
    source: a.source,
    domain: a.domain,
    title: a.title,
    time: a.time,
    created_at: a.created_at,
    owner: a.owner,
  }
}

/** 告警中心 store: 持有活动告警 / 规则 / 引擎状态, WS 实时推送自动并入。 */
export const useAlarmsStore = defineStore('alarms', {
  state: () => ({
    activeAlarms: [] as AlarmEvent[],
    rules: [] as AlarmRuleDef[],
    engineState: null as AlarmEngineState | null,
    loading: false,
    wsConnected: false,
  }),
  getters: {
    enabledCount: (s) => s.rules.filter((r: AlarmRuleDef) => r.status === 'enabled').length,
    activeCount: (s) => s.activeAlarms.length,
  },
  actions: {
    async fetchActive() {
      const res = await getActiveAlarms()
      this.activeAlarms = (res?.items ?? []).map(toAlarmEvent)
    },
    async fetchRules() {
      this.rules = (await getAlarmRules()) ?? []
    },
    /** 引擎状态由本地规则列表计算 (后端无 /state 端点, 与 AlarmRules 页一致) */
    async fetchEngineState() {
      await this.fetchRules()
      this.engineState = {
        totalRules: this.rules.length,
        enabledCount: this.rules.filter(
          (r: AlarmRuleDef) => r.status === 'enabled' || r.enabled,
        ).length,
        triggeredCount: 0,
        silencedCount: this.rules.filter((r: AlarmRuleDef) => r.status === 'silenced').length,
      }
    },
    /** WS 实时告警并入 (去重 by id) */
    ingestRealtime(alarm: AlarmEvent | null) {
      if (!alarm) return
      const id = alarm.id
      if (!id) {
        this.activeAlarms.unshift(alarm)
        return
      }
      const idx = this.activeAlarms.findIndex((a) => a.id === id)
      if (idx >= 0) this.activeAlarms[idx] = { ...this.activeAlarms[idx], ...alarm }
      else this.activeAlarms.unshift(alarm)
    },
    async ack(id: string) {
      const prev = this.activeAlarms.find((a) => a.id === id)
      if (prev) prev.status = 'acknowledged'
      try {
        await ackActiveAlarm(id)
      } catch (e) {
        if (prev) prev.status = 'active'
        throw e
      }
    },
    async resolve(id: string) {
      const before = [...this.activeAlarms]
      this.activeAlarms = this.activeAlarms.filter((a) => a.id !== id) // 乐观移除
      try {
        await resolveActiveAlarm(id)
      } catch (e) {
        this.activeAlarms = before // 回滚
        throw e
      }
    },
    async toggleRule(id: string | number, status: 'enabled' | 'silenced') {
      const prev = this.rules.find((r) => String(r.id) === String(id))?.status
      const target = this.rules.find((r) => String(r.id) === String(id))
      if (target) target.status = status // 乐观
      try {
        const updated = await toggleAlarmRule(id, status)
        const idx = this.rules.findIndex((r) => String(r.id) === String(id))
        if (idx >= 0 && updated) this.rules[idx] = updated
      } catch (e) {
        if (target && prev) target.status = prev // 回滚
        throw e
      }
    },
    setWsConnected(v: boolean) {
      this.wsConnected = v
    },
  },
})
