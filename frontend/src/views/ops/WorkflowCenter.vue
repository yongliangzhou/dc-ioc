<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="page-title">{{ t.title }}</h1>
        <p class="page-sub">{{ t.sub }}</p>
      </div>
      <div class="page-actions">
        <input v-model="kw" class="inp" :placeholder="t.search" />
        <button class="btn green" @click="openEditor()">+ {{ t.newProcess }}</button>
      </div>
    </header>

    <ErrorBanner v-if="knowledgeError" :count="1" :labels="['知识库']" @retry="loadKnowledge" />

    <!-- KPI -->
    <section class="kpi-row">
      <div class="kpi">
        <span class="kpi-v">{{ stats.open }}</span
        ><span class="kpi-l">{{ t.openCount }}</span>
      </div>
      <div class="kpi">
        <span class="kpi-v">{{ stats.monthCreated }}</span
        ><span class="kpi-l">{{ t.monthCreated }}</span>
      </div>
      <div class="kpi">
        <span class="kpi-v">{{ stats.monthClosed }}</span
        ><span class="kpi-l">{{ t.monthClosed }}</span>
      </div>
      <div class="kpi">
        <span class="kpi-v">{{ stats.avgResolve }}</span
        ><span class="kpi-l">{{ t.avgResolve }}</span>
      </div>
      <div class="kpi">
        <span class="kpi-v" :class="stats.breachRate > 20 ? 'bad' : ''"
          >{{ stats.breachRate }}%</span
        ><span class="kpi-l">{{ t.breachRate }}</span>
      </div>
    </section>

    <!-- 筛选 -->
    <section class="filters">
      <div class="seg">
        <button
          v-for="p in types"
          :key="p.key"
          class="seg-btn"
          :class="{ active: fType === p.key }"
          @click="fType = p.key"
        >
          {{ p.label }}
        </button>
      </div>
      <div class="seg">
        <button
          v-for="s in statuses"
          :key="s.key"
          class="seg-btn"
          :class="{ active: fStatus === s.key }"
          @click="fStatus = s.key"
        >
          {{ s.label }}
        </button>
      </div>
    </section>

    <div class="layout">
      <!-- 列表 -->
      <section class="list">
        <article v-for="w in filtered" :key="w.id" class="row-card" @click="openDetail(w)">
          <div class="row-id">{{ w.id }}</div>
          <div class="row-main">
            <div class="row-title">{{ w.title }}</div>
            <div class="row-sub">
              <span class="dot" :class="typeCls(w.type)"></span>{{ typeLabel(w.type) }} ·
              <span :class="priCls(w.priority)">{{ priLabel(w.priority) }}</span> ·
              {{ w.owner }}
            </div>
          </div>
          <div class="row-right">
            <span class="badge" :class="statusCls(w.status)">{{ statusLabel(w.status) }}</span>
            <span class="sla" :class="slaCls(w)">{{ slaText(w) }}</span>
          </div>
        </article>
        <div v-if="!filtered.length" class="empty">{{ t.empty }}</div>
      </section>

      <!-- 右侧统计 -->
      <aside class="side">
        <!-- 按类型分布 -->
        <div class="panel">
          <div class="panel-h">
            <span class="panel-t">{{ t.byType }}</span>
            <span class="panel-meta">{{ t.totalLabel }} {{ totalCount }}</span>
          </div>
          <div
            v-for="d in typeData"
            :key="d.key"
            class="bar-line clickable"
            :title="`${t.clickFilter}：${d.label}`"
            @click="fType = fType === d.key ? 'all' : d.key"
          >
            <span class="bl-label"
              ><i class="bl-dot" :class="typeCls(d.key)"></i>{{ d.label }}</span
            >
            <div class="bl-track">
              <div
                class="bl-fill"
                :class="typeCls(d.key)"
                :style="{ width: barPct(d.count) }"
              ></div>
            </div>
            <span class="bl-num">{{ d.count }}</span>
            <span class="bl-pct">{{ ratioPct(d.count) }}</span>
          </div>
        </div>

        <!-- 按状态分布 -->
        <div class="panel">
          <div class="panel-h">
            <span class="panel-t">{{ t.byStatus }}</span>
            <span class="panel-meta">{{ t.totalLabel }} {{ totalCount }}</span>
          </div>
          <div
            v-for="d in statusData"
            :key="d.key"
            class="bar-line clickable"
            :title="`${t.clickFilter}：${d.label}`"
            @click="fStatus = fStatus === d.key ? 'all' : d.key"
          >
            <span class="bl-label"
              ><i class="bl-dot" :class="statusCls(d.key)"></i>{{ d.label }}</span
            >
            <div class="bl-track">
              <div
                class="bl-fill"
                :class="statusCls(d.key)"
                :style="{ width: barPct(d.count) }"
              ></div>
            </div>
            <span class="bl-num">{{ d.count }}</span>
            <span class="bl-pct">{{ ratioPct(d.count) }}</span>
          </div>
        </div>

        <!-- 近 12 周创建 / 关闭趋势 -->
        <div class="panel">
          <div class="panel-h">
            <span class="panel-t">{{ t.trendTitle }}</span>
            <span class="panel-meta">{{ t.unitTicket }}</span>
          </div>
          <div class="trend-box">
            <div class="trend-y">
              <span v-for="g in trendGridY" :key="g.v" :style="{ top: g.y + 'px' }">{{ g.v }}</span>
            </div>
            <div class="trend-canvas">
              <svg
                :viewBox="`0 0 320 ${trendH}`"
                class="trend"
                preserveAspectRatio="none"
                role="img"
                :aria-label="`${t.trendTitle} · ${t.trendSum}: ${trendSum.created} ${t.trendCreated} / ${trendSum.closed} ${t.trendClosed}`"
              >
                <line
                  v-for="g in trendGridY"
                  :key="'g' + g.v"
                  x1="0"
                  x2="320"
                  :y1="g.y"
                  :y2="g.y"
                  stroke="var(--line)"
                  stroke-width="0.6"
                  stroke-dasharray="4 4"
                />
                <polyline
                  :points="trendPoints.created"
                  fill="none"
                  stroke="var(--cyan)"
                  stroke-width="2"
                />
                <polyline
                  :points="trendPoints.closed"
                  fill="none"
                  stroke="var(--green)"
                  stroke-width="2"
                />
                <circle
                  v-for="(p, i) in trendDots"
                  :key="'p' + i"
                  :cx="p.x"
                  :cy="p.y"
                  r="2"
                  :fill="p.kind === 'created' ? 'var(--cyan)' : 'var(--green)'"
                >
                  <title>
                    {{ p.label }} · {{ p.kind === 'created' ? t.trendCreated : t.trendClosed }}
                    {{ p.v }}
                  </title>
                </circle>
              </svg>
              <div class="trend-x">
                <span v-for="l in trendXLabels" :key="l.i" :style="{ left: l.left + '%' }">{{
                  l.label
                }}</span>
              </div>
            </div>
          </div>
          <div class="legend">
            <span class="lg cyan"></span>{{ t.trendCreated }} <span class="lg green"></span
            >{{ t.trendClosed }}
          </div>
          <div class="trend-sum">
            {{ t.trendSum }}：<b class="cyan">{{ trendSum.created }}</b> {{ t.trendCreated }} /
            <b class="green">{{ trendSum.closed }}</b> {{ t.trendClosed }}
          </div>
          <div v-if="trendEmpty" class="trend-empty">{{ t.trendEmpty }}</div>
        </div>
      </aside>
    </div>

    <!-- 编辑/详情抽屉 -->
    <div v-if="editor || detail" class="mask" @click.self="closeDrawer">
      <aside class="drawer">
        <header class="drawer-head">
          <h2>
            {{
              editor && !editingId
                ? '+ ' + t.newProcess
                : detail
                  ? detail.id + ' · ' + detail.title
                  : t.edit
            }}
          </h2>
          <button
            class="x"
            :title="tc('tooltipClose')"
            :aria-label="tc('tooltipClose')"
            @click="closeDrawer"
          >
            ×
          </button>
        </header>
        <div class="drawer-body">
          <!-- 表单 -->
          <template v-if="editor">
            <div class="form-grid">
              <label class="fld">
                <span>{{ t.process }}</span>
                <select v-model="form.type" class="inp">
                  <option
                    v-for="p in types.filter((x) => x.key !== 'all')"
                    :key="p.key"
                    :value="p.key"
                  >
                    {{ p.label }}
                  </option>
                </select>
              </label>
              <label class="fld">
                <span>{{ t.priority }}</span>
                <select v-model="form.priority" class="inp">
                  <option value="P1">{{ t.p1 }}</option>
                  <option value="P2">{{ t.p2 }}</option>
                  <option value="P3">{{ t.p3 }}</option>
                  <option value="P4">{{ t.p4 }}</option>
                </select>
              </label>
              <label class="fld wide">
                <span>{{ t.titleField }}</span>
                <input v-model="form.title" class="inp" :placeholder="t.titlePlaceholder" />
              </label>
              <label class="fld">
                <span>{{ t.owner }}</span>
                <input v-model="form.owner" class="inp" placeholder="—" />
              </label>
              <label class="fld" v-if="form.type === 'risk'">
                <span>{{ t.riskLevel }}</span>
                <select v-model="form.riskLevel" class="inp">
                  <option value="high">{{ t.high }}</option>
                  <option value="medium">{{ t.medium }}</option>
                  <option value="low">{{ t.low }}</option>
                </select>
              </label>
              <label class="fld wide">
                <span>{{ t.descField }}</span>
                <textarea
                  v-model="form.description"
                  class="area"
                  :placeholder="t.descPlaceholder"
                ></textarea>
              </label>
            </div>
            <div class="drawer-actions">
              <button class="btn green" @click="save">{{ t.submit }}</button>
              <button class="btn ghost" @click="closeDrawer">{{ t.cancel }}</button>
            </div>
          </template>

          <!-- 详情 -->
          <template v-else-if="detail">
            <div class="row">
              <span>{{ t.process }}：</span
              ><b :class="typeCls(detail.type)">{{ typeLabel(detail.type) }}</b>
            </div>
            <div class="row">
              <span>{{ t.priority }}：</span
              ><b :class="priCls(detail.priority)">{{ priLabel(detail.priority) }}</b>
            </div>
            <div class="row">
              <span>{{ t.status }}：</span
              ><b :class="statusCls(detail.status)">{{ statusLabel(detail.status) }}</b>
            </div>
            <div class="row">
              <span>{{ t.owner }}：</span><b>{{ detail.owner }}</b>
            </div>
            <div class="row">
              <span>{{ t.createdAt }}：</span><b>{{ fmt(detail.createdAt) }}</b>
            </div>
            <div class="row">
              <span>{{ t.sla }}：</span><b :class="slaCls(detail)">{{ slaText(detail) }}</b>
            </div>
            <p class="content">{{ detail.description }}</p>

            <!-- 关联知识 -->
            <div class="block">
              <div class="block-h">{{ t.linkedKnowledge }}</div>
              <div v-if="detail.knowledgeLinks?.length" class="links">
                <span v-for="k in detail.knowledgeLinks" :key="k" class="link-chip"
                  >📚 {{ k }}
                  <button
                    class="mini"
                    :title="tc('tooltipUnlink')"
                    :aria-label="tc('tooltipUnlink')"
                    @click="unlink(detail!, k)"
                  >
                    ×
                  </button></span
                >
              </div>
              <div class="cite-row">
                <select v-model="linkPick" class="inp">
                  <option value="">—</option>
                  <option v-for="it in knowledgeItems" :key="it.id" :value="it.id">
                    {{ it.title }}
                  </option>
                </select>
                <button class="btn sm soft" @click="link(detail!)">{{ t.linkKnowledge }}</button>
              </div>
            </div>

            <!-- 审批流 -->
            <div class="block">
              <div class="block-h">{{ t.approvalFlow }}</div>
              <div v-for="(node, i) in detail.approval" :key="i" class="node">
                <span class="node-idx">{{ i + 1 }}</span>
                <div class="node-body">
                  <div class="node-line">
                    <b>{{ t.nodeApprover }}：</b>{{ node.approver }}
                  </div>
                  <div class="node-line">
                    <span class="badge" :class="nodeCls(node.status)">{{
                      nodeLabel(node.status)
                    }}</span>
                    <span v-if="node.comment" class="muted small"> · {{ node.comment }}</span>
                  </div>
                  <div v-if="node.status === 'pending' && canApprove(node)" class="node-actions">
                    <input v-model="node.comment" class="inp sm" :placeholder="t.nodeComment" />
                    <button class="btn sm green" @click="approveNode(detail!, i, 'approved')">
                      {{ t.approve }}
                    </button>
                    <button class="btn sm red" @click="approveNode(detail!, i, 'rejected')">
                      {{ t.reject }}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 处理日志 -->
            <div class="block">
              <div class="block-h">{{ t.logs }}</div>
              <div v-if="detail.logs?.length" class="logs">
                <div v-for="(l, i) in detail.logs" :key="i" class="log">
                  <span class="muted">{{ fmt(l.at) }}</span> · <b>{{ l.user }}</b
                  >：{{ l.text }}
                </div>
              </div>
              <div v-else class="muted small">—</div>
              <div class="cite-row">
                <input
                  v-model="logText"
                  class="inp"
                  :placeholder="t.logPlaceholder"
                  @keyup.enter="addLog(detail!)"
                />
                <button class="btn sm" @click="addLog(detail!)">{{ t.addLog }}</button>
              </div>
            </div>

            <div class="drawer-actions">
              <button
                v-if="detail.status === 'new' || detail.status === 'progress'"
                class="btn"
                @click="advance(detail!)"
              >
                {{ t.next }}
              </button>
              <button
                v-if="['approval', 'approved', 'progress'].includes(detail.status)"
                class="btn green"
                @click="closeWorkflow(detail!)"
              >
                {{ t.close }}
              </button>
              <button v-if="detail.status === 'closed'" class="btn" @click="reopen(detail!)">
                {{ t.reopen }}
              </button>
              <button class="btn ghost" @click="remove(detail!)">{{ t.delete }}</button>
            </div>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/modules/auth'
