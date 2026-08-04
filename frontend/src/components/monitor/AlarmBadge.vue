<template>
  <span class="alarm-badge" :class="levelClass">
    {{ text }}
  </span>
</template>

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
  critical: { cls: 'critical', text: '紧急' },
  urgent: { cls: 'critical', text: '紧急' },
  major: { cls: 'major', text: '严重' },
  severe: { cls: 'major', text: '严重' },
  warning: { cls: 'warning', text: '警告' },
  info: { cls: 'info', text: '提示' },
}

const levelClass = computed(() => LEVEL_MAP[props.level?.toLowerCase()]?.cls ?? 'info')
const text = computed(() => {
  const base = LEVEL_MAP[props.level?.toLowerCase()]?.text ?? props.level
  return props.count > 0 ? `${base} ${props.count}` : base
})
</script>

<style scoped>
.alarm-badge {
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
.critical {
  color: #fff;
  background: var(--red);
}
.major {
  color: var(--amber);
  background: rgba(255, 176, 32, 0.15);
  border: 1px solid rgba(255, 176, 32, 0.35);
}
.warning {
  color: var(--amber);
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.25);
}
.info {
  color: var(--blue);
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.25);
}
</style>
