import { defineStore } from 'pinia'
import { getExternalDevices } from '@/api'

/** 设备 store: 设备台账 + 实时状态, WS 设备状态/测点推送自动并入。 */
export const useDevicesStore = defineStore('devices', {
  state: () => ({
    list: [] as any[],
    statusMap: {} as Record<string, any>,
    metricsMap: {} as Record<string, any[]>,
    loading: false,
    wsConnected: false,
  }),
  getters: {
    onlineCount: (s) => Object.values(s.statusMap).filter((v: any) => v?.online).length,
    total: (s) => s.list.length,
  },
  actions: {
    async fetchDevices(params: Record<string, any> = {}) {
      const res = await getExternalDevices(params)
      this.list = res?.items ?? res ?? []
    },
    /** WS device_status 推送 */
    applyStatus(status: any) {
      if (!status) return
      const id = status.device_id || status.id
      if (!id) return
      this.statusMap[id] = { ...(this.statusMap[id] || {}), ...status, ts: Date.now() }
    },
    /** WS device_metrics 推送 (实时测点) */
    applyMetrics(deviceId: string, points: any[]) {
      if (!deviceId || !Array.isArray(points)) return
      this.metricsMap[deviceId] = points
      const st = this.statusMap[deviceId]
      if (st) st.online = true
    },
    setWsConnected(v: boolean) {
      this.wsConnected = v
    },
  },
})