import { getKnowledgeItems } from '@/api/knowledge'
import type { KnowledgeItem } from '@/types'
import { toErrorMessage, useAsyncPage } from '@/composables/useAsyncPage'
import {
  getWorkflows,
  createWorkflow,
  deleteWorkflow,
  advanceWorkflow as advanceWorkflowApi,
  closeWorkflow as closeWorkflowApi,
  reopenWorkflow as reopenWorkflowApi,
  approveNode as approveNodeApi,
  addWorkflowLog,
  linkKnowledge,
  unlinkKnowledge,
  getWorkflowStats,
} from '@/api/workflow'
import type {
  WorkflowItem,
  WNode,
  WType,
  WPriority,
  NodeStatus,
  WorkflowStats,
} from '@/api/workflow'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'

const { t: raw, tm } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (tm('workflow') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})
/** 通用动作文案（common 命名空间），用于图标按钮的 title / aria-label */
const tc = (k: string) => (raw('common.' + k) as string) || ''
const auth = useAuthStore()
const toast = useToast()
const me = computed(() => auth.user?.username || 'me')

const items = ref<WorkflowItem[]>([])
const _page = useAsyncPage<WorkflowItem[]>(
  async () => {
    const resp = await getWorkflows()
    const data = resp.items || []
    items.value = data
    return data
  },
  { isEmpty: (d) => !d || d.length === 0 },
)
const kw = ref('')
const fType = ref<string>('all')
const fStatus = ref<string>('all')

