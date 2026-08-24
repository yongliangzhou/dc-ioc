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

    <!-- KPI -->
    <section class="kpi-row">
      <div class="kpi"><span class="kpi-v">{{ stats.open }}</span><span class="kpi-l">{{ t.openCount }}</span></div>
      <div class="kpi"><span class="kpi-v">{{ stats.monthCreated }}</span><span class="kpi-l">{{ t.monthCreated }}</span></div>
      <div class="kpi"><span class="kpi-v">{{ stats.monthClosed }}</span><span class="kpi-l">{{ t.monthClosed }}</span></div>
      <div class="kpi"><span class="kpi-v">{{ stats.avgResolve }}</span><span class="kpi-l">{{ t.avgResolve }}</span></div>
      <div class="kpi"><span class="kpi-v" :class="stats.breachRate > 20 ? 'bad' : ''">{{ stats.breachRate }}%</span><span class="kpi-l">{{ t.breachRate }}</span></div>
    </section>

    <!-- 筛选 -->
    <section class="filters">
      <div class="seg">
        <button v-for="p in types" :key="p.key" class="seg-btn" :class="{ active: fType === p.key }" @click="fType = p.key">{{ p.label }}</button>
      </div>
      <div class="seg">
        <button v-for="s in statuses" :key="s.key" class="seg-btn" :class="{ active: fStatus === s.key }" @click="fStatus = s.key">{{ s.label }}</button>
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
        <div class="panel">
          <div class="panel-h">{{ t.byType }}</div>
          <div v-for="p in types.filter(x => x.key !== 'all')" :key="p.key" class="bar-line">
            <span class="bl-label">{{ p.label }}</span>
            <div class="bl-track"><div class="bl-fill" :class="typeCls(p.key)" :style="{ width: pct(typeCount(p.key)) }"></div></div>
            <span class="bl-num">{{ typeCount(p.key) }}</span>
          </div>
        </div>
        <div class="panel">
          <div class="panel-h">{{ t.byStatus }}</div>
          <div v-for="s in statuses.filter(x => x.key !== 'all')" :key="s.key" class="bar-line">
            <span class="bl-label">{{ s.label }}</span>
            <div class="bl-track"><div class="bl-fill gray" :style="{ width: pct(statusCount(s.key)) }"></div></div>
            <span class="bl-num">{{ statusCount(s.key) }}</span>
          </div>
        </div>
        <div class="panel">
          <div class="panel-h">{{ t.trendTitle }}</div>
          <svg :viewBox="`0 0 320 ${trendH}`" class="trend" preserveAspectRatio="none">
            <polyline :points="trendPoints.created" fill="none" stroke="var(--cyan)" stroke-width="2" />
            <polyline :points="trendPoints.closed" fill="none" stroke="var(--green)" stroke-width="2" />
            <g v-for="(wk, i) in trend.created" :key="i">
              <rect v-if="i % 2 === 0" :x="i * 26" y="0" width="26" height="trendH" fill="rgba(255,255,255,.03)" />
            </g>
          </svg>
          <div class="legend"><span class="lg cyan"></span>{{ t.monthCreated }}<span class="lg green"></span>{{ t.monthClosed }}</div>
        </div>
      </aside>
    </div>

    <!-- 编辑/详情抽屉 -->
    <div v-if="editor || detail" class="mask" @click.self="closeDrawer">
      <aside class="drawer">
        <header class="drawer-head">
          <h2>{{ editor && !editingId ? '+ ' + t.newProcess : (detail ? detail.id + ' · ' + detail.title : t.edit) }}</h2>
          <button class="x" @click="closeDrawer">×</button>
        </header>
        <div class="drawer-body">
          <!-- 表单 -->
          <template v-if="editor">
            <div class="form-grid">
              <label class="fld">
                <span>{{ t.process }}</span>
                <select v-model="form.type" class="inp">
                  <option v-for="p in types.filter(x => x.key !== 'all')" :key="p.key" :value="p.key">{{ p.label }}</option>
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
                <textarea v-model="form.description" class="area" :placeholder="t.descPlaceholder"></textarea>
              </label>
            </div>
            <div class="drawer-actions">
              <button class="btn green" @click="save">{{ t.submit }}</button>
              <button class="btn ghost" @click="closeDrawer">{{ t.cancel }}</button>
            </div>
          </template>

          <!-- 详情 -->
          <template v-else-if="detail">
            <div class="row"><span>{{ t.process }}：</span><b :class="typeCls(detail.type)">{{ typeLabel(detail.type) }}</b></div>
            <div class="row"><span>{{ t.priority }}：</span><b :class="priCls(detail.priority)">{{ priLabel(detail.priority) }}</b></div>
            <div class="row"><span>{{ t.status }}：</span><b :class="statusCls(detail.status)">{{ statusLabel(detail.status) }}</b></div>
            <div class="row"><span>{{ t.owner }}：</span><b>{{ detail.owner }}</b></div>
            <div class="row"><span>{{ t.createdAt }}：</span><b>{{ fmt(detail.createdAt) }}</b></div>
            <div class="row"><span>{{ t.sla }}：</span><b :class="slaCls(detail)">{{ slaText(detail) }}</b></div>
            <p class="content">{{ detail.description }}</p>

            <!-- 关联知识 -->
            <div class="block">
              <div class="block-h">{{ t.linkedKnowledge }}</div>
              <div v-if="detail.knowledgeLinks?.length" class="links">
                <span v-for="k in detail.knowledgeLinks" :key="k" class="link-chip">📚 {{ k }} <button class="mini" @click="unlink(detail!, k)">×</button></span>
              </div>
              <div class="cite-row">
                <select v-model="linkPick" class="inp">
                  <option value="">—</option>
                  <option v-for="it in knowledgeItems" :key="it.id" :value="it.id">{{ it.title }}</option>
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
                  <div class="node-line"><b>{{ t.nodeApprover }}：</b>{{ node.approver }}</div>
                  <div class="node-line">
                    <span class="badge" :class="nodeCls(node.status)">{{ nodeLabel(node.status) }}</span>
                    <span v-if="node.comment" class="muted small"> · {{ node.comment }}</span>
                  </div>
                  <div v-if="node.status === 'pending' && canApprove(node)" class="node-actions">
                    <input v-model="node.comment" class="inp sm" :placeholder="t.nodeComment" />
                    <button class="btn sm green" @click="approveNode(detail!, i, 'approved')">{{ t.approve }}</button>
                    <button class="btn sm red" @click="approveNode(detail!, i, 'rejected')">{{ t.reject }}</button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 处理日志 -->
            <div class="block">
              <div class="block-h">{{ t.logs }}</div>
              <div v-if="detail.logs?.length" class="logs">
                <div v-for="(l, i) in detail.logs" :key="i" class="log"><span class="muted">{{ fmt(l.at) }}</span> · <b>{{ l.user }}</b>：{{ l.text }}</div>
              </div>
              <div v-else class="muted small">—</div>
              <div class="cite-row">
                <input v-model="logText" class="inp" :placeholder="t.logPlaceholder" @keyup.enter="addLog(detail!)" />
                <button class="btn sm" @click="addLog(detail!)">{{ t.addLog }}</button>
              </div>
            </div>

            <div class="drawer-actions">
              <button v-if="detail.status === 'new' || detail.status === 'progress'" class="btn" @click="advance(detail!)">{{ t.next }}</button>
              <button v-if="['approval','approved','progress'].includes(detail.status)" class="btn green" @click="closeWorkflow(detail!)">{{ t.close }}</button>
              <button v-if="detail.status === 'closed'" class="btn" @click="reopen(detail!)">{{ t.reopen }}</button>
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

