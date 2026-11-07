<template>
  <div class="cf-wrap">
    <div v-for="f in fields" :key="f.key" class="cf-item">
      <label class="p3-label">
        {{ labelOf(f) }}
        <span v-if="f.required" style="color: #f87171">*</span>
      </label>
      <select
        v-if="f.type === 'select'"
        class="p3-ipt"
        :value="valueOf(f.key)"
        @change="setValue(f.key, $event)"
      >
        <option value="">{{ placeholder }}</option>
        <option v-for="o in f.options || []" :key="o" :value="o">{{ o }}</option>
      </select>
      <input
        v-else
        class="p3-ipt"
        :type="inputType(f.type)"
        :value="valueOf(f.key)"
        @input="setValue(f.key, $event)"
      />
    </div>
    <p v-if="!fields.length" class="p3-empty">{{ emptyText }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { CustomFieldRow } from '@/api/p3'

const props = withDefaults(
  defineProps<{
    fields: CustomFieldRow[]
    modelValue: Record<string, unknown>
    placeholder?: string
    emptyText?: string
  }>(),
  { placeholder: '—', emptyText: '' },
)
const emit = defineEmits<{ (e: 'update:modelValue', value: Record<string, unknown>): void }>()
const { locale } = useI18n()

function labelOf(f: CustomFieldRow): string {
  return locale.value === 'en' ? f.label_en || f.label_zh : f.label_zh
}
function inputType(type: CustomFieldRow['type']): string {
  if (type === 'number') return 'number'
  if (type === 'date') return 'date'
  return 'text'
}
function valueOf(key: string): string {
  const v = props.modelValue[key]
  return v === undefined || v === null ? '' : String(v)
}
function setValue(key: string, event: Event) {
  const target = event.target as HTMLInputElement | HTMLSelectElement
  emit('update:modelValue', { ...props.modelValue, [key]: target.value })
}
</script>