const types = computed(() => [
  { key: 'all', label: t.all },
  { key: 'incident', label: t.incident },
  { key: 'problem', label: t.problem },
  { key: 'change', label: t.change },
  { key: 'risk', label: t.risk },
])
const statuses = computed(() => [
  { key: 'all', label: t.all },
  { key: 'new', label: t.new },
  { key: 'progress', label: t.progress },
  { key: 'approval', label: t.approval },
  { key: 'approved', label: t.approved },
  { key: 'rejected', label: t.rejected },
  { key: 'closed', label: t.closed },
])

const filtered = computed(() => {
  const q = kw.value.trim().toLowerCase()
  return items.value.filter((w) => {
    if (fType.value !== 'all' && w.type !== fType.value) return false
    if (fStatus.value !== 'all' && w.status !== fStatus.value) return false
    if (q && !(w.id + w.title + w.owner).toLowerCase().includes(q)) return false
    return true
  })
})

// ---- 统计（优先服务端聚合 GET /api/ops/workflows/stats，失败回退本地计算）----
const serverStats = ref<WorkflowStats | null>(null)
const statsFallback = ref(false)
async function loadStats() {
  try {
    serverStats.value = await getWorkflowStats()
    statsFallback.value = false
  } catch {
    serverStats.value = null
    statsFallback.value = true
  }
}

