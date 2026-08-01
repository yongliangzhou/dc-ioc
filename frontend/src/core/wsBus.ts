/**
 * 全局实时总线 (单例)。
 *
 * 之前各组件各自 new WebSocket; 现统一为一条连接:
 *   1. 连接后发送首条握手消息 {type:"auth", token} (安全: token 不再走 URL)
 *   2. 收到 auth_ok 后开始分发业务消息
 *   3. 将 telemetry / alarm / device_status / device_metrics 分派到对应 Pinia store
 *
 * 在 App.vue 中 initRealtimeBus() 启动, 组件改为从 store 读取实时数据。
 */
import { useTelemetryStore } from "@/stores/modules/telemetry";
import { useAlarmsStore } from "@/stores/modules/alarms";
import { useDevicesStore } from "@/stores/modules/devices";

let socket: WebSocket | null = null;
let reconnectTimer: number | null = null;
let destroyed = false;
let started = false;

function buildUrl(): string {
  const base = import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000`;
  return `${base}/ws`;
}

function dispatch(raw: string) {
  let msg: any;
  try {
    msg = JSON.parse(raw);
  } catch {
    return;
  }
  const telemetry = useTelemetryStore();
  const alarms = useAlarmsStore();
  const devices = useDevicesStore();

  switch (msg.type) {
    case "auth_ok":
      telemetry.setConnected(true);
      alarms.setWsConnected(true);
      devices.setWsConnected(true);
      break;
    case "auth_error":
      telemetry.setConnected(false);
      break;
    case "telemetry":
      telemetry.applySnapshot(msg.data);
      break;
    case "alarm":
      alarms.ingestRealtime(msg.data);
      break;
    case "device_status":
      devices.applyStatus(msg.data);
      break;
    case "device_metrics":
      if (msg.device_id && Array.isArray(msg.points)) {
        devices.applyMetrics(msg.device_id, msg.points);
      }
      break;
    default:
      break;
  }
}

function connect() {
  if (destroyed || started) return;
  started = true;
  const sock = new WebSocket(buildUrl());

  sock.onopen = () => {
    const token = localStorage.getItem("dc_ioc_token") ?? "";
    sock.send(JSON.stringify({ type: "auth", token }));
  };

  sock.onmessage = (ev) => dispatch(ev.data);

  sock.onclose = () => {
    useTelemetryStore().setConnected(false);
    if (destroyed) return;
    // 退避重连 (3s)
    reconnectTimer = window.setTimeout(() => {
      started = false;
      reconnectTimer = null;
      connect();
    }, 3000);
  };

  sock.onerror = () => sock.close();

  socket = sock;
}

export function initRealtimeBus() {
  destroyed = false;
  connect();
}

export function closeRealtimeBus() {
  destroyed = true;
  started = false;
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  if (socket) {
    socket.close();
    socket = null;
  }
}