type WType = 'incident' | 'problem' | 'change' | 'risk'
type WStatus = 'new' | 'progress' | 'approval' | 'approved' | 'rejected' | 'closed'
type WPriority = 'P1' | 'P2' | 'P3' | 'P4'
type NodeStatus = 'approved' | 'rejected' | 'pending' | 'skipped'

interface WNode { approver: string; status: NodeStatus; comment?: string; at?: string }
interface WLog { user: string; text: string; at: string }
export interface WorkflowItem {
  id: string; type: WType; title: string; description: string; priority: WPriority
  status: WStatus; owner: string; applicant: string; createdAt: string; updatedAt: string
  slaHours: number; riskLevel?: 'high' | 'medium' | 'low'
  approval: WNode[]; logs: WLog[]; knowledgeLinks: string[]
}

const { t: raw } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (raw('workflow') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})
const auth = useAuthStore()
const me = computed(() => auth.user?.username || 'me')

const LS = 'wf_items'
function load(): WorkflowItem[] {
  const seed = seedData()
  try {
    const saved = JSON.parse(localStorage.getItem(LS) || 'null')
    if (saved && Array.isArray(saved) && saved.length) return saved
  } catch {}
  localStorage.setItem(LS, JSON.stringify(seed))
  return seed
}
function persist() { localStorage.setItem(LS, JSON.stringify(items.value)) }