/** 本地回退统计（后端 /stats 不可用时，口径与后端一致） */
const localStats = computed(() => {
  const arr = items.value
  const open = arr.filter((w) => !['closed', 'rejected'].includes(w.status)).length
  const now = new Date()
  const mc = arr.filter(
    (w) =>
      new Date(w.createdAt).getMonth() === now.getMonth() &&
      new Date(w.createdAt).getFullYear() === now.getFullYear(),
  ).length
  const mcl = arr.filter(
    (w) => w.status === 'closed' && new Date(w.updatedAt).getMonth() === now.getMonth(),
  ).length
  const closed = arr.filter((w) => w.status === 'closed')
  const avg = closed.length
    ? closed.reduce(
        (s, w) => s + (new Date(w.updatedAt).getTime() - new Date(w.createdAt).getTime()) / 36e5,
        0,
      ) / closed.length
    : 0
  const breached = arr.filter((w) => isBreached(w)).length
  return {
    open,
    monthCreated: mc,
    monthClosed: mcl,
    avgResolve: avg ? avg.toFixed(1) : '—',
    breachRate: arr.length ? Math.round((breached / arr.length) * 100) : 0,
  }
})

const stats = computed(() => {
  const s = serverStats.value
  if (!s) return localStats.value
  return {
    open: s.open,
    monthCreated: s.monthCreated,
    monthClosed: s.monthClosed,
    avgResolve: s.avgResolve ? String(s.avgResolve) : '—',
    breachRate: Math.round(s.breachRate),
  }
})

function typeCount(k: string) {
  return items.value.filter((w) => w.type === k).length
}
function statusCount(k: string) {
  return items.value.filter((w) => w.status === k).length
}

const totalCount = computed(() => serverStats.value?.total ?? items.value.length)

