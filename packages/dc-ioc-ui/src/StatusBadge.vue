<script setup lang="ts">
import { computed } from 'vue'
import { statusClassOf, statusLabelOf } from './statusMap'

const props = withDefaults(
  defineProps<{
    status: string
    label?: string
  }>(),
  { label: '' },
)

const statusClass = computed(() => statusClassOf(props.status))
const label = computed(() => props.label || statusLabelOf(props.status))
</script>

<template>
  <span class="dui-status-badge" :class="statusClass">
    <span class="dui-status-dot"></span>
    {{ label }}
  </span>
</template>

<style scoped>
/* StatusBadge — @dc-ioc/ui
   颜色只来自全局 :root token（前端 assets/styles/index.scss），不设硬编码兜底。 */
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

.dui-g .dui-status-dot { background: var(--green); box-shadow: 0 0 6px var(--green); }
.dui-g { color: var(--green); }

.dui-a .dui-status-dot { background: var(--amber); box-shadow: 0 0 6px var(--amber); }
.dui-a { color: var(--amber); }

.dui-r .dui-status-dot { background: var(--red); box-shadow: 0 0 6px var(--red); animation: dui-blink 1.2s infinite; }
.dui-r { color: var(--red); }

.dui-b .dui-status-dot { background: var(--blue); box-shadow: 0 0 6px var(--blue); }
.dui-b { color: var(--blue); }

.dui-o .dui-status-dot { background: var(--line); }
.dui-o { color: var(--txt3); }

@keyframes dui-blink { 50% { opacity: 0.3; } }
</style>