const items = ref<WorkflowItem[]>(load())
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
  return items.value.filter(w => {
    if (fType.value !== 'all' && w.type !== fType.value) return false
    if (fStatus.value !== 'all' && w.status !== fStatus.value) return false
    if (q && !(w.id + w.title + w.owner).toLowerCase().includes(q)) return false
    return true
  })
})

// ---- 统计 ----
const stats = computed(() => {
  const arr = items.value
  const open = arr.filter(w => !['closed', 'rejected'].includes(w.status)).length
  const now = new Date()
  const mc = arr.filter(w => new Date(w.createdAt).getMonth() === now.getMonth() && new Date(w.createdAt).getFullYear() === now.getFullYear()).length
  const mcl = arr.filter(w => w.status === 'closed' && new Date(w.updatedAt).getMonth() === now.getMonth()).length
  const closed = arr.filter(w => w.status === 'closed')
  const avg = closed.length ? closed.reduce((s, w) => s + (new Date(w.updatedAt).getTime() - new Date(w.createdAt).getTime()) / 36e5, 0) / closed.length : 0
  const breached = arr.filter(w => isBreached(w)).length
  return { open, monthCreated: mc, monthClosed: mcl, avgResolve: avg ? avg.toFixed(1) : '—', breachRate: arr.length ? Math.round((breached / arr.length) * 100) : 0 }
})

function typeCount(k: string) { return items.value.filter(w => w.type === k).length }
function statusCount(k: string) { return items.value.filter(w => w.status === k).length }
function pct(n: number) { const max = Math.max(1, ...items.value.map(() => 0), ...types.value.filter(x => x.key !== 'all').map(x => typeCount(x.key)), ...statuses.value.filter(x => x.key !== 'all').map(x => statusCount(x.key))); return Math.round((n / max) * 100) + '%' }

// ---- 趋势（近12周）----
const trend = computed(() => {
  const weeks = 12
  const created: number[] = [], closed: number[] = []
  const now = new Date()
  for (let i = weeks - 1; i >= 0; i--) {
    const start = new Date(now); start.setDate(now.getDate() - i * 7)
    const end = new Date(start); end.setDate(start.getDate() + 7)
    created.push(items.value.filter(w => { const d = new Date(w.createdAt); return d >= start && d < end }).length)
    closed.push(items.value.filter(w => w.status === 'closed' && (() => { const d = new Date(w.updatedAt); return d >= start && d < end })()).length)
  }
  return { created, closed }
})
const trendH = 120
const trendPoints = computed(() => {
  const max = Math.max(1, ...trend.value.created, ...trend.value.closed)
  const mk = (arr: number[]) => arr.map((v, i) => `${i * 26 + 4},${trendH - (v / max) * (trendH - 10) - 4}`).join(' ')
  return { created: mk(trend.value.created), closed: mk(trend.value.closed) }
})