/** 分布数据：服务端优先，回退本地计数 */
const typeData = computed(() =>
  types.value
    .filter((x) => x.key !== 'all')
    .map((x) => ({
      key: x.key,
      label: x.label,
      count: serverStats.value ? (serverStats.value.byType?.[x.key] ?? 0) : typeCount(x.key),
    })),
)
const statusData = computed(() =>
  statuses.value
    .filter((x) => x.key !== 'all')
    .map((x) => ({
      key: x.key,
      label: x.label,
      count: serverStats.value ? (serverStats.value.byStatus?.[x.key] ?? 0) : statusCount(x.key),
    })),
)
/** 条形图按最大分类值归一化；占比按总数计算 */
const maxBar = computed(() =>
  Math.max(1, ...typeData.value.map((d) => d.count), ...statusData.value.map((d) => d.count)),
)
function barPct(n: number) {
  return Math.round((n / maxBar.value) * 100) + '%'
}
function ratioPct(n: number) {
  return totalCount.value ? Math.round((n / totalCount.value) * 100) + '%' : '0%'
}

// ---- 趋势（近12周：服务端按自然周聚合，回退本地 7 天一桶）----
const trendData = computed(() => {
  const s = serverStats.value
  if (s?.trend?.length) {
    return s.trend.map((p) => ({ label: p.week, created: p.created, closed: p.closed }))
  }
  const weeks = 12
  const now = new Date()
  const out: { label: string; created: number; closed: number }[] = []
  for (let i = weeks - 1; i >= 0; i--) {
    const start = new Date(now)
    start.setDate(now.getDate() - i * 7)
    const end = new Date(start)
    end.setDate(start.getDate() + 7)
    out.push({
      label: `${start.getMonth() + 1}/${start.getDate()}`,
      created: items.value.filter((w) => {
        const d = new Date(w.createdAt)
        return d >= start && d < end
      }).length,
      closed: items.value.filter(
        (w) =>
          w.status === 'closed' &&
          (() => {
            const d = new Date(w.updatedAt)
            return d >= start && d < end
          })(),
      ).length,
    })
  }
  return out
})
const trendH = 120
// 绘图区上下留白；CSS .trend 高度同为 120px，故 SVG y 坐标 1:1 对应 px，刻度可绝对定位对齐
const TREND_PAD_TOP = 6
const TREND_PAD_BOTTOM = 10
const trendPlotH = trendH - TREND_PAD_TOP - TREND_PAD_BOTTOM
const trendMax = computed(() =>
  Math.max(1, ...trendData.value.map((d) => d.created), ...trendData.value.map((d) => d.closed)),
)
/** 数值 -> SVG y 坐标：网格线与数据折线共用，保证刻度标签与网格线严格对齐 */
function trendY(v: number) {
  return trendH - TREND_PAD_BOTTOM - (v / trendMax.value) * trendPlotH
}
/** 三条网格线：顶(max) / 中(max/2) / 底(0) */
const trendGridY = computed(() => [
  { v: trendMax.value, y: trendY(trendMax.value) },
  { v: Math.round(trendMax.value / 2), y: trendY(trendMax.value / 2) },
  { v: 0, y: trendY(0) },
])
const trendPoints = computed(() => {
  const n = trendData.value.length || 1
  const step = 320 / n
  const mk = (pick: (d: (typeof trendData.value)[number]) => number) =>
    trendData.value
      .map((d, i) => {
        const x = (i * step + step / 2).toFixed(1)
        const y = trendY(pick(d)).toFixed(1)
        return `${x},${y}`
      })
      .join(' ')
  return { created: mk((d) => d.created), closed: mk((d) => d.closed) }
})
/** 折线落点圆点：悬停可读出每周具体数值，避免只有线条无落点 */
const trendDots = computed(() => {
  const n = trendData.value.length || 1
  const step = 320 / n
  return trendData.value.flatMap((d, i) => {
    const x = i * step + step / 2
    return [
      { x, y: trendY(d.created), v: d.created, kind: 'created', label: d.label },
      { x, y: trendY(d.closed), v: d.closed, kind: 'closed', label: d.label },
    ]
  })
})
/** X 轴标签：12 周全标会重叠，取首 / 1/3 / 2/3 / 尾 四个刻度 */
const trendXLabels = computed(() => {
  const d = trendData.value
  if (!d.length) return []
  const last = d.length - 1
  const idxs =
    d.length <= 4 ? d.map((_, i) => i) : [0, Math.round(last / 3), Math.round((2 * last) / 3), last]
  return [...new Set(idxs)].map((i) => ({
    i,
    left: ((i + 0.5) / d.length) * 100,
    label: d[i].label,
  }))
})
const trendSum = computed(() => ({
  created: trendData.value.reduce((s, d) => s + d.created, 0),
  closed: trendData.value.reduce((s, d) => s + d.closed, 0),
}))
const trendEmpty = computed(() => trendSum.value.created === 0 && trendSum.value.closed === 0)

