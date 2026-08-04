import { ref, reactive, onBeforeUnmount, type Ref } from 'vue'
import { getDeviceRealtime, getDeviceHistory } from '@/api'
import type {
  MetricRealtimePoint,
  MetricRealtimeResponse,
  MetricHistoryResponse,
  MetricHistoryPoint,
  MetricQuality,
} from '@/types'

/* ===================================================================
 * useTelemetry — 设备遥测统一数据源
 *
 * 提供:
 *   1. WS 实时订阅 (优先) 或 HTTP 轮询 (降级) 的实时测点
 *   2. HTTP 历史趋势查询 (按时间窗自动降采样)
 *   3. 在线/离线状态判定
 *   4. 自动生命周期管理 (onBeforeUnmount 清理)
 *
 * 使用方式:
 *   const { realtime, latest, online, history, subscribe, fetchHistory, connected } = useTelemetry("CH-01", ["supply_temp", "return_temp"]);
 * =================================================================== */

export interface TelemetryMetric {
  value: number
  unit?: string
  quality: MetricQuality
  ts?: string
  /** 历史缓冲区 (最近 N 个实时推送点积累的迷你趋势, 用于 sparkline) */
  spark: { ts: string; value: number }[]
}

export interface TelemetryOptions {
  /** 关注的测点名列表 (不传则拉取全部) */
  metrics?: string[]
  /** HTTP 轮询间隔 ms (WS 不可用时启用, 默认 5000) */
  pollIntervalMs?: number
  /** WS 地址前缀, 默认 VITE_WS_URL 或 ws://localhost:8000 */
  wsBase?: string
  /** spark 历史点数 (默认 60) */
  sparkSize?: number
  /** 数据新鲜度阈值 ms (超过此阈值判定离线, 默认 120000 = 2分钟) */
  staleThresholdMs?: number
  /** 采集器上报周期 s (兜底值, 默认 5; 后端 WS connected 会动态覆盖) */
  reportIntervalS?: number
  /** 单测点 stale 阈值 ms (兜底值, 默认 15000; 后端 WS connected 会动态覆盖) */
  metricStaleMs?: number
}

