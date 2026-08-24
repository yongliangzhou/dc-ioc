/**
 * 全局格式化 / 状态着色工具
 *
 * 该模块收口了原本散落在各 .vue 文件中、实现完全一致（或已在此统一）的
 * 数值格式化与状态着色函数，避免跨页面重复定义。
 *
 * 注意：
 * - `barCls` 不在此处收口：NetworkFirewalls 与 CapacityDashboard 两套
 *   返回值（res-/crit-warn-ok）类名体系不同，保留各自局部实现。
 * - ops 模块原 `fmt(s?: string)` 为"字符串时间格式化"，与数值版 `fmt`
 *   同名冲突，此处以 `fmtDateTime` 导出，调用点需相应改名。
 */

/** 数值格式化：null/NaN -> '-'，否则保留 dp 位小数 */
export function fmt(v: number | null | undefined, dp = 2): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Number(v).toFixed(dp)
}

/** 整数格式化（千分位）：null/NaN -> '-' */
export function fmtInt(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return '-'
  return Math.round(v).toLocaleString()
}

/** 大数缩写：K / M。null -> '-' */
export function fmtNum(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '-'
  if (v >= 1_000_000) return (v / 1_000_000).toFixed(1) + 'M'
  if (v >= 1_000) return (v / 1_000).toFixed(1) + 'K'
  return v.toLocaleString()
}

/** 带宽格式化：Kbps / Mbps / Gbps。null -> '-' */
export function fmtBps(bps: number | null | undefined): string {
  if (bps == null) return '-'
  if (bps >= 1e9) return (bps / 1e9).toFixed(2) + ' Gbps'
  if (bps >= 1e6) return (bps / 1e6).toFixed(1) + ' Mbps'
  if (bps >= 1e3) return (bps / 1e3).toFixed(1) + ' Kbps'
  return bps + ' bps'
}

/** 生成最近 n 小时的标签（含分钟），用于时序图 x 轴 */
export function genHours(n: number): string[] {
  const now = new Date()
  const hrs: string[] = []
  for (let i = n - 1; i >= 0; i--) {
    const t = new Date(now.getTime() - i * 3600 * 1000)
    hrs.push(
      t.getHours().toString().padStart(2, '0') + ':' +
      t.getMinutes().toString().padStart(2, '0'),
    )
  }
  return hrs
}

/** 断路器状态着色：合闸->g，分闸->r，检修/备用/热备->b，其他->a */
export function breakerCls(v: string | undefined | null): string {
  const t = String(v ?? '').trim()
  if (t.includes('合闸') || (t.includes('合') && !t.includes('分'))) return 'g'
  if (t.includes('分')) return 'r'
  if (t.includes('检修') || t.includes('备用') || t.includes('热备')) return 'b'
  return 'a'
}

/** 负载率着色 */
export function loadCls(load: number): string {
  if (load >= 90) return 'r-text'
  if (load >= 80) return 'a-text'
  return 'g-text'
}

/** 温度着色：>=alarm 红，>=warn 黄，否则绿 */
export function tempCls(t: number, warn: number, alarm: number): string {
  if (t >= alarm) return 'r-text'
  if (t >= warn) return 'a-text'
  return 'g-text'
}

/** 功率因数着色 */
export function pfCls(pf: number): string {
  if (pf >= 0.95) return 'g-text'
  if (pf >= 0.9) return 'a-text'
  return 'r-text'
}

/** 谐波 THD-U 着色 */
export function thduCls(v: number): string {
  if (v >= 5) return 'r-text'
  if (v >= 3) return 'a-text'
  return 'g-text'
}

/** 利用率着色：>=85 黄，>=60 白，否则绿（修正 Switches 旧实现的恒 a-text bug） */
export function utilCls(v: number): string {
  if (v >= 85) return 'a-text'
  if (v >= 60) return 'w-text'
  return 'g-text'
}

/** HVAC 行状态着色：fault/告警 -> row-danger，standby/待机 -> row-warning，否则空 */
export function statusRow(s: string): string {
  return s === 'fault' || s === '告警'
    ? 'row-danger'
    : s === 'standby' || s === '待机'
      ? 'row-warning'
      : ''
}

/** 保留 1 位小数（HVAC 数值，与 fmt 同义） */
export function numVal(v: number | string | null | undefined): string {
  if (v === '-' || v === undefined || v === null) return '-'
  return String(Math.round(Number(v) * 10) / 10)
}

/** 数值格式化：整数不补小数，否则 1 位（HVAC，与 fmt 同义） */
export function formatVal(v: number | string | null | undefined): string {
  if (v === '-' || v === undefined || v === null) return '-'
  if (typeof v === 'string') return v
  return v % 1 === 0 ? String(v) : v.toFixed(1)
}

/** 时间字符串 -> 本地时间（HH:MM:SS）；非法原样返回 */
export function formatTime(t: string | undefined | null): string {
  if (!t) return '-'
  try {
    const d = new Date(t)
    if (isNaN(d.getTime())) return t
    return d.toLocaleTimeString('zh-CN')
  } catch {
    return t
  }
}

/** ops 模块原 `fmt(s?: string)`：ISO 时间字符串 -> 本地日期时间；空 -> — */
export function fmtDateTime(s?: string): string {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}