// ---- 抽屉 ----
const editor = ref(false)
const detail = ref<WorkflowItem | null>(null)
const editingId = ref<string | null>(null)
const form = ref<Partial<WorkflowItem>>({
  type: 'incident',
  priority: 'P3',
  title: '',
  description: '',
  owner: '',
  riskLevel: 'medium',
})
const logText = ref('')
const linkPick = ref('')
const knowledgeItems = ref<KnowledgeItem[]>([])
const knowledgeError = ref('')
async function loadKnowledge() {
  knowledgeError.value = ''
  try {
    const r = await getKnowledgeItems({ page: 1, page_size: 200 })
    knowledgeItems.value = r.items || []
  } catch (e) {
    knowledgeItems.value = []
    knowledgeError.value = toErrorMessage(e) || '知识库加载失败'
  }
}
onMounted(() => {
  loadKnowledge()
  loadStats()
})

function openEditor() {
  editor.value = true
  editingId.value = null
  form.value = {
    type: 'incident',
    priority: 'P3',
    title: '',
    description: '',
    owner: me.value,
    riskLevel: 'medium',
  }
}
function openDetail(w: WorkflowItem) {
  detail.value = w
  editor.value = false
}
function closeDrawer() {
  editor.value = false
  detail.value = null
  editingId.value = null
}

async function save() {
  if (!form.value.title?.trim()) {
    toast.warning(t.titlePlaceholder)
    return
  }
  const type = form.value.type as WType
  const created = await createWorkflow({
    type,
    title: form.value.title!,
    description: form.value.description || '',
    priority: (form.value.priority as WPriority) || 'P3',
    owner: form.value.owner || me.value,
    applicant: me.value,
    riskLevel: type === 'risk' ? (form.value.riskLevel as any) : undefined,
  })
  items.value = [created, ...items.value]
  closeDrawer()
  void loadStats()
}

async function advance(w: WorkflowItem) {
  const u = await advanceWorkflowApi(w.id)
  replaceItem(u)
}
async function closeWorkflow(w: WorkflowItem) {
  const u = await closeWorkflowApi(w.id)
  replaceItem(u)
}
async function reopen(w: WorkflowItem) {
  const u = await reopenWorkflowApi(w.id)
  replaceItem(u)
}
async function remove(w: WorkflowItem) {
  if (!(await useConfirm({ message: t.confirmDelete, danger: true }))) return
  await deleteWorkflow(w.id)
  items.value = items.value.filter((x) => x.id !== w.id)
  if (detail.value?.id === w.id) detail.value = null
  void loadStats()
}

function canApprove(node: WNode) {
  // 审批权限基于角色: 超管放行; 否则要求当前用户角色集合包含该节点审批角色
  if (node.status !== 'pending') return false
  if (auth.isAdmin) return true
  const roles = auth.user?.roles || []
  const approvers = node.approver
    .split(/[、,，/]/)
    .map((s) => s.trim())
    .filter(Boolean)
  return approvers.some((a) => roles.includes(a))
}
function replaceItem(u: WorkflowItem) {
  const i = items.value.findIndex((x) => x.id === u.id)
  if (i >= 0) items.value.splice(i, 1, u)
  else items.value = [u, ...items.value]
  if (detail.value && detail.value.id === u.id) detail.value = u
  void loadStats()
}
async function approveNode(w: WorkflowItem, idx: number, result: 'approved' | 'rejected') {
  const u = await approveNodeApi(w.id, idx, result, w.approval[idx]?.comment || '')
  replaceItem(u)
}
async function addLog(w: WorkflowItem) {
  const x = logText.value.trim()
  if (!x) return
  const u = await addWorkflowLog(w.id, x)
  logText.value = ''
  replaceItem(u)
}
async function link(w: WorkflowItem) {
  if (!linkPick.value) return
  const u = await linkKnowledge(w.id, linkPick.value)
  linkPick.value = ''
  replaceItem(u)
}
async function unlink(w: WorkflowItem, k: string) {
  const u = await unlinkKnowledge(w.id, k)
  replaceItem(u)
}

// ---- SLA ----
function isBreached(w: WorkflowItem) {
  if (w.status === 'closed') return false
  const hours = (Date.now() - new Date(w.createdAt).getTime()) / 36e5
  return hours > w.slaHours
}
function slaText(w: WorkflowItem) {
  if (w.status === 'closed') return t.slaMet
  const hours = (Date.now() - new Date(w.createdAt).getTime()) / 36e5
  if (hours > w.slaHours) return t.slaBreached
  const left = Math.max(0, w.slaHours - hours)
  return `${t.slaDue} ${left.toFixed(1)}h`
}
function slaCls(w: WorkflowItem) {
  return isBreached(w) ? 'bad' : w.status === 'closed' ? 'good' : ''
}

