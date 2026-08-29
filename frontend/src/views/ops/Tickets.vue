<template>
  <div>
    <div class="view-head">
      <div class="vh-left">
        <h1>{{ tl('工单中心') }}</h1>
        <span class="sub"
          >{{ tl('维修工单') }} {{ tl('与') }} {{ tl('事件工单') }} {{ tl('统一创建') }} · {{ tl('派发') }} · {{ tl('跟踪') }} {{ tl('·') }}
          {{ tl('告警自动转单') }} {{ tl('·') }} {{ tl('状态流转') }} {{ tl('·') }} SLA {{ tl('跟踪') }} {{ tl('·') }}
          {{ tl('按看板分组') }}</span
        >
      </div>
      <button class="hdr-btn ghost" :disabled="store.loading" @click="reload">
        <RefreshCw :size="13" :class="{ 'is-spin': store.loading }" />
        {{ store.loading ? '刷新中' : '刷新' }}
      </button>
      <button class="hdr-btn" v-bind="authState('write')" @click="openCreate">
        + {{ tl('新建工单') }}
      </button>
    </div>

    <!-- 内容区: 加载 / 失败可重试 / 空态 -->
    <AsyncSection
      :page="page"
      skeleton-variant="skeleton"
      :skeleton-rows="5"
      min-height="240px"
      empty-title="暂无工单"
      empty-desc="后端未返回任何工单，可从告警直接转单，或手动创建一张"
      @retry="reload"
    >
      <template #empty-actions>
        <button class="link-btn" v-bind="authState('write')" @click="openCreate">
          + {{ tl('新建工单') }}
        </button>
      </template>

      <!-- KPI -->
      <div class="grid cols-4">
        <KpiCard :title="tl('待处理')" :value="stats.open" unit="单" status="warning" />
        <KpiCard :title="tl('处理中')" :value="stats.doing" unit="单" />
        <KpiCard :title="tl('待归档')" :value="stats.pending" unit="单" />
        <KpiCard :title="tl('累计闭环')" :value="stats.done" unit="单" />
      </div>

      <!-- 批量操作条（选中后出现） -->
      <Panel v-if="selectedTickets.length" class="batch-bar">
        <span class="bb-count">已选 {{ selectedTickets.length }} 张</span>
        <button
          class="bb-btn primary"
          :disabled="!advanceableSelected.length || batching"
          v-bind="authState('write')"
          @click="batchAdvance"
        >
          批量推进{{ advanceableSelected.length ? ` (${advanceableSelected.length})` : '' }}
        </button>
        <button
          class="bb-btn danger"
          :disabled="batching"
          v-bind="authState('write')"
          @click="batchDelete"
        >
          批量删除
        </button>
        <button class="bb-btn" @click="exportSelected">导出所选 CSV</button>
        <button class="bb-btn" @click="selectedIds = []">取消选择</button>
      </Panel>

      <!-- 工具条 -->
      <Panel class="toolbar">
      <input
        v-model.trim="kw"
        class="ipt"
        :placeholder="tl('搜索工单号 / 标题 / 责任')"
        style="width: 220px"
      />
      <select v-model="fStatus" class="ipt" style="width: 120px">
        <option value="">{{ tl('全部状态') }}</option>
        <option v-for="s in STATUS_ORDER" :key="s" :value="s">{{ statusLabel(s) }}</option>
      </select>
      <select v-model="fLv" class="ipt" style="width: 110px">
        <option value="">{{ tl('全部级别') }}</option>
        <option value="crit">{{ tl('紧急') }}</option>
        <option value="warn">{{ tl('重要') }}</option>
        <option value="info">{{ tl('提示') }}</option>
      </select>
      <div class="flex1"></div>
      <button class="tb-btn" :disabled="!tickets.length" @click="exportAll">
        导出全部 CSV
      </button>
      <div class="seg">
        <button :class="{ on: view === 'kanban' }" @click="view = 'kanban'">
          {{ tl('看板') }}
        </button>
        <button :class="{ on: view === 'table' }" @click="view = 'table'">{{ tl('列表') }}</button>
      </div>
    </Panel>

    <!-- 看板视图 -->
    <template v-if="view === 'kanban'">
      <div class="kanban">
        <div class="kcol" v-for="col in STATUS_ORDER" :key="col">
          <div class="kh">
            <span :style="{ color: colColor(col) }">{{ statusLabel(col) }}</span>
            <span class="muted">{{ filtered.filter((x) => x.state === col).length }}</span>
          </div>
          <div
            class="kcard-i"
            v-for="x in filtered.filter((y) => y.state === col)"
            :key="x.id"
            :class="{ 'is-sel': selectedIds.includes(x.id) }"
            @click="openDetail(x)"
          >
            <div class="flex between">
              <label class="ck-wrap" @click.stop>
                <input
                  type="checkbox"
                  class="ck"
                  :checked="selectedIds.includes(x.id)"
                  @change="toggleRow(x.id)"
                />
              </label>
              <b class="kcard-title">{{ x.title }}</b>
              <span class="tag" :class="lvClass(x.lv)">{{ lvText(x.lv) }}</span>
            </div>
            <div class="km">{{ x.id }} {{ tl('·') }} {{ x.sys }} {{ tl('·') }} {{ x.owner }}</div>
            <div class="km">{{ tl('创建') }} {{ x.created }} {{ tl('·') }} SLA {{ x.sla }}</div>
            <div class="progress kbar" style="height: 5px">
              <i :style="{ width: x.progress + '%', background: colColor(col) }"></i>
            </div>
            <div class="kacts" @click.stop>
              <button
                class="kbtn"
                v-if="col !== 'done'"
                v-bind="authState('write')"
                @click="advance(x)"
                :title="tl('推进到下一状态')"
              >
                {{ tl('推进') }} ▸
              </button>
              <button
                class="kbtn ghost"
                v-bind="authState('write')"
                @click="openEdit(x)"
                :title="tl('编辑')"
              >
                ✎
              </button>
              <button
                class="kbtn ghost danger"
                v-bind="authState('write')"
                @click="askDelete(x)"
                :title="tl('删除')"
              >
                🗑
              </button>
            </div>
          </div>
          <div class="kempty muted" v-if="!filtered.filter((y) => y.state === col).length">
            {{ tl('无工单') }}
          </div>
        </div>
      </div>
    </template>

    <!-- 列表视图 -->
    <template v-else>
      <Panel class="scroll-x">
        <table>
          <thead>
            <tr>
              <th style="width: 36px">
                <input
                  type="checkbox"
                  class="ck"
                  :checked="allSelected"
                  :indeterminate.prop="someSelected && !allSelected"
                  :disabled="!filtered.length"
                  @change="toggleAll"
                  title="全选 / 取消全选"
                />
              </th>
              <th scope="col">工单号</th>
              <th scope="col">标题</th>
              <th scope="col">系统</th>
              <th scope="col">级别</th>
              <th scope="col">状态</th>
              <th scope="col">责任</th>
              <th scope="col">创建时间</th>
              <th scope="col">SLA</th>
              <th scope="col">进度</th>
              <th style="width: 140px">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="x in filtered"
              :key="x.id"
              @click="openDetail(x)"
              style="cursor: pointer"
              :class="{ 'row-sel': selectedIds.includes(x.id) }"
            >
              <td @click.stop>
                <input
                  type="checkbox"
                  class="ck"
                  :checked="selectedIds.includes(x.id)"
                  @change="toggleRow(x.id)"
                />
              </td>
              <td class="mono">{{ x.id }}</td>
              <td>{{ x.title }}</td>
              <td>{{ x.sys }}</td>
              <td>
                <span class="tag" :class="lvClass(x.lv)">{{ lvText(x.lv) }}</span>
              </td>
              <td>
                <span class="tag" :class="tagClass(x.state)">{{ statusLabel(x.state) }}</span>
              </td>
              <td>{{ x.owner }}</td>
              <td class="mono">{{ x.created }}</td>
              <td>{{ x.sla }}</td>
              <td>
                <div class="progress" style="width: 80px">
                  <i
                    :style="{ width: x.progress + '%', background: pctColor(x.progress, 50, 80) }"
                  ></i>
                </div>
              </td>
              <td>
                <div class="flex gap4" @click.stop>
                  <button
                    class="act-btn"
                    v-if="x.state !== 'done'"
                    v-bind="authState('write')"
                    @click="advance(x)"
                  >
                    推进
                  </button>
                  <button class="act-btn ghost" v-bind="authState('write')" @click="openEdit(x)">
                    编辑
                  </button>
                  <button class="act-btn danger" v-bind="authState('write')" @click="askDelete(x)">
                    删
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="tbl-empty" v-if="!filtered.length">
          <span class="muted">当前筛选条件下无匹配工单</span>
          <button class="link-btn" @click="resetFilter">清空筛选条件</button>
        </div>
      </Panel>
    </template>
    </AsyncSection>

    <!-- 新建 / 编辑弹窗 -->
    <TicketFormModal
      :open="formOpen"
      :title="editing ? '编辑工单' : '新建工单'"
      :is-edit="!!editing"
      :initial="formInitial"
      @close="closeForm"
      @submit="onFormSubmit"
    />

    <!-- 详情 / 生命周期弹窗 -->
    <teleport to="body">
      <div v-if="detail" class="tf-mask" @click.self="detail = null">
        <div class="tf-modal">
          <div class="tf-head">
            <h3>工单详情 · 生命周期</h3>
            <button class="tf-x" @click="detail = null">✕</button>
          </div>
          <div class="tf-body">
            <div class="dv-row">
              <span class="dv-k">工单号</span><span class="dv-v mono">{{ detail.id }}</span>
            </div>
            <div class="dv-row">
              <span class="dv-k">标题</span><span class="dv-v">{{ detail.title }}</span>
            </div>
            <div class="dv-row">
              <span class="dv-k">系统 / 级别</span
              ><span class="dv-v"
                >{{ detail.sys }} ·
                <span class="tag" :class="lvClass(detail.lv)">{{ lvText(detail.lv) }}</span></span
              >
            </div>
            <div class="dv-row">
              <span class="dv-k">责任 / SLA</span
              ><span class="dv-v">{{ detail.owner }} · {{ detail.sla }}</span>
            </div>
            <div class="dv-row">
              <span class="dv-k">来源</span
              ><span class="dv-v">
                <span class="tag" :class="detail.source === 'alarm' ? 'r' : 'b'">{{
                  detail.source === 'alarm' ? '告警转单' : '手动创建'
                }}</span>
                <span v-if="detail.sourceAlarmId" class="mono muted">
                  ({{ detail.sourceAlarmId }})</span
                >
              </span>
            </div>
            <div class="dv-row">
              <span class="dv-k">进度</span
              ><span class="dv-v">
                <div
                  class="progress"
                  style="width: 160px; display: inline-block; vertical-align: middle"
                >
                  <i
                    :style="{
                      width: detail.progress + '%',
                      background: pctColor(detail.progress, 50, 80),
                    }"
                  ></i>
                </div>
                {{ detail.progress }}%
              </span>
            </div>
            <div class="dv-desc">
              <b>描述</b>
              <p>{{ detail.description || '—' }}</p>
            </div>

            <div class="dv-section">状态流转</div>
            <div class="seg full">
              <button
                v-for="s in STATUS_ORDER"
                :key="s"
                :class="{ on: detail.state === s }"
                :disabled="detail.state === s"
                @click="jumpState(detail, s)"
              >
                {{ statusLabel(s) }}
              </button>
            </div>

            <div class="dv-section">操作日志 ({{ detail.logs.length }})</div>
            <div class="loglist">
              <div class="logitem" v-for="(l, i) in [...detail.logs].reverse()" :key="i">
                <span class="ldot" :class="logColor(l.action)"></span>
                <div class="ltxt">
                  <b>{{ logText(l) }}</b>
                  <div class="lmeta">
                    {{ l.operator }} · {{ l.ts }}<span v-if="l.note"> · {{ l.note }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="tf-foot">
            <button class="tf-btn ghost" @click="detail = null">关闭</button>
            <button
              class="tf-btn primary"
              v-if="detail.state !== 'done'"
              @click="advance(detail)"
            >
              推进状态
            </button>
          </div>
        </div>
      </div>
    </teleport>

    <!-- 删除确认 -->
    <teleport to="body">
      <div v-if="toDelete.length" class="tf-mask" @click.self="toDelete = []">
        <div class="tf-modal" style="width: 440px">
          <div class="tf-head">
            <h3>确认删除工单（{{ toDelete.length }} 张）</h3>
            <button class="tf-x" @click="toDelete = []">✕</button>
          </div>
          <div class="tf-body">
            <p style="color: var(--txt); font-size: 13px; margin: 0 0 8px">
              此操作不可恢复，确定删除以下工单？
            </p>
            <ul class="del-list">
              <li v-for="t in toDelete" :key="t.id">
                <b class="mono">{{ t.id }}</b> 「{{ t.title }}」
              </li>
            </ul>
          </div>
          <div class="tf-foot">
            <button class="tf-btn ghost" @click="toDelete = []">取消</button>
            <button
              class="tf-btn primary"
              style="background: var(--red, #ff4d5e)"
              :disabled="deleting"
              @click="doDelete"
            >
              {{ deleting ? '删除中…' : `删除 ${toDelete.length} 张` }}
            </button>
          </div>
        </div>
      </div>
    </teleport>

    <KnowledgePanels :knowledge="ticketKb" />

    <div class="footer-note">
      运维作业·事件工单中心 — 全生命周期 CRUD · {{ tickets.length }} 张工单 ·
      数据实时读写后端 /api/ops/tickets（离线时无法加载与提交）
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import { computed, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { storeToRefs } from 'pinia'
import { useTicketsStore } from '@/stores/modules/tickets'
import { lvClass, lvText, tagClass, pctColor } from '@/utils/state'
import { TICKET_STATUS_ORDER, TICKET_STATUS_LABEL } from '@/types'
import type { Ticket, TicketStatus, TicketCreateRequest, PowerKnowledge } from '@/types'
import KnowledgePanels from '@/components/KnowledgePanels.vue'
import TicketFormModal from '@/components/business/TicketFormModal.vue'
import { KpiCard } from '@dc-ioc/ui'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { toErrorMessage } from '@/composables/useAsyncPage'
import { downloadCsv, stampedName } from '@/utils/export'
import { useToast } from '@/hooks/useToast'
import { usePermission, type PermAction } from '@/hooks/usePermission'

const toast = useToast()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

const store = useTicketsStore()
const { stats, tickets } = storeToRefs(store)

/**
 * 呈现状态映射：store 自己管 loading/lastError，这里只做「失败 → 可见」。
 * 离线时 tickets 为空且 lastError 非空 → 走 ErrorRetry，而不是原来的空白页。
 * 形状与 useAsyncPage 的 AsyncPageResult 对齐，保证 AsyncSection 契约一致。
 */
function makePage(): {
  loading: boolean
  error: string
  empty: boolean
  retrying: boolean
} {
  const hasData = tickets.value.length > 0
  const err = store.lastError ?? ''
  return {
    loading: store.loading && !hasData,
    error: hasData ? '' : err,
    empty: !store.loading && !err && !hasData,
    retrying: store.loading,
  }
}
const page = computed(makePage)
/** 统一的重载入口：刷新按钮与失败重试都走它，与上架 useAsyncPage 的 reload 语义一致 */
const reload = () => store.load()
const ticketKb: PowerKnowledge = {
  thresholds: [
    { k: tl('闭环跟踪'), v: '告警→工单→问题→风险', note: 'EOP 覆盖 62 类事件' },
    { k: '闭环率(自动关闭)', v: '71%', note: 'SLA 跟踪 MTTA/MTTR' },
  ],
  arch: {
    components: ['告警中心', '事件工单(Tickets)', '问题根因', '风险中心(Risk)', '知识库/EOP'],
    design: '工单是运维闭环的纽带：一条告警生成工单，处置沉淀为问题，反复/高危升级为风险。',
    redundancy: '全生命周期 CRUD，状态可追踪。',
  },
  logic: [
    {
      title: tl('事件→问题→风险 双闭环'),
      steps: [
        { step: 1, text: tl('告警触发 → 生成事件工单'), ok: true },
        { step: 2, text: tl('工单处置沉淀为问题根因'), ok: true },
        { step: 3, text: tl('反复/高危问题升级为风险项并跟踪'), ok: true },
        { step: 4, text: tl('EOP 覆盖 62 类主要事件, 一键拉预案'), ok: true },
      ],
    },
  ],
  note: '事件工单中心是“运维闭环的纽带”：把瞬时告警转化为可追踪、可复盘的工作项，并向上沉淀为问题与风险。',
}

const STATUS_ORDER = TICKET_STATUS_ORDER
const statusLabel = (s: TicketStatus) => TICKET_STATUS_LABEL[s]
const colColor = (s: TicketStatus) =>
  s === 'open'
    ? 'var(--amber)'
    : s === 'doing'
      ? 'var(--cyan)'
      : s === 'pending'
        ? 'var(--purple, #a78bfa)'
        : 'var(--green)'

/* ---- 过滤 ---- */
const kw = ref('')
const fStatus = ref('')
const fLv = ref('')
const view = ref<'kanban' | 'table'>('kanban')

const filtered = computed(() => {
  const q = kw.value.toLowerCase()
  return tickets.value.filter((t) => {
    if (fStatus.value && t.state !== fStatus.value) return false
    if (fLv.value && t.lv !== fLv.value) return false
    if (q && !`${t.id} ${t.title} ${t.owner} ${t.sys}`.toLowerCase().includes(q)) return false
    return true
  })
})

function resetFilter() {
  kw.value = ''
  fStatus.value = ''
  fLv.value = ''
}

/* ---- 批量选择 ---- */
const selectedIds = ref<string[]>([])
const batching = ref(false)
const deleting = ref(false)

const selectedTickets = computed(() => tickets.value.filter((t) => selectedIds.value.includes(t.id)))
/** 可推进 = 未处于终态 done */
const advanceableSelected = computed(() => selectedTickets.value.filter((t) => t.state !== 'done'))

const allSelected = computed(
  () => filtered.value.length > 0 && filtered.value.every((t) => selectedIds.value.includes(t.id)),
)
const someSelected = computed(() => filtered.value.some((t) => selectedIds.value.includes(t.id)))

function toggleRow(id: string) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((x) => x !== id)
    : [...selectedIds.value, id]
}
function toggleAll() {
  selectedIds.value = allSelected.value ? [] : filtered.value.map((t) => t.id)
}

async function batchAdvance() {
  const list = advanceableSelected.value
  if (!list.length) return
  batching.value = true
  try {
    let ok = 0
    for (const t of list) {
      try {
        await store.advance(t.id)
        ok += 1
      } catch (e: unknown) {
        toast.error(`${t.id} 推进失败：${toErrorMessage(e)}`)
      }
    }
    if (ok) toast.success(`已批量推进 ${ok} 张工单`)
    selectedIds.value = []
  } finally {
    batching.value = false
  }
}

/* ---- 导出 ---- */
const EXPORT_HEADERS = [
  '工单号',
  '标题',
  '系统',
  '级别',
  '状态',
  '责任人',
  '创建时间',
  'SLA',
  '进度(%)',
  '来源',
  '描述',
]
function toExportRows(list: Ticket[]) {
  return list.map((t) => [
    t.id,
    t.title,
    t.sys,
    lvText(t.lv),
    statusLabel(t.state),
    t.owner,
    t.created,
    t.sla,
    t.progress,
    t.source === 'alarm' ? '告警转单' : '手动创建',
    t.description ?? '',
  ])
}
function exportAll() {
  downloadCsv(stampedName('工单'), EXPORT_HEADERS, toExportRows(filtered.value))
  toast.success(`已导出 ${filtered.value.length} 张工单`)
}
function exportSelected() {
  downloadCsv(stampedName('工单-选中'), EXPORT_HEADERS, toExportRows(selectedTickets.value))
  toast.success(`已导出 ${selectedTickets.value.length} 张工单`)
}

/* ---- 表单弹窗 ---- */
const formOpen = ref(false)
const editing = ref<Ticket | null>(null)
const formInitial = ref<Partial<TicketCreateRequest>>({})

function openCreate() {
  editing.value = null
  formInitial.value = {}
  formOpen.value = true
}
function openEdit(t: Ticket) {
  editing.value = t
  formInitial.value = {
    title: t.title,
    sys: t.sys,
    lv: t.lv,
    owner: t.owner,
    sla: t.sla,
    description: t.description,
  }
  formOpen.value = true
}
function closeForm() {
  formOpen.value = false
  editing.value = null
}
const saving = ref(false)
async function onFormSubmit(data: TicketCreateRequest) {
  if (saving.value) return // 防重复提交
  const target = editing.value
  saving.value = true
  try {
    if (target) {
      await store.update(target.id, data)
      toast.success(tl('已更新工单'))
    } else {
      await store.create(data)
      toast.success(tl('已新建工单'))
    }
    closeForm()
  } catch (e: unknown) {
    // 关键: 后端写失败时必须报错, 不能先弹"已新建/已更新"再悄悄抛异常
    toast.error(`${target ? tl('更新') : tl('新建')}失败：${toErrorMessage(e)}`)
  } finally {
    saving.value = false
  }
}

/* ---- 详情 / 生命周期 ---- */
const detail = ref<Ticket | null>(null)
function openDetail(t: Ticket) {
  detail.value = store.getById(t.id) ?? t
}
async function advance(t: Ticket) {
  try {
    await store.advance(t.id)
    if (detail.value) detail.value = store.getById(t.id) ?? null
    const after = store.getById(t.id)
    if (after) toast.info(`${tl('已推进至')} ${statusLabel(after.state)}`)
  } catch (e: unknown) {
    toast.error(`${t.id} ${tl('推进')}失败：${toErrorMessage(e)}`)
  }
}
async function jumpState(t: Ticket, s: TicketStatus) {
  try {
    await store.transition(t.id, { state: s, operator: '运维人员' })
    if (detail.value) detail.value = store.getById(t.id) ?? null
    toast.info(`${tl('已流转至')} ${statusLabel(s)}`)
  } catch (e: unknown) {
    toast.error(`${t.id} ${tl('流转')}失败：${toErrorMessage(e)}`)
  }
}

/* ---- 删除（单张 / 批量共用一个确认弹窗） ---- */
const toDelete = ref<Ticket[]>([])
function askDelete(t: Ticket) {
  toDelete.value = [t]
}
function batchDelete() {
  toDelete.value = selectedTickets.value
}
async function doDelete() {
  const list = toDelete.value
  toDelete.value = []
  if (!list.length) return
  deleting.value = true
  try {
    let ok = 0
    for (const t of list) {
      try {
        await store.remove(t.id)
        ok += 1
      } catch (e: unknown) {
        toast.error(`${t.id} ${tl('删除')}失败：${toErrorMessage(e)}`)
      }
    }
    if (ok) toast.success(`已删除 ${ok} 张工单`)
    selectedIds.value = []
  } finally {
    deleting.value = false
  }
}

/* ---- 日志着色 ---- */
function logColor(a: string) {
  return a === 'create' ? 'b' : a === 'close' ? 'g' : a === 'transition' ? 'a' : 'o'
}
function logText(l: { action: string; from?: TicketStatus; to?: TicketStatus }) {
  if (l.action === 'create') return '创建工单'
  if (l.action === 'close') return '关单闭环'
  if (l.action === 'update') return '更新字段'
  if (l.action === 'transition' && l.from && l.to)
    return `${statusLabel(l.from)} → ${statusLabel(l.to)}`
  return l.action
}
</script>

<style scoped>
.hdr-btn {
  margin-left: auto;
  padding: 6px 14px;
  border-radius: 7px;
  cursor: pointer;
  background: linear-gradient(135deg, #1a73e8, #22e3ff);
  color: #fff;
  border: none;
  font-size: 12px;
  font-weight: 600;
}
.kpi-card {
  min-height: 65px;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
}
.flex1 {
  flex: 1;
}
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
.seg {
  display: flex;
  border: 1px solid var(--line);
  border-radius: 7px;
  overflow: hidden;
}
.seg button {
  background: var(--bg2);
  border: none;
  color: var(--txt2);
  padding: 6px 14px;
  font-size: 12px;
  cursor: pointer;
}
.seg button.on {
  background: rgba(34, 227, 255, 0.14);
  color: var(--cyan);
  font-weight: 600;
}
.seg.full {
  width: 100%;
}
.seg.full button {
  flex: 1;
}

/* 看板 */
.kanban {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.kcol {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px;
  min-height: 200px;
}
.kh {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12.5px;
  font-weight: 700;
  margin-bottom: 8px;
}
.kcard-i {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.kcard-i:hover {
  border-color: rgba(34, 227, 255, 0.35);
}
.kcard-i .km {
  font-size: 10.5px;
  color: var(--txt3);
  margin-top: 4px;
}
.kbar {
  margin-top: 6px;
}
.kacts {
  display: flex;
  gap: 4px;
  margin-top: 8px;
}
.kbtn {
  font-size: 10.5px;
  padding: 3px 8px;
  border-radius: 5px;
  border: 1px solid var(--line);
  background: rgba(34, 227, 255, 0.1);
  color: var(--cyan);
  cursor: pointer;
}
.kbtn.ghost {
  background: var(--bg2);
  color: var(--txt2);
}
.kbtn.danger {
  background: rgba(255, 77, 94, 0.1);
  color: var(--red, #ff4d5e);
  border-color: rgba(255, 77, 94, 0.25);
}
.kempty {
  text-align: center;
  font-size: 11px;
  padding: 12px 0;
}

/* 表格操作 */
.act-btn {
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--line);
  font-size: 10px;
  cursor: pointer;
  background: rgba(34, 227, 255, 0.1);
  color: var(--cyan);
}
.act-btn.ghost {
  background: var(--bg2);
  color: var(--txt2);
}
.act-btn.danger {
  background: rgba(255, 77, 94, 0.1);
  color: var(--red, #ff4d5e);
  border-color: rgba(255, 77, 94, 0.25);
}

/* 详情 */
.dv-row {
  display: flex;
  gap: 10px;
  font-size: 12.5px;
  padding: 5px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.dv-k {
  color: var(--txt3);
  width: 88px;
  flex-shrink: 0;
}
.dv-v {
  color: var(--txt);
}
.dv-desc {
  margin-top: 10px;
  font-size: 12.5px;
  color: var(--txt2);
}
.dv-desc p {
  margin: 4px 0 0;
  white-space: pre-wrap;
  line-height: 1.5;
}
.dv-section {
  margin: 14px 0 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--cyan);
}
.loglist {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 220px;
  overflow: auto;
}
.logitem {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
.ldot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-top: 4px;
  background: var(--txt3);
  flex-shrink: 0;
}
.ldot.g {
  background: var(--green);
}
.ldot.a {
  background: var(--amber);
}
.ldot.b {
  background: var(--cyan);
}
.ldot.o {
  background: var(--txt3);
}
.ltxt {
  font-size: 12px;
  color: var(--txt);
}
.lmeta {
  font-size: 10px;
  color: var(--txt3);
  margin-top: 2px;
}

/* ===== 本轮新增: 头部 / 批量 / 复选 / 空态 ===== */
.view-head {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.vh-left {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.hdr-btn.ghost {
  background: transparent;
  border: 1px solid var(--line);
  color: var(--txt2);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-left: 0;
}
.hdr-btn.ghost:hover:not(:disabled) {
  color: #fff;
  border-color: var(--cyan);
}
.hdr-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.is-spin {
  animation: tk-rotate 0.8s linear infinite;
}
@keyframes tk-rotate {
  to {
    transform: rotate(360deg);
  }
}
.link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: var(--cyan, #22e3ff);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* 批量操作条 */
.batch-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 12px;
  margin-bottom: 10px;
  border-color: rgba(34, 227, 255, 0.35);
}
.bb-count {
  font-size: 12px;
  font-weight: 600;
  color: var(--cyan, #22e3ff);
}
.bb-btn,
.tb-btn {
  padding: 5px 12px;
  border-radius: 7px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt2);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.bb-btn:hover:not(:disabled),
.tb-btn:hover:not(:disabled) {
  color: #fff;
  border-color: var(--cyan, #22e3ff);
}
.bb-btn:disabled,
.tb-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.bb-btn.primary {
  border-color: var(--cyan, #22e3ff);
  color: var(--cyan, #22e3ff);
}
.bb-btn.primary:hover:not(:disabled) {
  background: rgba(34, 227, 255, 0.12);
}
.bb-btn.danger {
  border-color: rgba(255, 77, 94, 0.45);
  color: var(--red, #ff4d5e);
}
.bb-btn.danger:hover:not(:disabled) {
  background: rgba(255, 77, 94, 0.12);
}

/* 复选框 */
.ck {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: var(--cyan, #22e3ff);
  vertical-align: middle;
}
.ck-wrap {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  flex-shrink: 0;
}
.kcard-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 选中态 */
.row-sel {
  background: rgba(34, 227, 255, 0.08);
  box-shadow: inset 2px 0 0 var(--cyan, #22e3ff);
}
.kcard-i.is-sel {
  border-color: var(--cyan, #22e3ff);
  box-shadow: 0 0 0 1px rgba(34, 227, 255, 0.35);
}

/* 表格内空态（筛选无结果，区别于整页空态） */
.tbl-empty {
  text-align: center;
  padding: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

/* 删除确认列表 */
.del-list {
  margin: 0;
  padding-left: 18px;
  max-height: 220px;
  overflow: auto;
  font-size: 12.5px;
  line-height: 1.8;
  color: var(--txt2);
}

/* ===== 响应式 ===== */
@media (max-width: 1100px) {
  .kanban {
    grid-template-columns: repeat(2, 1fr);
  }
  .toolbar {
    flex-wrap: wrap;
  }
  .toolbar .ipt {
    flex: 1 1 140px;
    width: auto !important;
  }
  .flex1 {
    display: none;
  }
}
@media (max-width: 720px) {
  .view-head {
    flex-wrap: wrap;
  }
  .kanban {
    grid-template-columns: 1fr;
  }
  .batch-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
