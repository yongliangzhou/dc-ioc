<template>
  <div class="time-range-picker">
    <span class="trp-label">时间范围</span>
    <div class="trp-options">
      <button
        v-for="opt in options"
        :key="opt.key"
        class="trp-btn"
        :class="{ active: modelValue === opt.key }"
        @click="onChange(opt.key)"
      >
        {{ opt.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface TimeRangeOption {
  key: string
  label: string
}

withDefaults(
  defineProps<{
    modelValue?: string
    options?: TimeRangeOption[]
  }>(),
  {
    modelValue: '24h',
    options: () => [
      { key: '24h', label: '24h' },
      { key: '7d', label: '7天' },
      { key: '30d', label: '30天' },
    ],
  },
)

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

function onChange(key: string) {
  emit('update:modelValue', key)
}
</script>

<style scoped>
.time-range-picker {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.trp-label {
  font-size: 11px;
  color: var(--txt3);
}
.trp-options {
  display: flex;
  gap: 4px;
  background: var(--track);
  border-radius: 6px;
  padding: 2px;
}
.trp-btn {
  border: none;
  background: transparent;
  color: var(--txt3);
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.15s;
  line-height: 1.4;
}
.trp-btn:hover {
  color: var(--txt);
}
.trp-btn.active {
  background: var(--cyan);
  color: #070d1a;
  font-weight: 600;
}
</style>