// ---- 样式辅助 ----
function typeCls(k: string) {
  return { incident: 'cyan', problem: 'amber', change: 'blue', risk: 'red' }[k] || 'gray'
}
function typeLabel(k: string) {
  return (
    ({ incident: t.incident, problem: t.problem, change: t.change, risk: t.risk } as any)[k] || k
  )
}
function priCls(p: string) {
  return { P1: 'bad', P2: 'warn', P3: '', P4: 'muted' }[p] || ''
}
function priLabel(p: string) {
  return ({ P1: t.p1, P2: t.p2, P3: t.p3, P4: t.p4 } as any)[p] || p
}
function statusCls(s: string) {
  return (
    {
      new: 'gray',
      progress: 'blue',
      approval: 'amber',
      approved: 'green',
      rejected: 'red',
      closed: 'gray',
    }[s] || 'gray'
  )
}
function statusLabel(s: string) {
  return (
    (
      {
        new: t.new,
        progress: t.progress,
        approval: t.approval,
        approved: t.approved,
        rejected: t.rejected,
        closed: t.closed,
      } as any
    )[s] || s
  )
}
function nodeCls(s: NodeStatus) {
  return { approved: 'green', rejected: 'red', pending: 'amber', skipped: 'gray' }[s] || 'gray'
}
function nodeLabel(s: NodeStatus) {
  return (
    ({ approved: t.approved, rejected: t.rejected, pending: t.approval, skipped: t.closed } as any)[
      s
    ] || s
  )
}
function fmt(d?: string) {
  return d ? new Date(d).toLocaleString() : '—'
}
</script>

<style scoped>
.page {
  padding: 18px 22px 40px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 16px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
}
.page-sub {
  color: var(--muted);
  font-size: 13px;
  margin-top: 4px;
}
.page-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.inp {
  background: var(--panel-2);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 8px;
  padding: 7px 10px;
  min-width: 160px;
}
.inp.sm {
  min-width: 120px;
  padding: 5px 8px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.kpi {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
}
.kpi-v {
  font-size: 24px;
  font-weight: 800;
  color: var(--cyan);
}
.kpi-v.bad {
  color: #f87171;
}
.kpi-l {
  font-size: 12px;
  color: var(--muted);
  margin-top: 4px;
}
.filters {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.seg {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.seg-btn {
  background: var(--panel-2);
  border: 1px solid var(--line);
  color: var(--muted);
  padding: 5px 12px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
}
.seg-btn.active {
  background: var(--cyan);
  color: #04121a;
  border-color: var(--cyan);
  font-weight: 600;
}
.layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 16px;
  align-items: start;
}
.list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.row-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: border-color 0.15s;
}
.row-card:hover {
  border-color: var(--cyan);
}
.row-id {
  font-family: monospace;
  font-size: 12px;
  color: var(--muted);
  min-width: 96px;
}
.row-main {
  flex: 1;
}
.row-title {
  font-size: 14px;
  font-weight: 600;
}
.row-sub {
  font-size: 12px;
  color: var(--muted);
  margin-top: 3px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.dot.cyan {
  background: var(--cyan);
}
.dot.amber {
  background: #fbbf24;
}
.dot.blue {
  background: #38bdf8;
}
.dot.red {
  background: #f87171;
}
.dot.gray {
  background: var(--line);
}
.row-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}
.sla {
  font-size: 11px;
  color: var(--muted);
}
.sla.bad {
  color: #f87171;
}
.sla.good {
  color: #4ade80;
}
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
}
.badge.green {
  background: rgba(34, 197, 94, 0.16);
  color: #4ade80;
}
.badge.amber {
  background: rgba(245, 158, 11, 0.16);
  color: #fbbf24;
}
.badge.red {
  background: rgba(239, 68, 68, 0.16);
  color: #f87171;
}
.badge.blue {
  background: rgba(56, 189, 248, 0.16);
  color: #38bdf8;
}
.badge.gray {
  background: var(--panel-2);
  color: var(--muted);
}
.empty {
  text-align: center;
  color: var(--muted);
  padding: 40px;
}
.side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: sticky;
  top: 16px;
}
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 12px 14px;
}
.panel-h {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 10px;
}
.panel-t {
  color: var(--text);
}
.panel-meta {
  font-size: 11px;
  font-weight: 400;
  color: var(--muted);
}
.bar-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 6px 0;
  font-size: 12px;
}
.bar-line.clickable {
  cursor: pointer;
  border-radius: 6px;
  padding: 1px 2px;
  transition: background 0.15s;
}
.bar-line.clickable:hover {
  background: rgba(255, 255, 255, 0.05);
}
.bl-label {
  width: 62px;
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 5px;
}
.bl-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--muted);
}
.bl-dot.cyan {
  background: var(--cyan);
}
.bl-dot.amber {
  background: #fbbf24;
}
.bl-dot.blue {
  background: #38bdf8;
}
.bl-dot.red {
  background: #f87171;
}
.bl-dot.green {
  background: var(--green);
}
.bl-dot.gray {
  background: var(--muted);
}
.bl-track {
  flex: 1;
  height: 8px;
  background: var(--panel-2);
  border-radius: 6px;
  overflow: hidden;
}
.bl-fill {
  height: 100%;
  border-radius: 6px;
  background: var(--cyan);
}
.bl-fill.gray {
  background: var(--muted);
}
.bl-fill.cyan {
  background: var(--cyan);
}
.bl-fill.amber {
  background: #fbbf24;
}
.bl-fill.blue {
  background: #38bdf8;
}
.bl-fill.red {
  background: #f87171;
}
.bl-fill.green {
  background: var(--green);
}
.bl-num {
  width: 22px;
  text-align: right;
  font-weight: 600;
}
.bl-pct {
  width: 34px;
  text-align: right;
  color: var(--muted);
  font-size: 11px;
}

