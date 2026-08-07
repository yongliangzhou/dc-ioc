<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(
  defineProps<{
    status: string
    label?: string
  }>(),
  {
    label: '',
  },
)

const STATUS_MAP: Record<string, { cls: string; text: string }> = {
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

const statusClass = computed(() => {
  const s = (props.status || '').toLowerCase()
  return 'dui-' + (STATUS_MAP[s]?.cls ?? 'dui-o')
})

const label = computed(() => {
  const s = (props.status || '').toLowerCase()
  return props.label || STATUS_MAP[s]?.text || props.status || '-'
})
</script>

<template>
  <span class="dui-status-badge" :class="statusClass">
    <span class="dui-status-dot"></span>
    {{ label }}
  </span>
</template>

<style scoped>
/* StatusBadge — @dc-ioc/ui
   Requires CSS variables: --green, --amber, --red, --blue */
.dui-status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  line-height: 1;
}
.dui-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* green */
.dui-g .dui-status-dot {
  background: var(--green, #22c55e);
  box-shadow: 0 0 6px var(--green, #22c55e);
}
.dui-g {
  color: var(--green, #22c55e);
}

/* amber */
.dui-a .dui-status-dot {
  background: var(--amber, #f59e0b);
  box-shadow: 0 0 6px var(--amber, #f59e0b);
}
.dui-a {
  color: var(--amber, #f59e0b);
}

/* red (blink) */
.dui-r .dui-status-dot {
  background: var(--red, #ef4444);
  box-shadow: 0 0 6px var(--red, #ef4444);
  animation: dui-blink 1.2s infinite;
}
.dui-r {
  color: var(--red, #ef4444);
}

/* blue */
.dui-b .dui-status-dot {
  background: var(--blue, #3b82f6);
  box-shadow: 0 0 6px var(--blue, #3b82f6);
}
.dui-b {
  color: var(--blue, #3b82f6);
}

/* offline / gray */
.dui-o .dui-status-dot {
  background: #3a4a66;
}
.dui-o {
  color: #6b7280;
}

@keyframes dui-blink {
  50% {
    opacity: 0.3;
  }
}
</style>
