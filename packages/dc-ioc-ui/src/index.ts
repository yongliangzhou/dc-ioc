// @dc-ioc/ui — DC IOC Platform shared UI components
// v0.1.0

export { default as StatusBadge } from './StatusBadge.vue'
export { default as AlarmBadge } from './AlarmBadge.vue'
export { default as KpiCard } from './KpiCard.vue'

// 状态语义映射（纯函数，便于单测与跨端复用）
export { STATUS_MAP, statusClassOf, statusLabelOf, DEFAULT_STATUS_CLASS } from './statusMap'
export type { StatusDef } from './statusMap'

// Component types
export type { default as StatusBadgeComponent } from './StatusBadge.vue'
export type { default as AlarmBadgeComponent } from './AlarmBadge.vue'
export type { default as KpiCardComponent } from './KpiCard.vue'
