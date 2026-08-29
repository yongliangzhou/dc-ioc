<template>
  <span class="data-badge" :class="`db-${tone}`" :title="tip || defaultTip">
    <component :is="toneIcon" :size="11" class="db-icon" />
    <slot>{{ label || defaultLabel }}</slot>
  </span>
</template>

<script setup lang="ts">
/**
 * DataBadge — 数据可信度角标
 *
 * 运维平台里"看不到数据来源"比"数据不好看"危险得多。
 * 凡是前端合成 / 后端未返回时的本地兜底 / 部分降级的数据，都必须挂角标，
 * 让值班人员一眼知道这不是真实遥测。
 *
 * 用法:
 *   <DataBadge tone="sample" />                       → 示例数据
 *   <DataBadge tone="mock" tip="后端未返回，已回退本地模拟" />
 *   <DataBadge tone="stale" label="数据陈旧" />
 */
import { computed } from 'vue'
import { FlaskConical, AlertTriangle, Clock, CircleSlash } from 'lucide-vue-next'

type Tone = 'mock' | 'sample' | 'stale' | 'partial'

const props = withDefaults(
  defineProps<{
    /** mock=本地模拟兜底; sample=前端合成示例; stale=数据陈旧; partial=部分降级 */
    tone?: Tone
    /** 覆盖默认文案 */
    label?: string
    /** 悬浮说明, 讲清"为什么这不是真数据" */
    tip?: string
  }>(),
  { tone: 'sample' },
)

const LABELS: Record<Tone, string> = {
  mock: '模拟数据',
  sample: '示例数据',
  stale: '数据陈旧',
  partial: '部分降级',
}

const TIPS: Record<Tone, string> = {
  mock: '后端未返回有效数据，当前展示的是本地模拟数据，不可作为决策依据',
  sample: '该图表由前端基于当前指标合成示例曲线，非真实历史时序',
  stale: '数据超过预期刷新周期，可能已不反映当前状态',
  partial: '部分数据源加载失败，展示内容不完整',
}

const ICONS = {
  mock: FlaskConical,
  sample: FlaskConical,
  stale: Clock,
  partial: CircleSlash,
} as const

const defaultLabel = computed(() => LABELS[props.tone] ?? LABELS.sample)
const defaultTip = computed(() => TIPS[props.tone] ?? TIPS.sample)
const toneIcon = computed(() => ICONS[props.tone] ?? AlertTriangle)
</script>

<style scoped>
.data-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
  padding: 2px 7px;
  border-radius: 999px;
  font-size: 10px;
  line-height: 1.5;
  font-weight: 500;
  letter-spacing: 0.02em;
  white-space: nowrap;
  cursor: help;
  border: 1px solid transparent;
}
.db-icon {
  opacity: 0.9;
}

/* 示例 / 模拟: 琥珀色 —— 醒但不刺眼, 区别于红色告警 */
.db-sample,
.db-mock {
  color: #d9a441;
  background: rgba(217, 164, 65, 0.12);
  border-color: rgba(217, 164, 65, 0.35);
}
/* 陈旧: 灰蓝 */
.db-stale {
  color: #8892b0;
  background: rgba(136, 146, 176, 0.12);
  border-color: rgba(136, 146, 176, 0.3);
}
/* 部分降级: 橙红 */
.db-partial {
  color: #e0844a;
  background: rgba(224, 132, 74, 0.12);
  border-color: rgba(224, 132, 74, 0.35);
}
</style>
