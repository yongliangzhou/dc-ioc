<template>
  <div class="colcfg">
    <div class="colcfg-head">
      <span class="colcfg-title">{{ t('filterView.columns') }}</span>
      <button class="btn-ghost btn-xs" type="button" @click="reset">
        {{ t('filterView.resetColumns') }}
      </button>
    </div>
    <ul class="colcfg-list">
      <li v-for="(col, i) in modelValue" :key="col.key" class="colcfg-item">
        <label class="colcfg-label">
          <input
            type="checkbox"
            :checked="col.visible"
            :disabled="col.locked"
            @change="toggle(col.key)"
          />
          <span>{{ col.label }}</span>
          <span v-if="col.locked" class="colcfg-lock">{{ t('filterView.locked') }}</span>
        </label>
        <span class="colcfg-move">
          <button
            class="btn-ghost btn-xs"
            type="button"
            :disabled="i === 0"
            aria-label="move up"
            @click="move(col.key, -1)"
          >
            ↑
          </button>
          <button
            class="btn-ghost btn-xs"
            type="button"
            :disabled="i === modelValue.length - 1"
            aria-label="move down"
            @click="move(col.key, 1)"
          >
            ↓
          </button>
        </span>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
/** 04 §6.2 列配置面板：显隐 + 拖拽式上下排序，纯受控组件。 */
import { useI18n } from 'vue-i18n'
import {
  defaultColumns,
  moveColumn,
  toggleColumn,
  type ColumnDef,
  type ColumnSeed,
} from '@/composables/useColumnConfig'

const props = defineProps<{ modelValue: ColumnDef[]; seeds: ColumnSeed[] }>()
const emit = defineEmits<{ 'update:modelValue': [ColumnDef[]] }>()
const { t } = useI18n()

function toggle(key: string) {
  emit('update:modelValue', toggleColumn(props.modelValue, key))
}
function move(key: string, delta: number) {
  emit('update:modelValue', moveColumn(props.modelValue, key, delta))
}
function reset() {
  emit('update:modelValue', defaultColumns(props.seeds))
}
</script>

<style scoped>
.colcfg {
  flex-basis: 100%;
  padding: var(--space-3);
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.colcfg-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-2);
}
.colcfg-title {
  color: var(--txt);
  font-size: 13px;
  font-weight: 600;
}
.colcfg-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: 0;
  padding: 0;
  list-style: none;
}
.colcfg-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 180px;
  padding: 6px var(--space-2);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.colcfg-label {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 6px;
  color: var(--txt2);
  font-size: 12px;
  cursor: pointer;
}
.colcfg-label input {
  accent-color: var(--cyan);
}
.colcfg-lock {
  color: var(--txt3);
  font-size: 11px;
}
.colcfg-move {
  display: flex;
  gap: 2px;
}
@media (max-width: 640px) {
  .colcfg-item {
    min-width: 100%;
  }
}
</style>