// ---- 抽屉 ----
const editor = ref(false)
const detail = ref<WorkflowItem | null>(null)
const editingId = ref<string | null>(null)
const form = ref<Partial<WorkflowItem>>({ type: 'incident', priority: 'P3', title: '', description: '', owner: '', riskLevel: 'medium' })
const logText = ref('')
const linkPick = ref('')
const knowledgeItems = ref<KnowledgeItem[]>([])
async function loadKnowledge() {
  try { const r = await getKnowledgeItems({ page: 1, page_size: 200 }); knowledgeItems.value = r.items || [] } catch { knowledgeItems.value = [] }
}
onMounted(() => { loadKnowledge() })

function openEditor() { editor.value = true; editingId.value = null; form.value = { type: 'incident', priority: 'P3', title: '', description: '', owner: me.value, riskLevel: 'medium' } }
function openDetail(w: WorkflowItem) { detail.value = w; editor.value = false }
function closeDrawer() { editor.value = false; detail.value = null; editingId.value = null }

function genId(type: WType, existingCount = 0): string {
  const p = { incident: 'INC', problem: 'PRB', change: 'CHG', risk: 'RSK' }[type]
  const n = String(existingCount + 1).padStart(4, '0')
  return `${p}-2026-${n}`
}
function defaultApproval(type: WType): WNode[] {
  if (type === 'change') return [{ approver: '变更委员会', status: 'pending' }, { approver: '运维经理', status: 'pending' }]
  if (type === 'risk') return [{ approver: '安全负责人', status: 'pending' }]
  if (type === 'problem') return [{ approver: '技术专家', status: 'pending' }]
  return [{ approver: '一线主管', status: 'pending' }]
}
function save() {
  if (!form.value.title?.trim()) { alert(t.titlePlaceholder); return }
  const type = form.value.type as WType
  const now = new Date().toISOString()
  const item: WorkflowItem = {
    id: genId(type, items.value.filter(w => w.type === type).length), type, title: form.value.title!, description: form.value.description || '',
    priority: (form.value.priority as WPriority) || 'P3', status: 'new', owner: form.value.owner || me.value,
    applicant: me.value, createdAt: now, updatedAt: now,
    slaHours: { P1: 4, P2: 8, P3: 24, P4: 72 }[form.value.priority as WPriority] || 24,
    riskLevel: type === 'risk' ? (form.value.riskLevel as any) : undefined,
    approval: defaultApproval(type), logs: [{ user: me.value, text: t.new, at: now }], knowledgeLinks: [],
  }
  items.value = [item, ...items.value]
  persist(); closeDrawer()
}

function advance(w: WorkflowItem) {
  if (w.status === 'new') w.status = w.approval.length ? 'approval' : 'progress'
  else if (w.status === 'progress') w.status = 'closed'
  w.updatedAt = new Date().toISOString()
  addLogInternal(w, t.next)
  persist()
}
function closeWorkflow(w: WorkflowItem) { w.status = 'closed'; w.updatedAt = new Date().toISOString(); addLogInternal(w, t.close); persist() }
function reopen(w: WorkflowItem) { w.status = 'progress'; w.updatedAt = new Date().toISOString(); addLogInternal(w, t.reopen); persist() }
function remove(w: WorkflowItem) { if (!confirm(t.confirmDelete)) return; items.value = items.value.filter(x => x.id !== w.id); persist(); detail.value = null }

function canApprove(node: WNode) { return node.status === 'pending' && (node.approver.includes(me.value) || me.value === 'admin') }
function approveNode(w: WorkflowItem, idx: number, result: 'approved' | 'rejected') {
  const node = w.approval[idx]; node.status = result; node.at = new Date().toISOString()
  addLogInternal(w, `${t.approveNode} ${idx + 1}: ${result}`)
  if (result === 'rejected') { w.status = 'rejected' }
  else if (w.approval.every(n => n.status === 'approved')) { w.status = 'progress' }
  w.updatedAt = new Date().toISOString(); persist()
}

function addLogInternal(w: WorkflowItem, text: string) { w.logs = [...w.logs, { user: me.value, text, at: new Date().toISOString() }] }
function addLog(w: WorkflowItem) { const x = logText.value.trim(); if (!x) return; addLogInternal(w, x); logText.value = ''; persist() }

