<template>
  <div class="device-card card" :class="statusClass">
    <div class="dc-head">
      <span class="dc-name">{{ name }}</span>
      <StatusBadge :status="status" />
    </div>
    <div class="dc-body">
      <slot>
        <div v-for="(m, i) in metrics" :key="i" class="dc-metric">
          <span class="dc-m-label">{{ m.label }}</span>
          <span class="dc-m-value" :class="m.status"
            >{{ m.value }}<small v-if="m.unit">{{ m.unit }}</small></span
          >
        </div>
      </slot>
    </div>
    <div v-if="$slots.actions" class="dc-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { StatusBadge } from '@dc-ioc/ui'

export interface DeviceMetric {
  label: string
  value?: string | number
  unit?: string
  status?: 'normal' | 'warning' | 'danger'
}

const props = withDefaults(
  defineProps<{
    name: string
    status?: string
    metrics?: DeviceMetric[]
    variant?: 'default' | 'compact'
  }>(),
  {
    variant: 'default',
    status: '',
  },
)

const statusClass = computed(() => {
  const s = (props.status || '').toLowerCase()
  if (s === 'fault' || s === 'error' || s === 'offline') return 'dc-fault'
  if (s === 'standby' || s === 'maintenance') return 'dc-standby'
  return ''
})
</script>

<style scoped>
.device-card {
  min-width: 150px;
}

.dc-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.dc-name {
  font-weight: 700;
  font-size: 13px;
  color: var(--txt-strong);
}

.dc-body {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
  gap: 6px;
}
.dc-metric {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.dc-m-label {
  font-size: 10px;
  color: var(--txt3);
}
.dc-m-value {
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--txt);
}
.dc-m-value small {
  font-size: 10px;
  color: var(--txt3);
  font-weight: 400;
  margin-left: 2px;
}
.dc-m-value.danger {
  color: var(--red);
}
.dc-m-value.warning {
  color: var(--amber);
}

.dc-actions {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--td-line);
}

.dc-fault {
  border-color: rgba(255, 77, 94, 0.3);
}
.dc-standby {
  opacity: 0.7;
}
</style>
