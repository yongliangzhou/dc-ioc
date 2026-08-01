/**
 * Device Monitor 组件包 — 物模型驱动的设备遥测可视化
 *
 * 使用方式:
 *   import { DeviceMonitor, MetricCard, TrendChart, type TrendMetric } from '@/components/deviceMonitor'
 *
 * 架构:
 *   DeviceMonitor (顶层) → MetricCard (测点卡片) + TrendChart (趋势图)
 *   └── useTelemetry (WS/HTTP 双通道数据源)
 *   └── ThingModelDef (物模型定义驱动)
 */

export { default as DeviceMonitor } from './business/DeviceMonitor.vue'
export { default as MetricCard } from './common/MetricCard.vue'
export { default as TrendChart, type TrendMetric } from './charts/TrendChart.vue'
