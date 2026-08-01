import { defineStore } from "pinia";
import { getDashboardOverview } from "@/api";
import type { DashboardOverview } from "@/types";

export const useMetricsStore = defineStore("metrics", {
  state: () => ({
    overview: null as DashboardOverview | null,
    timer: 0 as number,
  }),
  actions: {
    async fetchOverview() {
      this.overview = await getDashboardOverview();
    },
    startPolling() {
      this.fetchOverview();
      const interval = Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000);
      this.timer = window.setInterval(this.fetchOverview, interval);
    },
    stopPolling() {
      clearInterval(this.timer);
    },
  },
});
