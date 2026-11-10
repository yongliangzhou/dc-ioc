<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('系统管理') }} {{ tl('·') }} {{ tl('操作审计') }}</h1>
      <span class="sub"
        >{{ tl('记录所有写操作') }} (CRUD) {{ tl('与关键读操作') }}, {{ tl('由后端') }} core/audit
        {{ tl('中间件自动落库') }}</span
      >
    </div>

    <!-- 过滤 (容器层状态) -->
    <Panel>
      <div class="flex gap8 wrap" style="align-items: center">
        <select v-model="filters.resource" class="ipt" style="width: 170px">
          <option value="">{{ tl('全部资源') }}</option>
          <option value="auth">auth</option>
          <option value="alarms">alarms</option>
          <option value="users">users</option>
          <option value="devices">devices</option>
          <option value="tickets">tickets</option>
          <option value="knowledge">knowledge</option>
          <option value="drill">drill</option>
          <option value="risk">risk</option>
          <option value="external">external</option>
          <option value="alarm-rules">alarm-rules</option>
          <option value="ops">ops</option>
        </select>
        <select v-model="filters.action" class="ipt" style="width: 140px">
          <option value="">{{ tl('全部动作') }}</option>
          <option value="create">create</option>
          <option value="update">update</option>
          <option value="delete">delete</option>
          <option value="login">login</option>
        </select>
        <input
          v-model.trim="filters.username"
          class="ipt"
          :placeholder="tl('操作人')"
          style="width: 140px"
          @keyup.enter="applyFilters"
        />
        <input
          v-model.trim="filters.keyword"
          class="ipt"
          placeholder="关键字 (路径/详情)"
          style="width: 200px"
          @keyup.enter="applyFilters"
        />
        <button class="btn-sm btn-primary" @click="applyFilters">{{ tl('查询') }}</button>
        <button class="btn-ghost btn-sm" @click="resetFilters">{{ tl('重置') }}</button>
        <FilterBar compact view-key="audit-logs" :capture="captureView" :apply="applySavedView" />
        <button class="btn-sm" :disabled="!rows.length" @click="exportCsv">导出 CSV</button>
        <span class="muted" style="margin-left: auto; font-size: 11px"
          >{{ tl('共') }} {{ total }} {{ tl('条') }}</span
        >
      </div>
    </Panel>

    <!-- 审计日志表格 (Presentational) -->
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
              <th style="width: 80px">{{ tl('方法') }}</th>
              <th style="width: 80px">{{ tl('动作') }}</th>
              <th style="width: 120px">{{ tl('资源') }}</th>
              <th>{{ tl('路径') }}</th>
              <th style="width: 120px">{{ tl('操作人') }}</th>
              <th style="width: 110px">{{ tl('客户端') }} IP</th>
              <th style="width: 70px">{{ tl('状态码') }}</th>
              <th>{{ tl('请求详情') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.id">
              <td class="mono" style="font-size: 11px">{{ fmtTime(row.ts) }}</td>
              <td>
                <span class="tag b">{{ row.method }}</span>
              </td>
              <td>
                <span class="tag" :class="actionTag(row.action ?? '')">{{ row.action }}</span>
              </td>
              <td>{{ row.resource }}</td>
              <td
                class="mono"
                style="font-size: 11px; max-width: 260px; overflow: hidden; text-overflow: ellipsis"
                :title="row.path"
              >
                {{ row.path }}
              </td>
              <td>{{ row.username || '匿名' }}</td>
              <td class="mono" style="font-size: 11px">{{ row.ip }}</td>
              <td>
                <span class="tag" :class="statusTag(row.status_code ?? 0)">{{
                  row.status_code
                }}</span>
              </td>
              <td
                class="mono"
                style="
                  font-size: 10.5px;
                  max-width: 320px;
                  overflow: hidden;
                  text-overflow: ellipsis;
                  white-space: nowrap;
                "
                :title="row.detail"
              >
                {{ row.detail }}
              </td>
            </tr>
            <tr v-if="!rows.length">
              <td colspan="9" class="muted" style="text-align: center; padding: 20px">
                {{ loading ? '加载中…' : '暂无审计记录' }}
              </td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </AsyncSection>

    <!-- 分页 -->
    <Pagination
      :total="total"
      :page="page"
      :size="pageSize"
      @change="onPageChange"
      @size-change="onSizeChange"
    />
  </div>
</template>

<script setup lang="ts">
import FilterBar from '@/components/common/FilterBar.vue'
import type { FilterView } from '@/composables/useViewPreferences'
import { useReactiveFilterQuery } from '@/composables/useFilterQuery'
import Pagination from '@/components/Pagination.vue'
import { useI18n } from 'vue-i18n'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { toErrorMessage } from '@/composables/useAsyncPage'
const { t: tl } = useI18n()
import { onMounted, reactive, ref } from 'vue'
import { getAuditLogs, type AuditLogItem } from '@/api'

const rows = ref<AuditLogItem[]>([])
const total = ref(0)
const loading = ref(false)
const error = ref('')
const page = ref(1)
const pageSize = ref(50)
const filters = reactive<{ resource: string; action: string; username: string; keyword: string }>({
  resource: '',
  action: '',
  username: '',
  keyword: '',
})

const totalPages = ref(1)

async function reload() {
  loading.value = true
  error.value = ''
  try {
    const res = await getAuditLogs({
      page: page.value,
      page_size: pageSize.value,
      resource: filters.resource || undefined,
      action: filters.action || undefined,
      username: filters.username || undefined,
      keyword: filters.keyword || undefined,
    })
    rows.value = res?.items ?? []
    total.value = res?.total ?? 0
    totalPages.value = Math.max(1, Math.ceil(total.value / pageSize.value))
  } catch (e) {
    rows.value = []
    error.value = toErrorMessage(e) || '审计日志加载失败'
  } finally {
    loading.value = false
  }
}

/** RFC4180 转义: 含逗号/引号/换行的字段加双引号, 内部引号翻倍 */
function csvCell(value: unknown): string {
  const s = value == null ? '' : String(value)
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

/** 导出当前页已加载的记录 (不额外请求后端, 后端不可达时同样可用) */
function exportCsv() {
  const header = [
    '时间',
    '方法',
    '动作',
    '资源',
    '路径',
    '操作人',
    '客户端 IP',
    '状态码',
    '请求详情',
  ]
  const lines = rows.value.map((r) =>
    [
      fmtTime(r.ts),
      r.method,
      r.action ?? '',
      r.resource,
      r.path,
      r.username ?? '',
      r.ip,
      r.status_code ?? '',
      r.detail,
    ]
      .map(csvCell)
      .join(','),
  )
  // BOM 保证中文在 Excel 中不乱码
  const blob = new Blob(['\uFEFF' + [header.join(','), ...lines].join('\r\n')], {
    type: 'text/csv;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

function resetFilters() {
  filters.resource = ''
  filters.action = ''
  filters.username = ''
  filters.keyword = ''
  page.value = 1
  reload()
}

/** 筛选/查询: 变更过滤条件后回到第 1 页再查询 */
function applyFilters() {
  page.value = 1
  reload()
}

function onSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  reload()
}

function fmtTime(s?: string) {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}
const actionTag = (a: string) =>
  a === 'create' ? 'g' : a === 'update' ? 'b' : a === 'delete' ? 'r' : a === 'login' ? 'p' : 'a'
const statusTag = (c: number) => (c >= 500 ? 'r' : c >= 400 ? 'a' : 'g')

onMounted(reload)

function onPageChange(p: number) {
  page.value = p
  reload()
}

// 04 §6.2: 筛选条件与分页写入 URL query
useReactiveFilterQuery(filters, { page, size: pageSize })

// 04 §6.2: 统一筛选栏的保存视图（compact 模式，查询/重置仍由本页提供）
function captureView() {
  return { filters: { ...filters } }
}

function applySavedView(v: FilterView) {
  const f = v.filters
  for (const [k, val] of Object.entries(f)) {
    if (typeof val === 'string' && k in filters) Object.assign(filters, { [k]: val })
  }
  void applyFilters()
}
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
  color: var(--txt3);
  border-color: transparent;
  font-weight: 700;
}
</style>
