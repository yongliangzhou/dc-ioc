<template>
  <div class="device-table card">
    <div class="dt-header" v-if="title">
      <span class="dt-title">{{ title }}</span>
      <span v-if="count !== undefined" class="dt-count">共 {{ count }} 项</span>
    </div>
    <div class="dt-table-wrap">
      <table>
        <thead>
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              :style="{ width: col.width, textAlign: col.align || 'left' }"
            >
              {{ col.label }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(row, ri) in rows" :key="ri" :class="getRowClass(row)">
            <td v-for="col in columns" :key="col.key" :style="{ textAlign: col.align || 'left' }">
              <!-- 状态列渲染 StatusBadge -->
              <StatusBadge v-if="col.render === 'status'" :status="row[col.key] ?? ''" />
              <!-- 告警列渲染 AlarmBadge -->
              <AlarmBadge v-else-if="col.render === 'alarm'" :level="row[col.key] ?? 'info'" />
              <!-- 自定义渲染 -->
              <slot
                v-else-if="col.render === 'custom'"
                :name="'col-' + col.key"
                :row="row"
                :value="row[col.key]"
              />
              <!-- 默认文本 -->
              <span v-else :class="row._rowClass">{{ row[col.key] ?? '-' }}</span>
            </td>
          </tr>
        </tbody>
      </table>
      <EmptyState v-if="!rows.length" text="暂无设备数据" />
    </div>
  </div>
</template>

<script setup lang="ts">
import StatusBadge from './StatusBadge.vue'
import AlarmBadge from './AlarmBadge.vue'
import EmptyState from './EmptyState.vue'

export interface TableColumn {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
  render?: 'text' | 'status' | 'alarm' | 'custom'
}

withDefaults(
  defineProps<{
    title?: string
    columns: TableColumn[]
    rows: Record<string, any>[]
    count?: number
  }>(),
  {
    rows: () => [],
  },
)

function getRowClass(row: any): string {
  return row._rowClass ?? ''
}
</script>

<style scoped>
.device-table {
  overflow: hidden;
}
.dt-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.dt-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--txt);
}
.dt-count {
  font-size: 11px;
  color: var(--txt3);
}
.dt-table-wrap {
  max-height: 420px;
  overflow-y: auto;
}
.dt-table-wrap::-webkit-scrollbar {
  width: 4px;
}
.dt-table-wrap::-webkit-scrollbar-thumb {
  background: var(--line);
  border-radius: 3px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
thead {
  position: sticky;
  top: 0;
  z-index: 1;
}
thead th {
  background: var(--bg);
  color: var(--txt3);
  font-weight: 500;
  font-size: 11px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line);
}
tbody td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--td-line);
  color: var(--txt);
  white-space: nowrap;
}
tbody tr:hover {
  background: rgba(34, 227, 255, 0.03);
}
tbody tr.row-danger {
  background: rgba(239, 68, 68, 0.06);
}
tbody tr.row-warning {
  background: rgba(255, 176, 32, 0.04);
}
</style>
