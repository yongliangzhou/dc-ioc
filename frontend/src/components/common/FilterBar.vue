<template>
  <div :class="compact ? 'filterbar-compact' : 'filterbar'">
    <div v-if="!compact" class="filterbar-fields"><slot /></div>

    <div class="filterbar-actions">
      <button v-if="!compact" class="btn-primary btn-sm" type="button" @click="emit('query')">
        {{ t('filterView.query') }}
      </button>
      <button v-if="!compact" class="btn-ghost btn-sm" type="button" @click="emit('reset')">
        {{ t('filterView.reset') }}
      </button>
      <button
        class="btn-ghost btn-sm"
        type="button"
        :aria-expanded="openViews"
        @click="openViews = !openViews"
      >
        {{ t('filterView.views')
        }}<span v-if="state.views.length" class="fb-count">{{ state.views.length }}</span>
      </button>
      <button
        v-if="seeds?.length"
        class="btn-ghost btn-sm"
        type="button"
        :aria-expanded="openCols"
        @click="openCols = !openCols"
      >
        {{ t('filterView.columns') }}
      </button>
      <DataBadge
        v-if="source === 'local'"
        tone="partial"
        :label="t('filterView.localOnly')"
        :tip="t('filterView.localTip')"
      />
      <span v-if="notice" class="fb-notice">{{ notice }}</span>
    </div>

    <div v-if="openViews" class="filterbar-panel">
      <div class="fb-save">
        <input
          v-model="draftName"
          class="ipt fb-name"
          type="text"
          :maxlength="40"
          :placeholder="t('filterView.viewName')"
          @keyup.enter="saveCurrent"
        />
        <button
          class="btn-primary btn-sm"
          type="button"
          :disabled="!draftName.trim() || saving"
          @click="saveCurrent"
        >
          {{ t('filterView.save') }}
        </button>
      </div>
      <p v-if="!state.views.length" class="fb-empty">{{ t('filterView.empty') }}</p>
      <ul v-else class="fb-list">
        <li v-for="v in state.views" :key="v.id" class="fb-item">
          <button
            class="btn-ghost btn-sm fb-apply"
            type="button"
            :title="t('filterView.apply')"
            @click="applyView(v)"
          >
            {{ v.name }}
          </button>
          <span v-if="v.id === state.defaultId" class="fb-default">{{
            t('filterView.default')
          }}</span>
          <button
            class="btn-ghost btn-xs"
            type="button"
            :title="t('filterView.setDefault')"
            @click="setDefault(v.id)"
          >
            ☆
          </button>
          <button
            class="btn-ghost btn-xs"
            type="button"
            :title="t('filterView.delete')"
            @click="remove(v.id)"
          >
            ×
          </button>
        </li>
      </ul>
    </div>

    <ColumnConfig
      v-if="openCols && seeds?.length"
      :model-value="effectiveColumns"
      :seeds="seeds"
      @update:model-value="onColumnsChange"
    />
  </div>
</template>

<script setup lang="ts">
/**
 * 04 §6.2 统一筛选栏：查询 / 重置 / 保存视图 / 列配置。
 *
 * 两种接入形态：
 * - 完整模式：替换筛选容器，筛选控件走默认插槽，查询/重置由本组件发出；
 * - `compact`：容器内已有查询/重置按钮时只追加「保存视图 / 列配置」，避免重复按钮。
 *
 * `capture()` 由页面提供当前筛选快照，`apply(view)` 由页面恢复状态并触发加载。
 * 视图持久化与个人隔离交给 `useViewPreferences`；viewer 降级由 `DataBadge` 标注；
 * 列配置通过 `v-model:columns` 双向绑定，页面用 `applyColumns()` 过滤表格列。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import DataBadge from '@/components/common/DataBadge.vue'
import ColumnConfig from '@/components/common/ColumnConfig.vue'
import { defaultColumns, type ColumnDef, type ColumnSeed } from '@/composables/useColumnConfig'
import {
  newViewId,
  normalizeViewState,
  removeView,
  upsertView,
  useViewPreferences,
  type FilterView,
} from '@/composables/useViewPreferences'

interface FilterSnapshot {
  filters: Record<string, string | number>
  page?: number
  size?: number
  columns?: ColumnDef[]
}

const props = defineProps<{
  viewKey: string
  capture: () => FilterSnapshot
  apply: (view: FilterView) => void
  seeds?: ColumnSeed[]
  columns?: ColumnDef[]
  /** 容器内已有查询/重置按钮：只渲染保存视图 / 列配置 */
  compact?: boolean
}>()
const emit = defineEmits<{ query: []; reset: []; 'update:columns': [ColumnDef[]] }>()
const { t } = useI18n()
const { state, source, saving, load, save } = useViewPreferences(props.viewKey)

