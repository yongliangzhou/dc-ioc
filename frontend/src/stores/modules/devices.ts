import { defineStore } from 'pinia'
import { getExternalDevices } from '@/api'
import type { ExternalDeviceView, MetricRecordView } from '@/types'

// 设备实时状态: 在后端设备视图基础上附加本地推送时间戳
type DeviceStatusView = ExternalDeviceView & { ts: number }

/** 设备 store: 设备台账 + 实时状态, WS 设备状态/测点推送自动并入。 */
export const useDevicesStore = defineStore('devices', {
  state: () => ({
    list: [] as ExternalDeviceView[],
    statusMap: {} as Record<string, DeviceStatusView>,
    metricsMap: {} as Record<string, MetricRecordView[]>,
    loading: false,
    wsConnected: false,
  }),
  getters: {
    onlineCount: (s) => Object.values(s.statusMap).filter((v: DeviceStatusView) => v?.online).length,
    total: (s) => s.list.length,
  },
  actions: {
    async fetchDevices(params: Record<string, unknown> = {}) {
      const res = await getExternalDevices(params)
      this.list = res?.items ?? []
    },
    /** WS device_status 推送 */
    applyStatus(status: Partial<ExternalDeviceView> & { id?: string }) {
      if (!status) return
      const id = status.device_id || status.id
      if (!id) return
      this.statusMap[id] = { ...(this.statusMap[id] ?? ({} as DeviceStatusView)), ...status, ts: Date.now() } as DeviceStatusView
    },
    /** WS device_metrics 推送 (实时测点) */
    applyMetrics(deviceId: string, points: MetricRecordView[]) {
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