function link(w: WorkflowItem) { if (!linkPick.value) return; w.knowledgeLinks = [...new Set([...w.knowledgeLinks, linkPick.value])]; linkPick.value = ''; persist() }
function unlink(w: WorkflowItem, k: string) { w.knowledgeLinks = w.knowledgeLinks.filter(x => x !== k); persist() }

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
function slaCls(w: WorkflowItem) { return isBreached(w) ? 'bad' : (w.status === 'closed' ? 'good' : '') }

// ---- 样式辅助 ----
function typeCls(k: string) { return { incident: 'cyan', problem: 'amber', change: 'blue', risk: 'red' }[k] || 'gray' }
function typeLabel(k: string) { return ({ incident: t.incident, problem: t.problem, change: t.change, risk: t.risk } as any)[k] || k }
function priCls(p: string) { return { P1: 'bad', P2: 'warn', P3: '', P4: 'muted' }[p] || '' }
function priLabel(p: string) { return ({ P1: t.p1, P2: t.p2, P3: t.p3, P4: t.p4 } as any)[p] || p }
function statusCls(s: string) { return { new: 'gray', progress: 'blue', approval: 'amber', approved: 'green', rejected: 'red', closed: 'gray' }[s] || 'gray' }
function statusLabel(s: string) { return ({ new: t.new, progress: t.progress, approval: t.approval, approved: t.approved, rejected: t.rejected, closed: t.closed } as any)[s] || s }
function nodeCls(s: NodeStatus) { return { approved: 'green', rejected: 'red', pending: 'amber', skipped: 'gray' }[s] || 'gray' }
function nodeLabel(s: NodeStatus) { return ({ approved: t.approved, rejected: t.rejected, pending: t.approval, skipped: t.closed } as any)[s] || s }
function fmt(d?: string) { return d ? new Date(d).toLocaleString() : '—' }

// ---- 种子数据 ----
function seedData(): WorkflowItem[] {
  const now = Date.now()
  const list: WorkflowItem[] = []
  const mk = (o: Partial<WorkflowItem> & { type: WType; title: string; priority: WPriority; status: WStatus; owner: string; agoH: number; slaHours: number; approval: WNode[] }): WorkflowItem => {
    const item: WorkflowItem = {
      id: genId(o.type, list.filter(w => w.type === o.type).length), description: o.description || '', applicant: o.owner, riskLevel: o.riskLevel,
      createdAt: new Date(now - o.agoH * 36e5).toISOString(), updatedAt: new Date(now - (o.agoH / 2) * 36e5).toISOString(),
      knowledgeLinks: o.knowledgeLinks || [], logs: [{ user: o.owner, text: t.new, at: new Date(now - o.agoH * 36e5).toISOString() }],
      ...o,
    }
    list.push(item)
    return item
  }
  return [
    mk({ type: 'incident', title: 'B 区冷机 CH-02 高压报警', priority: 'P1', status: 'progress', owner: '张伟', agoH: 3, slaHours: 4,
      description: 'B 区冷机 CH-02 出水温度异常升高并触发高压报警，已切换至备用冷机。', approval: defaultApproval('incident') }),
    mk({ type: 'incident', title: 'UPS-A 旁路异常', priority: 'P2', status: 'approval', owner: '李娜', agoH: 10, slaHours: 8,
      description: 'UPS-A 模块显示旁路电压偏离，需主管确认是否现场处理。', approval: [{ approver: '一线主管', status: 'pending', comment: '' }, { approver: '运维经理', status: 'pending' }] }),
    mk({ type: 'problem', title: '机房湿度周期性波动根因分析', priority: 'P3', status: 'new', owner: '王强', agoH: 26, slaHours: 24,
      description: '近两周机房相对湿度在 40%~55% 间周期性波动，需定位加湿系统控制逻辑。', approval: defaultApproval('problem') }),
    mk({ type: 'change', title: '核心交换机固件升级', priority: 'P2', status: 'approved', owner: '赵敏', agoH: 50, slaHours: 8,
      description: '对核心交换机执行 9.3.2 固件升级，规避已知 ARP 表项溢出缺陷。', approval: [{ approver: '变更委员会', status: 'approved', comment: '同意窗口期', at: new Date(now - 20 * 36e5).toISOString() }, { approver: '运维经理', status: 'pending' }] }),
    mk({ type: 'risk', title: '市电双路单点隐患', priority: 'P2', status: 'closed', owner: '陈昊', agoH: 200, slaHours: 24, riskLevel: 'high',
      description: '发现 10kV 进线 II 路 PT 柜端子氧化，已安排带电紧固。', approval: [{ approver: '安全负责人', status: 'approved', at: new Date(now - 180 * 36e5).toISOString() }], knowledgeLinks: ['KB-2026-001'] }),
    mk({ type: 'incident', title: '动环采集器离线', priority: 'P3', status: 'closed', owner: '孙磊', agoH: 96, slaHours: 24,
      description: '采集器 COL-07 离线，重启后恢复，原因为网络端口协商异常。', approval: defaultApproval('incident'), knowledgeLinks: ['KB-2026-003'] }),
  ]
}
</script>

