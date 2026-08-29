import type { Alarm } from '@/types'

/** 状态/级别 -> 设计系统样式类 的通用映射, 供各业务域视图复用。 */

const GREEN = [
  '运行',
  '投入',
  '正常',
  '合闸',
  '浮充',
  '在线',
  '闭环',
  '通过',
  '就绪',
  '已编排',
  '正常',
]
const BLUE = ['待机', '分闸', '备用', '撤防', '常用侧']
const AMBER = ['检修', '预警', '调节', '临期', '轻微', '注意', '已规划', '观察中']
const RED = ['故障', '报警', '逾期', '异常', '告警', '维保']

/** 状态点 (dot) 颜色类: g/a/r/b/o */
export function dotClass(s: string): string {
  if (GREEN.includes(s)) return 'g'
  if (BLUE.includes(s)) return 'b'
  if (AMBER.includes(s)) return 'a'
  if (RED.includes(s)) return 'r'
  return 'o'
}

/** 标签 (tag) 颜色类: g/a/r/b */
export function tagClass(s: string): string {
  if (GREEN.includes(s)) return 'g'
  if (AMBER.includes(s)) return 'a'
  if (RED.includes(s)) return 'r'
  if (BLUE.includes(s)) return 'b'
  return 'o'
}

/** 告警级别 -> 颜色类 */
export function lvClass(lv: string): string {
  return lv === 'crit' ? 'r' : lv === 'warn' ? 'a' : 'b'
}

/** 告警级别 -> 中文 */
export function lvText(lv: string | undefined): string {
  return lv === 'crit' ? '紧急' : lv === 'warn' ? '重要' : '提示'
}

/** 百分比 -> 进度条颜色 (默认 绿/青) */
export function pctColor(v: number, warn = 70, alarm = 85): string {
  return v > alarm ? 'var(--red)' : v > warn ? 'var(--amber)' : 'var(--cyan)'
}

/** 告警状态 -> 中文 */
export function alarmStateText(s: string | undefined): string {
  return s === 'active'
    ? '活跃'
    : s === 'acknowledged'
      ? '已确认'
      : s === 'resolved'
        ? '已解决'
        : '已抑制'
}

interface RtAlarmLike extends Alarm {
  rt?: boolean
  id?: string
}

/**
 * 告警行的稳定标识，用于复选/批量操作。
 * - 实时联动告警 (rt=true) 用后端 id
 * - 其余用内容指纹，避免依赖数组下标（列表排序/轮询刷新后下标会漂移）
 */
export function alarmKeyOf(a: Alarm): string {
  const rt = a as RtAlarmLike
  if (rt.rt && rt.id) return `rt:${rt.id}`
  return `evt:${a.system ?? ''}|${a.message ?? ''}|${a.time ?? ''}`
}
