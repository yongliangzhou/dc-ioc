import { defineStore } from "pinia";
import { ref, computed } from "vue";
import {
  getTickets,
  createTicket,
  updateTicket,
  transitionTicket,
  deleteTicket,
  createTicketFromAlarm,
} from "@/api";
import type {
  Ticket,
  TicketStatus,
  TicketCreateRequest,
  TicketUpdateRequest,
  TicketTransitionRequest,
  Alarm,
} from "@/types";
import { TICKET_STATUS_ORDER } from "@/types";

/**
 * 工单中心 Store (2.2 后端化)
 * 全部读写经 /api/ops/tickets 真实后端; 离线时退回空列表, 不污染真实数据。
 */
export const useTicketsStore = defineStore("tickets", () => {
  const tickets = ref<Ticket[]>([]);
  const loading = ref(false);
  const lastError = ref<string | null>(null);

  const stats = computed(() => ({
    open: tickets.value.filter((t) => t.state === "open").length,
    doing: tickets.value.filter((t) => t.state === "doing").length,
    pending: tickets.value.filter((t) => t.state === "pending").length,
    done: tickets.value.filter((t) => t.state === "done").length,
  }));

  const byState = (s: TicketStatus) => tickets.value.filter((t) => t.state === s);
  const getById = (id: string) => tickets.value.find((t) => t.id === id);

  /** 从后端加载工单中心 */
  async function load(): Promise<void> {
    loading.value = true;
    lastError.value = null;
    try {
      const res = await getTickets();
      tickets.value = res.list ?? [];
    } catch (e) {
      lastError.value = e instanceof Error ? e.message : String(e);
      tickets.value = [];
    } finally {
      loading.value = false;
    }
  }

  async function create(req: TicketCreateRequest): Promise<Ticket> {
    const t = await createTicket(req);
    tickets.value.unshift(t);
    return t;
  }

  async function update(id: string, patch: TicketUpdateRequest): Promise<void> {
    const t = await updateTicket(id, patch);
    const i = tickets.value.findIndex((x) => x.id === id);
    if (i >= 0) tickets.value[i] = t;
  }

  async function transition(id: string, req: TicketTransitionRequest): Promise<void> {
    const t = await transitionTicket(id, req);
    const i = tickets.value.findIndex((x) => x.id === id);
    if (i >= 0) tickets.value[i] = t;
  }

  async function advance(id: string, operator = "运维人员"): Promise<void> {
    const t = tickets.value.find((x) => x.id === id);
    if (!t || t.state === "done") return;
    const idx = TICKET_STATUS_ORDER.indexOf(t.state);
    const next = TICKET_STATUS_ORDER[idx + 1];
    if (next) await transition(id, { state: next, operator });
  }

  async function remove(id: string): Promise<void> {
    await deleteTicket(id);
    tickets.value = tickets.value.filter((x) => x.id !== id);
  }

  /** 告警转工单: 优先调用 /from-alarm/{id}, 否则以 source=alarm 直接创建真实工单 */
  async function createFromAlarm(alarm: Alarm): Promise<Ticket> {
    const req: TicketCreateRequest = {
      title: `[告警转工单] ${alarm.desc}`,
      sys: alarm.sys,
      lv: alarm.lv,
      owner: alarm.owner ?? "待分配",
      sla: alarm.lv === "crit" ? "1h" : alarm.lv === "warn" ? "4h" : "8h",
      description: `来源告警系统: ${alarm.sys}\n告警内容: ${alarm.desc}\n触发时间: ${alarm.ts ?? "—"}\n原始状态: ${alarm.state}`,
      source: "alarm",
      sourceAlarmId: (alarm as any).id,
    };
    const alarmId = (alarm as any).id;
    if (alarmId) {
      const t = await createTicketFromAlarm(alarmId, req);
      tickets.value.unshift(t);
      return t;
    }
    return create(req);
  }

  function reset() {
    return load();
  }

  // 初次加载 (2.2 后端化)
  void load();

  return {
    tickets,
    stats,
    loading,
    lastError,
    byState,
    getById,
    load,
    create,
    update,
    transition,
    advance,
    remove,
    createFromAlarm,
    reset,
  };
});