<style scoped>
.page { padding: 18px 22px 40px; }
.page-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 16px; }
.page-title { font-size: 20px; font-weight: 700; }
.page-sub { color: var(--muted); font-size: 13px; margin-top: 4px; }
.page-actions { display: flex; gap: 8px; align-items: center; }
.inp { background: var(--panel-2); border: 1px solid var(--line); color: var(--text); border-radius: 8px; padding: 7px 10px; min-width: 160px; }
.inp.sm { min-width: 120px; padding: 5px 8px; }
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 16px; }
.kpi { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px; display: flex; flex-direction: column; }
.kpi-v { font-size: 24px; font-weight: 800; color: var(--cyan); }
.kpi-v.bad { color: #f87171; }
.kpi-l { font-size: 12px; color: var(--muted); margin-top: 4px; }
.filters { display: flex; gap: 18px; flex-wrap: wrap; margin-bottom: 14px; }
.seg { display: flex; gap: 4px; flex-wrap: wrap; }
.seg-btn { background: var(--panel-2); border: 1px solid var(--line); color: var(--muted); padding: 5px 12px; border-radius: 999px; cursor: pointer; font-size: 12px; }
.seg-btn.active { background: var(--cyan); color: #04121a; border-color: var(--cyan); font-weight: 600; }
.layout { display: grid; grid-template-columns: 1fr 320px; gap: 16px; align-items: start; }
.list { display: flex; flex-direction: column; gap: 10px; }
.row-card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; display: flex; align-items: center; gap: 12px; cursor: pointer; transition: border-color .15s; }
.row-card:hover { border-color: var(--cyan); }
.row-id { font-family: monospace; font-size: 12px; color: var(--muted); min-width: 96px; }
.row-main { flex: 1; }
.row-title { font-size: 14px; font-weight: 600; }
.row-sub { font-size: 12px; color: var(--muted); margin-top: 3px; display: flex; align-items: center; gap: 6px; }
.dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.dot.cyan { background: var(--cyan); } .dot.amber { background: #fbbf24; } .dot.blue { background: #38bdf8; } .dot.red { background: #f87171; } .dot.gray { background: var(--line); }
.row-right { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
.sla { font-size: 11px; color: var(--muted); } .sla.bad { color: #f87171; } .sla.good { color: #4ade80; }
.badge { font-size: 11px; padding: 2px 8px; border-radius: 999px; }
.badge.green { background: rgba(34,197,94,.16); color: #4ade80; }
.badge.amber { background: rgba(245,158,11,.16); color: #fbbf24; }
.badge.red { background: rgba(239,68,68,.16); color: #f87171; }
.badge.blue { background: rgba(56,189,248,.16); color: #38bdf8; }
.badge.gray { background: var(--panel-2); color: var(--muted); }
.empty { text-align: center; color: var(--muted); padding: 40px; }
.side { display: flex; flex-direction: column; gap: 12px; position: sticky; top: 16px; }
.panel { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 12px 14px; }
.panel-h { font-size: 13px; font-weight: 600; margin-bottom: 10px; }
.bar-line { display: flex; align-items: center; gap: 8px; margin: 6px 0; font-size: 12px; }
.bl-label { width: 48px; color: var(--muted); }
.bl-track { flex: 1; height: 8px; background: var(--panel-2); border-radius: 6px; overflow: hidden; }
.bl-fill { height: 100%; border-radius: 6px; background: var(--cyan); }
.bl-fill.gray { background: var(--line); } .bl-fill.cyan { background: var(--cyan); } .bl-fill.amber { background: #fbbf24; } .bl-fill.blue { background: #38bdf8; } .bl-fill.red { background: #f87171; }
.bl-num { width: 24px; text-align: right; }
.trend { width: 100%; height: 120px; }
.legend { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--muted); margin-top: 6px; }
.lg { width: 10px; height: 3px; border-radius: 2px; display: inline-block; margin-left: 10px; } .lg.cyan { background: var(--cyan); } .lg.green { background: var(--green); }
.mask { position: fixed; inset: 0; background: rgba(0,0,0,.5); display: flex; justify-content: flex-end; z-index: 50; }
.drawer { width: 480px; max-width: 94vw; background: var(--panel); height: 100%; overflow-y: auto; padding: 18px 20px; }
.drawer-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
.drawer-head h2 { font-size: 16px; }
.x { background: transparent; border: none; color: var(--muted); font-size: 18px; cursor: pointer; }
.row { font-size: 13px; margin: 6px 0; color: var(--muted); }
.row b { color: var(--text); }
.content { font-size: 13px; line-height: 1.7; white-space: pre-wrap; background: var(--panel-2); border-radius: 10px; padding: 12px; margin: 10px 0; }
.block { margin-top: 14px; border-top: 1px solid var(--line); padding-top: 12px; }
.block-h { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.fld { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); }
.fld.wide { grid-column: 1/-1; }
.area { width: 100%; min-height: 80px; background: var(--panel-2); border: 1px solid var(--line); color: var(--text); border-radius: 8px; padding: 10px; resize: vertical; }
.cite-row { display: flex; gap: 8px; margin: 8px 0; }
.links { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.link-chip { font-size: 12px; background: var(--panel-2); border-radius: 8px; padding: 4px 8px; display: flex; align-items: center; gap: 4px; }
.mini { background: none; border: none; color: var(--muted); cursor: pointer; }
.node { display: flex; gap: 10px; margin: 8px 0; }
.node-idx { width: 22px; height: 22px; border-radius: 50%; background: var(--panel-2); display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; }
.node-body { flex: 1; }
.node-line { font-size: 12px; margin: 2px 0; }
.node-actions { display: flex; gap: 6px; margin-top: 4px; }
.logs { display: flex; flex-direction: column; gap: 6px; margin-bottom: 8px; }
.log { font-size: 12px; background: var(--panel-2); border-radius: 8px; padding: 6px 8px; }
.muted { color: var(--muted); } .small { font-size: 11px; }
.drawer-actions { display: flex; gap: 10px; margin-top: 16px; flex-wrap: wrap; }
.btn { border: 1px solid var(--line); background: var(--panel-2); color: var(--text); border-radius: 8px; padding: 7px 12px; cursor: pointer; font-size: 13px; }
.btn.sm { padding: 4px 10px; font-size: 12px; }
.btn.ghost { background: transparent; }
.btn.soft { background: rgba(34,211,238,.12); color: var(--cyan); border-color: transparent; }
.btn.green { background: var(--green); color: #04121a; border-color: var(--green); font-weight: 600; }
.btn.red { background: rgba(239,68,68,.16); color: #f87171; border-color: transparent; }
.bad { color: #f87171; } .warn { color: #fbbf24; } .good { color: #4ade80; }
@media (max-width: 980px) { .layout { grid-template-columns: 1fr; } .side { position: static; } .kpi-row { grid-template-columns: repeat(2, 1fr); } }
</style>
