<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('系统管理') }} {{ tl('·') }} {{ tl('行级变更审计') }}</h1>
      <span class="sub"
        >{{ tl('记录敏感表') }} (users/roles/tenant) {{ tl('的行级变更') }} (I/U/D),
        {{ tl('由数据库触发器自动落库') }} row_audit</span
      >
    </div>

    <!-- 统计概览 (可视化) -->
    <div class="stats" v-if="stats">
      <div class="stat-card">
        <div class="stat-num">{{ stats.total }}</div>
        <div class="stat-lbl">{{ tl('变更总数') }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-lbl">{{ tl('按表分布') }}</div>
        <div class="stat-rows">
          <div class="stat-row" v-for="t in stats.by_table" :key="t.table_name">
            <span class="tag a">{{ t.table_name }}</span>
            <span class="mono">{{ t.count }}</span>
          </div>
          <div class="muted" v-if="!stats.by_table.length">{{ tl('暂无数据') }}</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-lbl">{{ tl('按类型分布') }}</div>
        <div class="stat-rows">
          <div class="stat-row" v-for="a in stats.by_action" :key="a.action">
            <span class="tag" :class="actionTag(a.action)">{{ actionLabel(a.action) }}</span>
            <span class="mono">{{ a.count }}</span>
          </div>
          <div class="muted" v-if="!stats.by_action.length">{{ tl('暂无数据') }}</div>
        </div>
      </div>
    </div>

    <!-- 过滤 -->
    <Panel>
      <div class="flex gap8 wrap" style="align-items: center">
        <select v-model="filters.table_name" class="ipt" style="width: 150px">
          <option value="">{{ tl('全部表') }}</option>
          <option value="users">users</option>
          <option value="roles">roles</option>
          <option value="tenant">tenant</option>
        </select>
        <select v-model="filters.action" class="ipt" style="width: 130px">
          <option value="">{{ tl('全部类型') }}</option>
          <option value="I">{{ tl('插入') }}</option>
          <option value="U">{{ tl('更新') }}</option>
          <option value="D">{{ tl('删除') }}</option>
        </select>
        <input
          v-model.trim="filters.changed_by"
          class="ipt"
          :placeholder="tl('操作人')"
          style="width: 140px"
          @keyup.enter="applyFilters"
        />
        <input v-model="filters.start" class="ipt" type="datetime-local" style="width: 190px" />
        <span class="muted">~</span>
        <input v-model="filters.end" class="ipt" type="datetime-local" style="width: 190px" />
        <button class="btn-sm primary" @click="applyFilters">{{ tl('查询') }}</button>
        <button class="btn-sm" @click="resetFilters">{{ tl('重置') }}</button>
        <span class="muted" style="margin-left: auto; font-size: 11px"
          >{{ tl('共') }} {{ total }} {{ tl('条') }}</span
        >
      </div>
    </Panel>

    <!-- 审计表格 -->
    <AsyncSection
      :loading="loading"
      :error="error"
      :empty="false"
      @retry="reload"
      :min-height="'320px'"
    >
      <Panel class="scroll-x">
        <table>
          <thead>
            <tr>
              <th style="width: 150px">{{ tl('时间') }}</th>
              <th style="width: 70px">{{ tl('类型') }}</th>
              <th style="width: 110px">{{ tl('表名') }}</th>
              <th style="width: 90px">{{ tl('行ID') }}</th>
              <th style="width: 130px">{{ tl('操作人') }}</th>
              <th style="width: 150px">{{ tl('应用') }}</th>
              <th style="width: 60px">{{ tl('详情') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in rows"
              :key="row.id"
              :class="{ sel: selected?.id === row.id }"
              @click="selected = row"
              style="cursor: pointer"
            >
              <td class="mono" style="font-size: 11px">{{ fmtTime(row.ts) }}</td>
              <td>
                <span class="tag" :class="actionTag(row.action ?? '')">{{
                  actionLabel(row.action)
                }}</span>
              </td>
              <td>{{ row.table_name }}</td>
              <td class="mono" style="font-size: 11px">{{ row.row_id }}</td>
              <td>{{ row.changed_by || '—' }}</td>
              <td class="mono" style="font-size: 11px">{{ row.app_name || '—' }}</td>
              <td class="muted">›</td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="7" class="muted" style="text-align: center; padding: 20px">
                {{ loading ? '加载中…' : '暂无审计记录' }}
              </td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </AsyncSection>

    <!-- 选中行: 变更前后差异 -->
    <Panel v-if="selected" class="diff">
      <div class="flex gap8" style="align-items: center; margin-bottom: 8px">
        <span class="tag" :class="actionTag(selected.action ?? '')">{{
          actionLabel(selected.action)
        }}</span>
        <b>{{ selected.table_name }}</b>
        <span class="muted">#{{ selected.row_id }}</span>
        <span class="muted" style="margin-left: auto; font-size: 11px">{{
          fmtTime(selected.ts)
        }}</span>
      </div>
      <div class="diff-grid">
        <div>
          <div class="diff-h">{{ tl('变更前') }}</div>
          <pre class="mono code">{{
            selected.action === 'I' ? '—' : pretty(selected.old_val)
          }}</pre>
        </div>
        <div>
          <div class="diff-h">{{ tl('变更后') }}</div>
          <pre class="mono code">{{
            selected.action === 'D' ? '—' : pretty(selected.new_val)
          }}</pre>
        </div>
      </div>
    </Panel>

    <!-- 分页 -->
    <div class="flex gap8" style="align-items: center; margin-top: 12px">
      <button class="btn-sm" :disabled="page <= 1" @click="goPrev">
        {{ tl('上一页') }}
      </button>
      <span class="muted" style="font-size: 12px"
        >{{ tl('第') }} {{ page }} {{ tl('页') }} / {{ tl('共') }} {{ totalPages }}
        {{ tl('页') }}</span
      >
      <button class="btn-sm" :disabled="page >= totalPages" @click="goNext">
        {{ tl('下一页') }}
      </button>
      <select
        v-model="pageSize"
        class="ipt"
        style="width: 120px; margin-left: auto"
        @change="onPageSizeChange"
      >
        <option :value="20">20 {{ tl('条') }}/{{ tl('页') }}</option>
        <option :value="50">50 {{ tl('条') }}/{{ tl('页') }}</option>
        <option :value="100">100 {{ tl('条') }}/{{ tl('页') }}</option>
        <option :value="200">200 {{ tl('条') }}/{{ tl('页') }}</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { toErrorMessage } from '@/composables/useAsyncPage'
const { t: tl } = useI18n()
import { onMounted, reactive, ref } from 'vue'
import { getRowAuditLogs, getRowAuditStats, type RowAuditItem, type RowAuditStats } from '@/api'

const rows = ref<RowAuditItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const page = ref(1)
const pageSize = ref(50)
const selected = ref<RowAuditItem | null>(null)
const stats = ref<RowAuditStats | null>(null)
const filters = reactive<{
  table_name: string
  action: string
  changed_by: string
  start: string
  end: string
}>({
  table_name: '',
  action: '',
  changed_by: '',
  start: '',
  end: '',
})

const totalPages = ref(1)

function toISO(v: string) {
  if (!v) return undefined
  const d = new Date(v)
  return isNaN(d.getTime()) ? undefined : d.toISOString()
}

async function reload() {
  loading.value = true
  error.value = ''
  try {
    const res = await getRowAuditLogs({
      page: page.value,
      page_size: pageSize.value,
      table_name: filters.table_name || undefined,
      action: filters.action || undefined,
      changed_by: filters.changed_by || undefined,
      start: toISO(filters.start),
      end: toISO(filters.end),
    })
    rows.value = res?.items ?? []
    total.value = res?.total ?? 0
    totalPages.value = Math.max(1, Math.ceil(total.value / pageSize.value))
  } catch (e) {
    rows.value = []
    error.value = toErrorMessage(e) || '行级审计加载失败'
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    stats.value = await getRowAuditStats()
  } catch {
    stats.value = null
  }
}

function resetFilters() {
  filters.table_name = ''
  filters.action = ''
  filters.changed_by = ''
  filters.start = ''
  filters.end = ''
  selected.value = null
  page.value = 1
  reload()
}

/** 筛选/查询: 变更过滤条件后回到第 1 页再查询 */
function applyFilters() {
  page.value = 1
  reload()
}

function goPrev() {
  if (page.value > 1) {
    page.value--
    reload()
  }
}

function goNext() {
  if (page.value < totalPages.value) {
    page.value++
    reload()
  }
}

function onPageSizeChange() {
  page.value = 1
  reload()
}

function pretty(v?: Record<string, unknown> | null) {
  if (!v) return '—'
  try {
    return JSON.stringify(v, null, 2)
  } catch {
    return String(v)
  }
}

function fmtTime(s?: string) {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}
const actionTag = (a: string) => (a === 'I' ? 'g' : a === 'U' ? 'b' : a === 'D' ? 'r' : 'a')
const actionLabel = (a?: string) =>
  a === 'I' ? tl('插入') : a === 'U' ? tl('更新') : a === 'D' ? tl('删除') : (a ?? '—')

onMounted(() => {
  loadStats()
  reload()
})
</script>

<style scoped>
.ipt {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 7px;
  color: var(--txt);
  padding: 6px 10px;
  font-size: 12px;
  outline: none;
}
.ipt:focus {
  border-color: var(--cyan);
}
.btn-sm.primary {
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  color: #04121f;
  border-color: transparent;
  font-weight: 700;
}
.stats {
  display: grid;
  grid-template-columns: 160px 1fr 1fr;
  gap: 12px;
  margin-bottom: 12px;
}
.stat-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
}
.stat-num {
  font-size: 26px;
  font-weight: 800;
  color: var(--cyan);
}
.stat-lbl {
  font-size: 12px;
  color: var(--txt3);
  margin-bottom: 6px;
}
.stat-rows {
  display: flex;
  flex-direction: column;
  gap: 5px;
}
.stat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
}
.diff .diff-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.diff-h {
  font-size: 12px;
  color: var(--txt3);
  margin-bottom: 4px;
}
.code {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  font-size: 11px;
  line-height: 1.5;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}
tr.sel {
  background: var(--panel);
}
</style>
