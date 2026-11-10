/** @dc-ioc/ui — 状态语义映射（唯一实现，供 StatusBadge 与单测共用） */
export interface StatusDef {
  /** 完整的 CSS 类名，已含 dui- 前缀；调用方不得再拼前缀 */
  cls: string
  text: string
}

export const STATUS_MAP: Record<string, StatusDef> = {
  online: { cls: 'dui-g', text: '在线' },
  running: { cls: 'dui-g', text: '运行' },
  normal: { cls: 'dui-g', text: '正常' },
  standby: { cls: 'dui-a', text: '待机' },
  warning: { cls: 'dui-a', text: '告警' },
  fault: { cls: 'dui-r', text: '故障' },
  error: { cls: 'dui-r', text: '异常' },
  offline: { cls: 'dui-o', text: '离线' },
  stopped: { cls: 'dui-o', text: '停机' },
  maintenance: { cls: 'dui-b', text: '检修' },
  closing: { cls: 'dui-b', text: '合闸' },
  opening: { cls: 'dui-o', text: '分闸' },
}

export const DEFAULT_STATUS_CLASS = 'dui-o'

/** 返回完整类名（不再由调用方拼接 'dui-' 前缀，避免 dui-dui-g 双前缀） */
export function statusClassOf(status: string | null | undefined): string {
  const s = (status || '').toLowerCase()
  return STATUS_MAP[s]?.cls ?? DEFAULT_STATUS_CLASS
}

/** 返回默认中文文案；未知状态原样回显，空值回显 '-' */
export function statusLabelOf(status: string | null | undefined): string {
  const s = (status || '').toLowerCase()
  return STATUS_MAP[s]?.text || status || '-'
}