const openViews = ref(false)
const openCols = ref(false)
const draftName = ref('')
const notice = ref('')
let noticeTimer: ReturnType<typeof setTimeout> | undefined

const effectiveColumns = computed(() =>
  props.columns?.length ? props.columns : props.seeds ? defaultColumns(props.seeds) : [],
)

function flash(text: string) {
  notice.value = text
  if (noticeTimer) clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => {
    notice.value = ''
  }, 2000)
}

onMounted(() => {
  void load()
})
onBeforeUnmount(() => {
  if (noticeTimer) clearTimeout(noticeTimer)
})

async function saveCurrent() {
  const name = draftName.value.trim()
  if (!name) return
  const snap = props.capture()
  const view: FilterView = {
    id: newViewId(),
    name,
    filters: snap.filters,
    columns: (snap.columns ?? effectiveColumns.value).map((c) => ({
      key: c.key,
      visible: c.visible,
      order: c.order,
    })),
    ...(snap.page !== undefined ? { page: snap.page } : {}),
    ...(snap.size !== undefined ? { size: snap.size } : {}),
  }
  const result = await save(upsertView(state.value, view))
  draftName.value = ''
  flash(result === 'failed' ? t('filterView.failed') : t('filterView.saved'))
}

/** 应用视图由页面 `apply` 全权负责（恢复筛选 + 加载）；此处不 emit query，
 *  否则页面的查询处理通常会把 page 重置为 1，视图里保存的页码会失效。 */
function applyView(v: FilterView) {
  props.apply(v)
}

async function remove(id: string) {
  await save(removeView(state.value, id))
}

async function setDefault(id: string) {
  await save(normalizeViewState({ ...state.value, defaultId: id }))
}

function onColumnsChange(next: ColumnDef[]) {
  emit('update:columns', next)
}
</script>

<style scoped>
.filterbar,
.filterbar-compact {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
}
.filterbar {
  padding: var(--space-3);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.filterbar-compact {
  gap: 6px;
}
.filterbar-fields {
  display: flex;
  flex: 1;
  flex-wrap: wrap;
  gap: var(--space-2);
  align-items: center;
  min-width: 0;
}
.filterbar-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.fb-count {
  margin-left: 4px;
  color: var(--txt2);
  font-size: 11px;
}
.fb-notice {
  color: var(--txt2);
  font-size: 12px;
}
.filterbar-panel {
  flex-basis: 100%;
  padding: var(--space-2) var(--space-3);
  background: var(--panel2);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.fb-save {
  display: flex;
  gap: 6px;
  align-items: center;
}
.fb-name {
  max-width: 220px;
}
.fb-empty {
  margin: var(--space-2) 0 0;
  color: var(--txt3);
  font-size: 12px;
}
.fb-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: var(--space-2) 0 0;
  padding: 0;
  list-style: none;
}
.fb-item {
  display: flex;
  gap: 2px;
  align-items: center;
  padding: 2px 4px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
}
.fb-default {
  color: var(--txt3);
  font-size: 11px;
}
@media (max-width: 640px) {
  .filterbar-fields,
  .filterbar-actions {
    flex-basis: 100%;
  }
}
</style>
