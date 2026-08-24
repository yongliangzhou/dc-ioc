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
          @keyup.enter="reload"
        />
        <input
          v-model.trim="filters.keyword"
          class="ipt"
          placeholder="关键字 (路径/详情)"
          style="width: 200px"
          @keyup.enter="reload"
        />
        <button class="btn-sm primary" @click="reload">{{ tl('查询') }}</button>
        <button class="btn-sm" @click="resetFilters">{{ tl('重置') }}</button>
        <span class="muted" style="margin-left: auto; font-size: 11px"
          >{{ tl('共') }} {{ total }} {{ tl('条') }}</span
        >
      </div>
    </Panel>

    <!-- 审计日志表格 (Presentational) -->
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
              <span class="tag" :class="statusTag(row.status_code ?? 0)">{{ row.status_code }}</span>
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

    <!-- 分页 -->
    <div class="flex gap8" style="align-items: center; margin-top: 12px">
      <button
        class="btn-sm"
        :disabled="page <= 1"
        @click="page--; reload()"
      >
        {{ tl('上一页') }}
      </button>
      <span class="muted" style="font-size: 12px"
        >{{ tl('第') }} {{ page }} {{ tl('页') }} / {{ tl('共') }} {{ totalPages }}
        {{ tl('页') }}</span
      >
      <button
        class="btn-sm"
        :disabled="page >= totalPages"
        @click="page++; reload()"
      >
        {{ tl('下一页') }}
      </button>
      <select
        v-model="pageSize"
        class="ipt"
        style="width: 120px; margin-left: auto"
        @change="page = 1; reload()"
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
const { t: tl } = useI18n()
import { onMounted, reactive, ref } from 'vue'
import { getAuditLogs, type AuditLogItem } from '@/api'

const rows = ref<AuditLogItem[]>([])
const total = ref(0)
const loading = ref(false)
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
  } catch {
    rows.value = []
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.resource = ''
  filters.action = ''
  filters.username = ''
  filters.keyword = ''
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
</style>
