import { ref, onBeforeUnmount, type Ref } from 'vue'

export interface WsMessage {
  type:
    | 'telemetry'
    | 'alarm'
    | 'device_status'
    | 'connected'
    | 'device_metrics'
    | 'subscribed'
    | 'auth_ok'
    | 'auth_error'
  data?: any
  ts?: string
  client_id?: string
}

export function useWebSocket(onMessage?: (msg: WsMessage) => void) {
  const ws = ref<WebSocket | null>(null)
  const connected = ref(false)
  let reconnectTimer = 0
  let destroyed = false

  function connect() {
    if (destroyed) return
    if (
      ws.value &&
      (ws.value.readyState === WebSocket.OPEN || ws.value.readyState === WebSocket.CONNECTING)
    )
      return

    // 安全: Token 不再拼进 URL (避免泄漏到日志/代理), 改为首条握手消息认证
    const base = import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8000`
    const socket = new WebSocket(`${base}/ws`)

    socket.onopen = () => {
      // 首条握手消息: {type:"auth", token}; 后端验签通过回复 auth_ok 后才视为已连接
      const token = localStorage.getItem('dc_ioc_token')
      socket.send(JSON.stringify({ type: 'auth', token: token ?? '' }))
    }

    socket.onmessage = (event) => {
      try {
        const msg: WsMessage = JSON.parse(event.data)
        if (msg.type === 'auth_ok') {
          connected.value = true
          console.log('[WS] 认证通过, 已连接')
        } else if (msg.type === 'auth_error') {
          console.warn('[WS] 认证失败, 连接将被关闭')
        }
        onMessage?.(msg)
      } catch {}
    }

    socket.onclose = () => {
      connected.value = false
      ws.value = null
      if (!destroyed) {
        reconnectTimer = window.setTimeout(connect, 3000)
      }
    }

    socket.onerror = () => {
      socket.close()
    }

    ws.value = socket
  }

  function disconnect() {
    destroyed = true
    clearTimeout(reconnectTimer)
    ws.value?.close()
    ws.value = null
    connected.value = false
  }

  onBeforeUnmount(disconnect)

  return { ws, connected, connect, disconnect }
}