/* 趋势图：Y 轴刻度 + 虚线网格 + X 轴首尾周标签 + 合计说明 */
.trend-box {
  display: flex;
  gap: 6px;
}
.trend-y {
  position: relative;
  height: 120px;
  width: 26px;
  font-size: 10px;
  color: var(--muted);
}
.trend-y span {
  position: absolute;
  right: 0;
  transform: translateY(-50%);
}
.trend-canvas {
  flex: 1;
  min-width: 0;
}
.trend {
  width: 100%;
  height: 120px;
  display: block;
}
.trend-x {
  position: relative;
  height: 14px;
  margin-top: 2px;
  font-size: 10px;
  color: var(--muted);
}
.trend-x span {
  position: absolute;
  transform: translateX(-50%);
  white-space: nowrap;
}
.legend {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--muted);
  margin-top: 6px;
}
.lg {
  width: 10px;
  height: 3px;
  border-radius: 2px;
  display: inline-block;
  margin-left: 10px;
}
.lg.cyan {
  background: var(--cyan);
}
.lg.green {
  background: var(--green);
}
.trend-sum {
  margin-top: 6px;
  font-size: 11px;
  color: var(--muted);
}
.trend-sum b.cyan {
  color: var(--cyan);
}
.trend-sum b.green {
  color: var(--green);
}
.trend-empty {
  margin-top: 4px;
  font-size: 10px;
  color: var(--muted);
  font-style: italic;
}
.mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: flex-end;
  z-index: 50;
}
.drawer {
  width: 480px;
  max-width: 94vw;
  background: var(--panel);
  height: 100%;
  overflow-y: auto;
  padding: 18px 20px;
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.drawer-head h2 {
  font-size: 16px;
}
.x {
  background: transparent;
  border: none;
  color: var(--muted);
  font-size: 18px;
  cursor: pointer;
}
.row {
  font-size: 13px;
  margin: 6px 0;
  color: var(--muted);
}
.row b {
  color: var(--text);
}
.content {
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  background: var(--panel-2);
  border-radius: 10px;
  padding: 12px;
  margin: 10px 0;
}
.block {
  margin-top: 14px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}
.block-h {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}
.fld.wide {
  grid-column: 1/-1;
}
.area {
  width: 100%;
  min-height: 80px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 8px;
  padding: 10px;
  resize: vertical;
}
.cite-row {
  display: flex;
  gap: 8px;
  margin: 8px 0;
}
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.link-chip {
  font-size: 12px;
  background: var(--panel-2);
  border-radius: 8px;
  padding: 4px 8px;
  display: flex;
  align-items: center;
  gap: 4px;
}
.mini {
  background: none;
  border: none;
  color: var(--muted);
  cursor: pointer;
}
.node {
  display: flex;
  gap: 10px;
  margin: 8px 0;
}
.node-idx {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--panel-2);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}
.node-body {
  flex: 1;
}
.node-line {
  font-size: 12px;
  margin: 2px 0;
}
.node-actions {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}
.logs {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 8px;
}
.log {
  font-size: 12px;
  background: var(--panel-2);
  border-radius: 8px;
  padding: 6px 8px;
}
.muted {
  color: var(--muted);
}
.small {
  font-size: 11px;
}
.drawer-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.btn {
  border: 1px solid var(--line);
  background: var(--panel-2);
  color: var(--text);
  border-radius: 8px;
  padding: 7px 12px;
  cursor: pointer;
  font-size: 13px;
}
.btn.sm {
  padding: 4px 10px;
  font-size: 12px;
}
.btn.ghost {
  background: transparent;
}
.btn.soft {
  background: rgba(34, 211, 238, 0.12);
  color: var(--cyan);
  border-color: transparent;
}
.btn.green {
  background: var(--green);
  color: #04121a;
  border-color: var(--green);
  font-weight: 600;
}
.btn.red {
  background: rgba(239, 68, 68, 0.16);
  color: #f87171;
  border-color: transparent;
}
.bad {
  color: #f87171;
}
.warn {
  color: #fbbf24;
}
.good {
  color: #4ade80;
}
@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .side {
    position: static;
  }
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
