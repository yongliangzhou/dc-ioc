import { defineStore } from "pinia";
import { getDashboardOverview } from "@/api";

/** 遥测 store: 持有驾驶舱 KPI 快照, WS 广播 (pue/wue/负载等) 实时并入。 */
export const useTelemetryStore = defineStore("telemetry", {
  state: () => ({
    /** 最近一次 KPI 快照 (来源: WS 广播 或 HTTP 初始拉取) */
    snapshot: null as Record<string, any> | null,
    connected: false,
    lastUpdate: 0 as number,
  }),
  getters: {
    pue: (s) => s.snapshot?.pue ?? 0,
    wue: (s) => s.snapshot?.wue ?? 0,
    itLoadMw: (s) => s.snapshot?.it_load_mw ?? 0,
    totalLoadMw: (s) => s.snapshot?.total_load_mw ?? 0,
    onlineRate: (s) => s.snapshot?.online_rate ?? 0,
    todayAlarms: (s) => s.snapshot?.today_alarms ?? 0,
  },
  actions: {
    /** WS telemetry 广播推送 */
    applySnapshot(data: Record<string, any>) {
      if (!data) return;
      this.snapshot = { ...(this.snapshot || {}), ...data };
      this.lastUpdate = Date.now();
    },
    /** HTTP 初始种子 (WS 未连通前) */
    async fetchInitial() {
      try {
        const ov = await getDashboardOverview();
        if (ov) this.snapshot = { ...(this.snapshot || {}), ...(ov as Record<string, any>) };
      } catch {
        /* 后端不可达时静默 */
      }
    },
    setConnected(v: boolean) {
      this.connected = v;
    },
  },
});
