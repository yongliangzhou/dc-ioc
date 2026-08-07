<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    level: string // critical / major / warning / info
    count?: number
  }>(),
  {
    count: 0,
  },
)

const LEVEL_MAP: Record<string, { cls: string; text: string }> = {
  critical: { cls: 'dui-critical', text: '紧急' },
  urgent: { cls: 'dui-critical', text: '紧急' },
  major: { cls: 'dui-major', text: '严重' },
  severe: { cls: 'dui-major', text: '严重' },
  warning: { cls: 'dui-warning', text: '警告' },
  info: { cls: 'dui-info', text: '提示' },
}

const levelClass = computed(() => LEVEL_MAP[props.level?.toLowerCase()]?.cls ?? 'dui-info')

const text = computed(() => {
  const base = LEVEL_MAP[props.level?.toLowerCase()]?.text ?? props.level
  return props.count > 0 ? `${base} ${props.count}` : base
})
</script>

<template>
  <span class="dui-alarm-badge" :class="levelClass">
    {{ text }}
  </span>
</template>

<style scoped>
/* AlarmBadge — @dc-ioc/ui
   Requires CSS variables: --red, --amber, --blue */
.dui-alarm-badge {
  display: inline-flex;
  align-items: center;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 10.5px;
  font-weight: 600;
  line-height: 18px;
  white-space: nowrap;
  letter-spacing: 0.3px;
}

.dui-critical {
  color: #fff;
  background: var(--red, #ef4444);
}

.dui-major {
  color: var(--amber, #f59e0b);
  background: rgba(255, 176, 32, 0.15);
  border: 1px solid rgba(255, 176, 32, 0.35);
}

.dui-warning {
  color: var(--amber, #f59e0b);
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.25);
}

.dui-info {
  color: var(--blue, #3b82f6);
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.25);
}
</style>
