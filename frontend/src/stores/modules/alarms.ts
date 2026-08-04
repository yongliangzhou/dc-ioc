import { defineStore } from 'pinia'
import {
  getActiveAlarms,
  ackActiveAlarm,
  resolveActiveAlarm,
  getAlarmRules,
  toggleAlarmRule,
} from '@/api'

/** 告警中心 store: 持有活动告警 / 规则 / 引擎状态, WS 实时推送自动并入。 */
export const useAlarmsStore = defineStore('alarms', {
  state: () => ({
    activeAlarms: [] as any[],
    rules: [] as any[],
    engineState: null as any,
    loading: false,
    wsConnected: false,
  }),
  getters: {
    enabledCount: (s) => s.rules.filter((r: any) => r.status === 'enabled').length,
    activeCount: (s) => s.activeAlarms.length,
  },
  actions: {
    async fetchActive() {
      const res = await getActiveAlarms()
      this.activeAlarms = res?.items ?? []
    },
    async fetchRules() {
      this.rules = (await getAlarmRules()) ?? []
    },
    /** 引擎状态由本地规则列表计算 (后端无 /state 端点, 与 AlarmRules 页一致) */
    async fetchEngineState() {
      await this.fetchRules()
      this.engineState = {
        totalRules: this.rules.length,
        enabledCount: this.rules.filter((r: any) => r.status === 'enabled' || r.enabled).length,
        triggeredCount: 0,
        silencedCount: this.rules.filter((r: any) => r.status === 'silenced').length,
      }
    },
    /** WS 实时告警并入 (去重 by id) */
    ingestRealtime(alarm: any) {
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
      if (prev) prev.state = '已确认' // 乐观更新
      try {
        await ackActiveAlarm(id)
      } catch (e) {
        if (prev) prev.state = '待确认' // 回滚
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
