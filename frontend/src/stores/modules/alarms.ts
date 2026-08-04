import { defineStore } from 'pinia'
import {
  getActiveAlarms,
  ackActiveAlarm,
  resolveActiveAlarm,
  getAlarmRules,
  toggleAlarmRule,
} from '@/api'
import type { AlarmRuleDef, AlarmEvent, Alarm, AlarmEngineState } from '@/types'

/** 后端告警摘要 (Alarm) 与生命周期事件 (AlarmEvent) 字段差异较大,
 *  这里把摘要归一化为事件模型以复用 store 统一处理逻辑 */
function toAlarmEvent(a: Alarm): AlarmEvent {
  return {
    id: a.ts != null ? String(a.ts) : a.sys,
    ruleId: '',
    ruleName: a.sys,
    metric: a.sys,
    sys: a.sys,
    lv: a.lv,
    desc: a.desc,
    value: 0,
    threshold: 0,
    unit: undefined,
    state: (a.state ?? 'active') as AlarmEvent['state'],
    triggeredAt: a.ts ?? new Date().toISOString(),
    autoResolved: false,
    escalationCount: 0,
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
      if (prev) prev.state = '已确认' as unknown as AlarmEvent['state'] // 乐观更新
      try {
        await ackActiveAlarm(id)
      } catch (e) {
        if (prev) prev.state = '待确认' as unknown as AlarmEvent['state'] // 回滚
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
    async toggleRule(id: string, status: 'enabled' | 'silenced') {
      const prev = this.rules.find((r) => r.id === id)?.status
      const target = this.rules.find((r) => r.id === id)
      if (target) target.status = status // 乐观
      try {
        const updated = await toggleAlarmRule(id, status)
        const idx = this.rules.findIndex((r) => r.id === id)
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
