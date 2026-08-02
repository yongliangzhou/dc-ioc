<template>
  <span class="status-badge" :class="statusClass">
    <span class="status-dot"></span>
    {{ label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  status: string
  label?: string
}>(), {
  label: '',
})

const STATUS_MAP: Record<string, { cls: string; text: string }> = {
  online:  { cls: 'g', text: '在线' },
  running: { cls: 'g', text: '运行' },
  normal:  { cls: 'g', text: '正常' },
  standby: { cls: 'a', text: '待机' },
  warning: { cls: 'a', text: '告警' },
  fault:   { cls: 'r', text: '故障' },
  error:   { cls: 'r', text: '异常' },
  offline: { cls: 'o', text: '离线' },
  stopped: { cls: 'o', text: '停机' },
  maintenance: { cls: 'b', text: '检修' },
  closing:  { cls: 'b', text: '合闸' },
  opening:  { cls: 'o', text: '分闸' },
}

const statusClass = computed(() => {
  const s = (props.status || '').toLowerCase()
  return STATUS_MAP[s]?.cls ?? 'o'
})

const label = computed(() => {
  const s = (props.status || '').toLowerCase()
  return props.label || STATUS_MAP[s]?.text || props.status || '-'
})
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  line-height: 1;
}
.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.g .status-dot { background: var(--green); box-shadow: 0 0 6px var(--green); }
.a .status-dot { background: var(--amber); box-shadow: 0 0 6px var(--amber); }
.r .status-dot { background: var(--red); box-shadow: 0 0 6px var(--red); animation: badge-blink 1.2s infinite; }
.b .status-dot { background: var(--blue); box-shadow: 0 0 6px var(--blue); }
.o .status-dot { background: #3a4a66; }
.g { color: var(--green); }
.a { color: var(--amber); }
.r { color: var(--red); }
.b { color: var(--blue); }
.o { color: #6b7280; }
@keyframes badge-blink { 50% { opacity: 0.3; } }
</style>