export function useTelemetry(deviceId: Ref<string> | string, opts: TelemetryOptions = {}) {
  const devId = typeof deviceId === 'string' ? deviceId : deviceId.value

  /* ---- reactive state ---- */
  const realtime = reactive<Record<string, TelemetryMetric>>({})
  const connected = ref(false)
  const online = ref(false)
  const history = ref<MetricHistoryResponse | null>(null)
  const loadingHistory = ref(false)
  const lastUpdate = ref<string | null>(null)

  const _metrics = opts.metrics ?? []
  const _pollMs = opts.pollIntervalMs ?? 5000
  const _sparkSize = opts.sparkSize ?? 60
  const _staleMs = opts.staleThresholdMs ?? 120_000

  // [P1-6] 由后端 WS connected 消息动态采纳的节奏参数 (兜底值保持原行为, 连上后覆盖)
  const reportIntervalS = ref<number>(opts.reportIntervalS ?? 5)
  const metricStaleMs = ref<number>(opts.metricStaleMs ?? 15_000)

  let _ws: WebSocket | null = null
  let _pollTimer = 0
  let _reconnectTimer = 0
  let _destroyed = false

  /* ---- helper: update a metric in the reactive map ---- */
  function _updateMetric(p: MetricRealtimePoint): void {
    const cur = realtime[p.metric_name]
    if (!cur) {
      realtime[p.metric_name] = {
        value: p.value,
        unit: p.unit,
        quality: p.quality,
        ts: new Date().toISOString(),
        spark: [{ ts: new Date().toISOString(), value: p.value }],
      }
    } else {
      cur.value = p.value
      cur.quality = p.quality
      if (p.unit !== undefined) cur.unit = p.unit
      cur.ts = new Date().toISOString()
      const buf = cur.spark
      buf.push({ ts: cur.ts, value: p.value })
      if (buf.length > _sparkSize) buf.splice(0, buf.length - _sparkSize)
    }
  }

  function _checkOnline(): void {
    let last = 0
    for (const k of Object.keys(realtime)) {
      const m = realtime[k]
      if (m.ts) {
        const t = new Date(m.ts).getTime()
        if (t > last) last = t
      }
    }
    online.value = last > 0 && Date.now() - last < _staleMs
  }

  /* ---- WS 连接 ---- */
  function _connectWs(): void {
    if (_destroyed) return
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING))
      return

    // 安全: Token 不再拼进 URL, 改为首条握手消息 {type:"auth", token} 认证
    const base =
      opts.wsBase ?? import.meta.env.VITE_WS_URL ?? `ws://${window.location.hostname}:8000`
    const sock = new WebSocket(`${base}/ws`)

    sock.onopen = () => {
      const token = localStorage.getItem('dc_ioc_token')
      sock.send(JSON.stringify({ type: 'auth', token: token ?? '' }))
    }

    sock.onmessage = (ev: MessageEvent) => {
      try {
        const msg = JSON.parse(ev.data)
        if (msg.type === 'auth_ok') {
          // 认证通过后才订阅当前设备 (后端验签前不接受业务指令)
          connected.value = true
          sock.send(JSON.stringify({ action: 'subscribe', device_id: devId }))
        } else if (msg.type === 'connected') {
          // [P1-6] 后端下发的上报周期 / 单测点 stale 阈值, 动态采纳 (替换前端硬编码)
          if (typeof msg.report_interval_s === 'number' && msg.report_interval_s > 0) {
            reportIntervalS.value = msg.report_interval_s
          }
          if (typeof msg.stale_threshold_ms === 'number' && msg.stale_threshold_ms > 0) {
            metricStaleMs.value = msg.stale_threshold_ms
          }
        } else if (
          msg.type === 'device_metrics' &&
          msg.device_id === devId &&
          Array.isArray(msg.points)
        ) {
          for (const p of msg.points as MetricRealtimePoint[]) {
            _updateMetric(p)
          }
          lastUpdate.value = new Date().toISOString()
          _checkOnline()
        } else if (msg.type === 'subscribed') {
          // 订阅确认
        }
      } catch {
        /* ignore malformed */
      }
    }

    sock.onclose = () => {
      connected.value = false
      _ws = null
      _checkOnline()
      if (!_destroyed) {
        _reconnectTimer = window.setTimeout(_connectWs, 3000)
      }
    }

    sock.onerror = () => {
      sock.close()
    }

    _ws = sock
  }

  /* ---- HTTP 降级轮询 ---- */
  async function _httpPoll(): Promise<void> {
    if (_destroyed || connected.value) return // WS 存活则跳过
    try {
      const res: MetricRealtimeResponse = await getDeviceRealtime(devId)
      if (!res || !res.points) return
      for (const p of res.points) {
        _updateMetric(p)
      }
      lastUpdate.value = res.ts ?? new Date().toISOString()
      online.value = res.online
    } catch {
      /* 后端不可达, 保持旧值 */
    }
    if (!_destroyed && !connected.value) {
      _pollTimer = window.setTimeout(_httpPoll, _pollMs)
    }
  }

  /* ---- 历史查询 ---- */
  async function fetchHistory(
    metrics?: string[],
    timeRange: { start?: string; end?: string; limit?: number } = {},
  ): Promise<MetricHistoryResponse | null> {
    if (_destroyed) return null
    loadingHistory.value = true
    try {
      const mList = metrics ?? _metrics
      const res: MetricHistoryResponse = await getDeviceHistory(devId, {
        metrics: mList.length ? mList.join(',') : undefined,
        start: timeRange.start,
        end: timeRange.end,
        limit: timeRange.limit ?? 500,
      })
      if (_destroyed) return null
      history.value = res
      return res
    } catch {
      return null
    } finally {
      loadingHistory.value = false
    }
  }

  /** 便捷: 最近 N 分钟历史 */
  function fetchRecentHistory(minutes = 30, limit = 300) {
    const end = new Date().toISOString()
    const start = new Date(Date.now() - minutes * 60_000).toISOString()
    return fetchHistory(undefined, { start, end, limit })
  }

  /* ---- 对外订阅 (切换设备) ---- */
  function subscribe(newDeviceId: string): void {
    if (_ws && _ws.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({ action: 'unsubscribe', device_id: devId }))
      _ws.send(JSON.stringify({ action: 'subscribe', device_id: newDeviceId }))
    }
    // 重置实时缓存
    for (const k of Object.keys(realtime)) delete realtime[k]
    // 如果是 Ref, 需要调用者自行更新
  }

  /* ---- API 数据辅助 ---- */
  /** 获取某测点最新值 (方便模板使用) */
  function val(name: string): number | null {
    return realtime[name]?.value ?? null
  }
  /** 获取某测点最近的 spark 序列 (用于迷你趋势图) */
  function spark(name: string): { ts: string; value: number }[] {
    return realtime[name]?.spark ?? []
  }
  /** 获取测点单位 */
  function unitOf(name: string): string {
    return realtime[name]?.unit ?? ''
  }

  /* ---- 生命周期 ---- */
  function _start(): void {
    _connectWs()
    // HTTP 轮询初尝 (WS 连上后自动停止)
    _httpPoll()
  }

  function destroy(): void {
    _destroyed = true
    clearTimeout(_pollTimer)
    clearTimeout(_reconnectTimer)
    if (_ws) {
      _ws.onclose = null
      _ws.onerror = null
      _ws.close()
      _ws = null
    }
    connected.value = false
    online.value = false
    for (const k of Object.keys(realtime)) delete realtime[k]
  }

  onBeforeUnmount(destroy)

  // 立即启动
  _start()

  return {
    // reactive data
    realtime,
    online,
    connected,
    history,
    loadingHistory,
    lastUpdate,
    // [P1-6] 由后端动态下发的节奏参数 (上报周期 / 单测点 stale 阈值)
    reportIntervalS,
    metricStaleMs,
    // actions
    subscribe,
    fetchHistory,
    fetchRecentHistory,
    // helpers
    val,
    spark,
    unitOf,
    // lifecycle
    destroy,
  }
}
