<template>
  <div class="device-table card">
    <div class="dt-header" v-if="title">
      <span class="dt-title">{{ title }}</span>
      <span v-if="count !== undefined" class="dt-count">共 {{ count }} 项</span>
    </div>

    <!-- 表头 -->
    <div class="dt-thead" :style="gridStyle">
      <div
        v-for="col in columns"
        :key="col.key"
        class="dt-th"
        :style="{ textAlign: col.align || 'left' }"
      >
        {{ col.label }}
      </div>
    </div>

    <!-- 数据体: 超过阈值启用虚拟滚动, 否则普通渲染 -->
    <div v-if="!rows.length" class="dt-empty">
      <EmptyState text="暂无设备数据" />
    </div>
    <div v-else-if="useVirtual" class="dt-body dt-body-virtual">
      <VirtualList
        :items="rows"
        :item-height="rowHeight"
        :height="virtualHeight"
        :item-key="rowKey"
        empty-text="暂无设备数据"
      >
        <template #default="{ item }">
          <div class="dt-row" :class="getRowClass(item)" :style="gridStyle">
            <div
              v-for="col in columns"
              :key="col.key"
              class="dt-td"
              :style="{ textAlign: col.align || 'left' }"
            >
              <StatusBadge v-if="col.render === 'status'" :status="(item[col.key] as string) ?? ''" />
              <AlarmBadge v-else-if="col.render === 'alarm'" :level="(item[col.key] as string) ?? 'info'" />
              <slot
                v-else-if="col.render === 'custom'"
                :name="'col-' + col.key"
                :row="item"
                :value="item[col.key]"
              />
              <span v-else :class="(item._rowClass as string) ?? ''">{{ item[col.key] ?? '-' }}</span>
            </div>
          </div>
        </template>
      </VirtualList>
    </div>
    <div v-else class="dt-body">
      <div
        v-for="(row, ri) in rows"
        :key="String(row._uid ?? ri)"
        class="dt-row"
        :class="getRowClass(row)"
        :style="gridStyle"
      >
        <div
          v-for="col in columns"
          :key="col.key"
          class="dt-td"
          :style="{ textAlign: col.align || 'left' }"
        >
          <StatusBadge v-if="col.render === 'status'" :status="(row[col.key] as string) ?? ''" />
          <AlarmBadge v-else-if="col.render === 'alarm'" :level="(row[col.key] as string) ?? 'info'" />
          <slot
            v-else-if="col.render === 'custom'"
            :name="'col-' + col.key"
            :row="row"
            :value="row[col.key]"
          />
          <span v-else :class="(row._rowClass as string) ?? ''">{{ row[col.key] ?? '-' }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { StatusBadge } from '@dc-ioc/ui'
import { AlarmBadge } from '@dc-ioc/ui'
import EmptyState from './EmptyState.vue'
import VirtualList from '@/components/common/VirtualList.vue'

export interface TableColumn {
  key: string
  label: string
  width?: string
  align?: 'left' | 'center' | 'right'
  render?: 'text' | 'status' | 'alarm' | 'custom'
}

const props = withDefaults(
  defineProps<{
    title?: string
    columns: TableColumn[]
    rows: Record<string, unknown>[]
    count?: number
    /** 启用虚拟滚动的阈值 (行数) */
    virtualThreshold?: number
    /** 每行高度 (虚拟滚动时使用) */
    rowHeight?: number
    /** 虚拟滚动容器高度 */
    virtualHeight?: number | string
  }>(),
  {
    rows: () => [],
    virtualThreshold: 100,
    rowHeight: 38,
    virtualHeight: 420,
  },
)

/** 用 WeakMap 为每行生成稳定 uid (不修改 props 对象) */
const _uidMap = new WeakMap<object, string>()
let _uidSeq = 0
function rowKey(row: Record<string, unknown>, _i: number): string | number {
  const r = row as object
  let id = _uidMap.get(r)
  if (id == null) {
    id = `dt-${_uidSeq++}`
    _uidMap.set(r, id)
  }
  return id
}

const useVirtual = computed(() => props.rows.length > props.virtualThreshold)

const gridStyle = computed(() => ({
  display: 'grid',
  gridTemplateColumns: props.columns.map((c) => c.width || '1fr').join(' '),
}))

function getRowClass(row: Record<string, unknown>): string {
  return (row._rowClass as string) ?? ''
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
/* 表头 */
.dt-thead {
  align-items: center;
  background: var(--bg);
  border-bottom: 1px solid var(--line);
  position: sticky;
  top: 0;
  z-index: 2;
}
.dt-th {
  font-size: 11px;
  color: var(--txt3);
  font-weight: 500;
  padding: 8px 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 数据体 */
.dt-body {
  max-height: 420px;
  overflow-y: auto;
}
.dt-body::-webkit-scrollbar,
.dt-body-virtual :deep(.virtual-list)::-webkit-scrollbar {
  width: 4px;
}
.dt-body::-webkit-scrollbar-thumb,
.dt-body-virtual :deep(.virtual-list)::-webkit-scrollbar-thumb {
  background: var(--line);
  border-radius: 3px;
}
.dt-row {
  align-items: center;
  border-bottom: 1px solid var(--td-line);
  font-size: 12px;
  transition: background 0.12s;
}
.dt-row:hover {
  background: rgba(34, 227, 255, 0.03);
}
.dt-row.row-danger {
  background: rgba(239, 68, 68, 0.06);
}
.dt-row.row-warning {
  background: rgba(255, 176, 32, 0.04);
}
.dt-td {
  padding: 8px 10px;
  color: var(--txt);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dt-empty {
  padding: 20px 0;
}
</style>
