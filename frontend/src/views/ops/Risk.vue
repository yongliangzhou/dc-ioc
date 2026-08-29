<template>
  <div>
    <div class="view-head">
      <div class="vh-left">
        <h1>{{ tl('nav.risk') }}</h1>
        <span class="sub">{{ tl('风险识别与评估管控') }}</span>
      </div>
      <button class="btn-sm" :disabled="busy" @click="page.reload">
        {{ busy ? tl('刷新中') : tl('刷新') }}
      </button>
    </div>

    <AsyncSection
      :page="page"
      skeleton-variant="skeleton"
      :skeleton-rows="8"
      min-height="320px"
      empty-title="暂无风险"
      empty-desc="后端未返回任何风险项，可先跑一次自动分析识别风险"
      @retry="page.reload"
    >
      <template #empty-actions>
        <button class="btn-sm primary" v-bind="authState('write')" @click="openCreate">
          {{ tl('新建') }}
        </button>
      </template>

      <!-- KPI -->
      <div class="grid cols-auto-sm" v-if="stats">
        <MetricCard
          metric-name="risk-total"
          :label="tl('风险总数')"
          :value="stats.total"
          quality="good"
          :online="true"
        />
        <MetricCard
          metric-name="risk-open"
          :label="tl('未关闭')"
          :value="stats.open"
          :quality="stats.open ? 'uncertain' : 'good'"
          :online="true"
        />
        <MetricCard
          metric-name="risk-mitigated"
          :label="tl('已缓解')"
          :value="stats.mitigated"
          quality="good"
          :online="true"
        />
        <MetricCard
          metric-name="risk-critical"
          :label="tl('高风险')"
          :value="stats.high"
          :quality="stats.high ? 'bad' : 'good'"
          severity="crit"
          :online="true"
        />
        <MetricCard
          metric-name="risk-mid"
          :label="tl('中风险')"
          :value="stats.mid"
          :quality="stats.mid ? 'uncertain' : 'good'"
          severity="warn"
          :online="true"
        />
      </div>

      <!-- ===== 主体: 宽屏左矩阵右列表, 窄屏自动堆叠 ===== -->
      <div class="risk-body">
        <!-- 左: 风险矩阵 P × I -->
        <Panel class="mx-panel">
          <div class="panel-head">
            <h5 class="section-title">{{ tl('风险矩阵') }}（{{ tl('可能性') }} × {{ tl('影响') }}）</h5>
          </div>

          <div class="mx-wrap">
            <div class="mx-axis-y">{{ tl('影响') }} ↑</div>
            <div class="mx-grid">
              <div class="mx-corner"></div>
              <div v-for="p in SCALE" :key="'h' + p" class="mx-head">{{ SCALE_LABEL[p] }}</div>
              <template v-for="row in matrixRows" :key="row.impact">
                <div class="mx-head mx-row-head">{{ SCALE_LABEL[row.impact] }}</div>
                <button
                  v-for="c in row.cells"
                  :key="c.prob"
                  class="mx-cell"
                  :class="[levelClass(c.level), { 'is-empty': !c.count, 'is-sel': isSel(c) }]"
                  :disabled="!c.count"
                  :title="cellTitle(c)"
                  @click="toggleCell(c)"
                >
                  {{ c.count || '·' }}
                </button>
              </template>
            </div>
          </div>
          <div class="mx-axis-x">{{ tl('可能性') }} →</div>

          <div class="mx-legend">
            <span class="lg"><i class="dot lv-low"></i>{{ tl('低') }}</span>
            <span class="lg"><i class="dot lv-mid"></i>{{ tl('中') }}</span>
            <span class="lg"><i class="dot lv-high"></i>{{ tl('高') }}</span>
            <span class="muted sm">{{ tl('格内为风险条数，点击格筛选右侧列表（空格不可点）') }}</span>
          </div>
        </Panel>

        <!-- 右: 风险列表 -->
        <Panel>
          <div class="panel-head">
            <h5 class="section-title">
              {{ tl('风险评估列表') }} ({{ filtered.length }})
            </h5>
            <div class="panel-actions">
              <button class="btn-sm" :disabled="!filtered.length" @click="exportCsv">
                {{ tl('导出 CSV') }}
              </button>
              <button class="btn-sm" v-bind="authState('write')" @click="runAnalyze">
                {{ analyzing ? tl('分析中…') : tl('自动分析') }}
              </button>
              <button class="btn-sm primary" v-bind="authState('write')" @click="openCreate">
                {{ tl('新建') }}
              </button>
            </div>
          </div>

          <!-- 筛选 -->
          <div class="filters">
            <select v-model="fCat" class="ipt f-ipt">
              <option value="">{{ tl('全部类别') }}</option>
              <option v-for="c in catOptions" :key="c" :value="c">{{ c }}</option>
            </select>
            <select v-model="fLevel" class="ipt f-ipt">
              <option value="">{{ tl('全部等级') }}</option>
              <option value="高">{{ tl('高') }}</option>
              <option value="中">{{ tl('中') }}</option>
              <option value="低">{{ tl('低') }}</option>
            </select>
            <select v-model="fStatus" class="ipt f-ipt">
              <option value="">{{ tl('全部状态') }}</option>
              <option value="open">{{ tl('未关闭') }}</option>
              <option value="closed">{{ tl('已缓解') }}</option>
            </select>
            <input
              v-model="kw"
              class="ipt f-ipt grow"
              :placeholder="tl('搜索编号 / 描述 / 责任人')"
            />
            <button v-if="hasFilter" class="btn-sm" @click="clearFilters">{{ tl('清除') }}</button>
          </div>

          <div class="tbl" v-if="filtered.length">
            <div class="tbl-head">
              <button class="col w-code sortable" @click="toggleSort('code')">
                {{ tl('编号') }}{{ sortMark('code') }}
              </button>
              <button class="col w-risk sortable" @click="toggleSort('risk')">
                {{ tl('风险描述') }}{{ sortMark('risk') }}
              </button>
              <button class="col w-cat sortable" @click="toggleSort('cat')">
                {{ tl('类别') }}{{ sortMark('cat') }}
              </button>
              <button class="col w-num sortable" @click="toggleSort('prob')">
                {{ tl('可能性') }}{{ sortMark('prob') }}
              </button>
              <button class="col w-num sortable" @click="toggleSort('impact')">
                {{ tl('影响') }}{{ sortMark('impact') }}
              </button>
              <button class="col w-lv sortable" @click="toggleSort('level')">
                {{ tl('等级') }}{{ sortMark('level') }}
              </button>
              <button class="col w-stat sortable" @click="toggleSort('closed')">
                {{ tl('状态') }}{{ sortMark('closed') }}
              </button>
              <span class="col w-ctrl">{{ tl('缓解措施') }}</span>
              <span class="col w-op">{{ tl('操作') }}</span>
            </div>
            <div v-for="r in paged" :key="r.id" class="tbl-row">
              <span class="col w-code mono">{{ r.code }}</span>
              <span class="col w-risk fw" :title="r.risk">{{ r.risk }}</span>
              <span class="col w-cat muted">{{ r.cat }}</span>
              <span class="col w-num muted">{{ SCALE_LABEL[r.prob] ?? r.prob }}</span>
              <span class="col w-num muted">{{ SCALE_LABEL[r.impact] ?? r.impact }}</span>
              <span class="col w-lv"
                ><span class="pill-tag" :class="levelTag(r)">{{ levelOf(r) }}</span></span
              >
              <span class="col w-stat"
                ><span class="pill-tag" :class="r.closed === 1 ? 'g' : 'a'">{{
                  r.closed === 1 ? tl('已缓解') : tl('未关闭')
                }}</span></span
              >
              <span class="col w-ctrl muted" :title="r.ctrl ?? ''">{{ r.ctrl || '—' }}</span>
              <span class="col w-op p-ops">
                <button class="link" v-bind="authState('write')" @click="openEdit(r)">{{
                  tl('编辑')
                }}</button>
                <button
                  class="link danger"
                  v-bind="authState('write')"
                  @click="remove(r)"
                >
                  {{ tl('删除') }}
                </button>
              </span>
            </div>
          </div>

          <div class="empty" v-else>
            <span class="muted">{{
              hasFilter ? tl('当前筛选条件下无匹配风险') : tl('暂无风险')
            }}</span>
            <button v-if="hasFilter" class="link" @click="clearFilters">{{ tl('清空筛选') }}</button>
          </div>

          <div class="pager" v-if="filtered.length">
            <span class="muted sm">{{ tl('共') }} {{ filtered.length }} {{ tl('条') }}</span>
            <select v-model.number="pageSize" class="ipt pg-ipt">
              <option v-for="s in PAGE_SIZES" :key="s" :value="s">{{ s }}/{{ tl('页') }}</option>
            </select>
            <button class="btn-sm pg-btn" :disabled="pageNo <= 1" @click="pageNo--">
              {{ tl('上一页') }}
            </button>
            <span class="pg-info">{{ pageNo }} / {{ totalPages }}</span>
            <button class="btn-sm pg-btn" :disabled="pageNo >= totalPages" @click="pageNo++">
              {{ tl('下一页') }}
            </button>
          </div>
        </Panel>
      </div>
    </AsyncSection>

    <!-- 风险抽屉 -->
    <div class="drawer-mask" v-if="drawer" @click.self="drawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ form.id ? tl('编辑风险') : tl('新建风险') }}</span>
          <button class="x" @click="drawer = false">✕</button>
        </div>
        <div class="form">
          <label
            >{{ tl('风险描述') }}
            <input v-model.trim="form.risk" class="ipt" :placeholder="tl('如 空调冗余不足')" />
          </label>
          <label
            >{{ tl('类别') }}
            <input v-model.trim="form.cat" class="ipt" :placeholder="tl('如 暖通 / 电力')" />
          </label>
          <div class="row">
            <label
              >{{ tl('可能性') }}
              <select v-model.number="form.prob" class="ipt">
                <option :value="1">{{ tl('低') }}</option>
                <option :value="2">{{ tl('中') }}</option>
                <option :value="3">{{ tl('高') }}</option>
                <option :value="4">{{ tl('极高') }}</option>
              </select>
            </label>
            <label
              >{{ tl('影响') }}
              <select v-model.number="form.impact" class="ipt">
                <option :value="1">{{ tl('低') }}</option>
                <option :value="2">{{ tl('中') }}</option>
                <option :value="3">{{ tl('高') }}</option>
                <option :value="4">{{ tl('极高') }}</option>
              </select>
            </label>
          </div>
          <div class="lv-preview">
            {{ tl('风险等级') }}：<b :class="levelClass(riskLevelOf(form.prob ?? 2, form.impact ?? 2))">{{
              riskLevelOf(form.prob ?? 2, form.impact ?? 2)
            }}</b>
            <span class="muted sm"
              >（{{ tl('可能性') }} {{ form.prob }} × {{ tl('影响') }} {{ form.impact }} =
              {{ (form.prob ?? 2) * (form.impact ?? 2) }}）</span
            >
          </div>
          <label
            >{{ tl('缓解措施') }}
            <textarea v-model.trim="form.ctrl" class="ipt" rows="2"></textarea>
          </label>
          <label
            >{{ tl('责任人') }}
            <input v-model.trim="form.owner" class="ipt" />
          </label>
          <div v-if="err" class="err">{{ err }}</div>
          <div class="drawer-foot">
            <button class="btn-sm" @click="drawer = false">{{ tl('取消') }}</button>
            <button class="btn-sm primary" :disabled="saving" @click="save">
              {{ saving ? tl('保存中…') : tl('保存') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 自动分析结果 -->
    <div class="drawer-mask" v-if="analyzeDrawer" @click.self="analyzeDrawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ tl('自动分析建议') }}</span>
          <button class="x" @click="analyzeDrawer = false">✕</button>
        </div>
        <div class="empty" v-if="!suggestions.length">{{ tl('暂无建议') }}</div>
        <div class="sug-list" v-else>
          <div v-for="(s, i) in suggestions" :key="i" class="sug">
            <div class="sug-main">
              <span
                class="pill-tag"
                :class="s.level === '高' ? 'r' : s.level === '中' ? 'a' : 'g'"
                >{{ s.level }}</span
              >
              <span class="sug-title">{{ s.risk }}</span>
            </div>
            <div class="sug-meta muted">P{{ s.prob }} × I{{ s.impact }} · {{ s.ctrl }}</div>
            <button class="btn-sm primary sm" @click="acceptSuggestion(s)">
              {{ tl('采纳入库') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { useAsyncPage, toErrorMessage } from '@/composables/useAsyncPage'
import { downloadCsv, stampedName } from '@/utils/export'
import {
  getRiskOverview,
  createRisk,
  updateRisk,
  deleteRisk,
  analyzeRisk,
  riskLevelOf,
  type RiskView,
  type RiskOverview,
  type RiskCreate,
} from '@/api/risk'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { usePermission, type PermAction } from '@/hooks/usePermission'

const toast = useToast()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

/* ------------------------------------------------------------------ */
/* 数据源：一次请求拿 列表 + 统计                                       */
/* ------------------------------------------------------------------ */
const page = useAsyncPage<RiskOverview>(() => getRiskOverview())
const { busy } = page
const risks = computed<RiskView[]>(() => page.data.value?.risks ?? [])
const stats = computed(() => page.data.value?.stats ?? null)

/* ------------------------------------------------------------------ */
/* 风险矩阵（可能性 × 影响）                                            */
/* ------------------------------------------------------------------ */
const SCALE = [1, 2, 3, 4] as const
/** 渲染顺序：影响从高到低（上 → 下），符合风险矩阵惯例 */
const IMPACT_DESC = [4, 3, 2, 1] as const
const SCALE_LABEL: Record<number, string> = { 1: tl('低'), 2: tl('中'), 3: tl('高'), 4: tl('极高') }

const matrixRows = computed(() =>
  IMPACT_DESC.map((impact) => ({
    impact,
    cells: SCALE.map((prob) => ({
      prob,
      impact,
      level: riskLevelOf(prob, impact),
      count: risks.value.filter((r) => r.prob === prob && r.impact === impact).length,
    })),
  })),
)

/**
 * 等级字面量：后端 crud/risk.py 固定返回中文「高 / 中 / 低」，
 * 比较时一律用字面量，不能用 tl() —— 否则切到非中文 locale 会全部误判为"低"。
 * tl() 只用于展示文案。
 */
const LV = { HIGH: '高', MID: '中', LOW: '低' } as const

function levelClass(lv: string): string {
  return lv === LV.HIGH ? 'lv-high' : lv === LV.MID ? 'lv-mid' : 'lv-low'
}
function levelOf(r: RiskView): string {
  return riskLevelOf(r.prob, r.impact)
}
function levelTag(r: RiskView): string {
  const lv = levelOf(r)
  return lv === LV.HIGH ? 'r' : lv === LV.MID ? 'a' : 'g'
}
function cellTitle(c: { prob: number; impact: number; count: number }): string {
  const base = `${tl('可能性')} ${SCALE_LABEL[c.prob]} × ${tl('影响')} ${SCALE_LABEL[c.impact]}`
  if (!c.count) return `${base}：${tl('无风险')}`
  // 列出该格内具体风险项（最多 5 条 + 余量），让矩阵不仅能看数量还能直接定位风险
  const names = risks.value
    .filter((r) => r.prob === c.prob && r.impact === c.impact)
    .map((r) => r.risk)
    .slice(0, 5)
  const tail = c.count > names.length ? ` 等 ${c.count} 条` : ''
  return `${base}：${names.join('、')}${tail}`
}

/** 选中的矩阵格 → 筛选列表；空格不可点 */
const selCell = ref<{ prob: number; impact: number } | null>(null)
function isSel(c: { prob: number; impact: number }): boolean {
  return selCell.value?.prob === c.prob && selCell.value?.impact === c.impact
}
function toggleCell(c: { prob: number; impact: number; count: number }) {
  if (!c.count) return
  selCell.value = isSel(c) ? null : { prob: c.prob, impact: c.impact }
}

/* ------------------------------------------------------------------ */
/* 筛选 + 排序                                                          */
/* ------------------------------------------------------------------ */
const fCat = ref('')
const fLevel = ref('')
const fStatus = ref('')
const kw = ref('')

const catOptions = computed(() =>
  Array.from(new Set(risks.value.map((r) => r.cat).filter(Boolean))).sort(),
)
const hasFilter = computed(
  () => !!(selCell.value || fCat.value || fLevel.value || fStatus.value || kw.value.trim()),
)
function clearFilters() {
  selCell.value = null
  fCat.value = ''
  fLevel.value = ''
  fStatus.value = ''
  kw.value = ''
}

type SortKey = 'code' | 'risk' | 'cat' | 'prob' | 'impact' | 'level' | 'closed'
const sortKey = ref<SortKey>('level')
const sortDir = ref<'asc' | 'desc'>('desc')

function toggleSort(k: SortKey) {
  if (sortKey.value === k) sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  else {
    sortKey.value = k
    sortDir.value = 'asc'
  }
}
function sortMark(k: SortKey): string {
  return sortKey.value === k ? (sortDir.value === 'asc' ? ' ↑' : ' ↓') : ''
}

const LEVEL_RANK: Record<string, number> = { [LV.HIGH]: 3, [LV.MID]: 2, [LV.LOW]: 1 }

const filtered = computed(() => {
  let list = risks.value

  if (selCell.value) {
    const { prob, impact } = selCell.value
    list = list.filter((r) => r.prob === prob && r.impact === impact)
  }
  if (fCat.value) list = list.filter((r) => r.cat === fCat.value)
  if (fLevel.value) list = list.filter((r) => levelOf(r) === fLevel.value)
  if (fStatus.value) {
    list = list.filter((r) => (fStatus.value === 'open' ? r.closed !== 1 : r.closed === 1))
  }
  const q = kw.value.trim().toLowerCase()
  if (q) {
    list = list.filter((r) =>
      `${r.code} ${r.risk} ${r.cat} ${r.owner} ${r.ctrl ?? ''}`.toLowerCase().includes(q),
    )
  }

  const dir = sortDir.value === 'asc' ? 1 : -1
  const rank = (r: RiskView) => LEVEL_RANK[levelOf(r)] ?? 0
  return [...list].sort((a, b) => {
    let x: string | number
    let y: string | number
    switch (sortKey.value) {
      case 'code':
        x = a.code
        y = b.code
        break
      case 'risk':
        x = a.risk
        y = b.risk
        break
      case 'cat':
        x = a.cat
        y = b.cat
        break
      case 'prob':
        x = a.prob
        y = b.prob
        break
      case 'impact':
        x = a.impact
        y = b.impact
        break
      case 'closed':
        x = a.closed
        y = b.closed
        break
      default:
        x = rank(a)
        y = rank(b)
    }
    if (typeof x === 'string' || typeof y === 'string') {
      return String(x).localeCompare(String(y), 'zh-CN') * dir
    }
    return (x - y) * dir
  })
})

/* ------------------------------------------------------------------ */
/* 分页                                                                */
/* ------------------------------------------------------------------ */
const PAGE_SIZES = [10, 20, 50]
const pageSize = ref(10)
const pageNo = ref(1)

/** 任一筛选项变化 → 回到第 1 页，避免停留在已无数据的页码 */
watch([selCell, fCat, fLevel, fStatus, kw], () => {
  pageNo.value = 1
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filtered.value.length / pageSize.value)),
)
const paged = computed(() => {
  const start = (pageNo.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

/** 筛选结果变少（如删除末页数据）时，把越界页码拉回有效范围 */
watch(filtered, () => {
  if (pageNo.value > totalPages.value) pageNo.value = totalPages.value
})

/* ------------------------------------------------------------------ */
/* 导出                                                                */
/* ------------------------------------------------------------------ */
const EXPORT_HEADERS = [
  tl('编号'),
  tl('风险描述'),
  tl('类别'),
  tl('可能性'),
  tl('影响'),
  tl('等级'),
  tl('状态'),
  tl('缓解措施'),
  tl('责任人'),
]
function exportCsv() {
  const rows = filtered.value.map((r) => [
    r.code,
    r.risk,
    r.cat,
    SCALE_LABEL[r.prob] ?? r.prob,
    SCALE_LABEL[r.impact] ?? r.impact,
    levelOf(r),
    r.closed === 1 ? tl('已缓解') : tl('未关闭'),
    r.ctrl ?? '',
    r.owner,
  ])
  downloadCsv(stampedName('风险清单'), EXPORT_HEADERS, rows)
  toast.success(`${tl('已导出')} ${rows.length} ${tl('条')}`)
}

/* ------------------------------------------------------------------ */
/* 抽屉                                                                */
/* ------------------------------------------------------------------ */
const drawer = ref(false)
const saving = ref(false)
const err = ref('')
const form = ref<Partial<RiskView> & RiskCreate>({
  risk: '',
  cat: '',
  prob: 2,
  impact: 2,
  ctrl: '',
  owner: '',
})

function openCreate() {
  form.value = { risk: '', cat: '', prob: 2, impact: 2, ctrl: '', owner: '' }
  err.value = ''
  drawer.value = true
}
function openEdit(r: RiskView) {
  // 字段名严格对齐后端 crud/risk.py 的返回：risk / cat / prob / impact / ctrl / owner
  form.value = {
    id: r.id,
    risk: r.risk,
    cat: r.cat,
    prob: r.prob,
    impact: r.impact,
    ctrl: r.ctrl ?? '',
    owner: r.owner,
  }
  err.value = ''
  drawer.value = true
}
async function save() {
  const f = form.value
  if (!f.risk) {
    err.value = tl('风险描述为必填')
    return
  }
  saving.value = true
  err.value = ''
  try {
    const payload: RiskCreate = {
      risk: f.risk,
      cat: f.cat || '',
      prob: f.prob ?? 2,
      impact: f.impact ?? 2,
      ctrl: f.ctrl || '',
      owner: f.owner || '',
    }
    if (f.id != null) await updateRisk(f.id, payload)
    else await createRisk(payload)
    drawer.value = false
    await page.reload()
    toast.success(tl('已保存'))
  } catch (ex: unknown) {
    err.value = toErrorMessage(ex) || tl('保存失败')
  } finally {
    saving.value = false
  }
}
async function remove(r: RiskView) {
  const ok = await useConfirm({
    title: tl('删除风险'),
    message: `${tl('确认删除风险')} ${r.code}?`,
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => {
      await deleteRisk(r.id)
    },
  })
  if (ok) {
    await page.reload()
    toast.success(tl('已删除'))
  }
}

/* ------------------------------------------------------------------ */
/* 自动分析                                                            */
/* ------------------------------------------------------------------ */
const analyzeDrawer = ref(false)
const analyzing = ref(false)
const suggestions = ref<
  { risk: string; cat: string; prob: number; impact: number; level: string; ctrl: string; owner: string }[]
>([])

async function runAnalyze() {
  analyzing.value = true
  try {
    const res = await analyzeRisk()
    suggestions.value = (res as { suggestions?: typeof suggestions.value }).suggestions ?? []
    analyzeDrawer.value = true
  } catch (ex: unknown) {
    // 分析失败不能只写进一个页面底部变量，必须让用户看见
    toast.error(`${tl('分析失败')}：${toErrorMessage(ex)}`)
  } finally {
    analyzing.value = false
  }
}
async function acceptSuggestion(s: (typeof suggestions.value)[number]) {
  try {
    await createRisk({
      risk: s.risk,
      cat: s.cat,
      prob: s.prob,
      impact: s.impact,
      ctrl: s.ctrl,
      owner: s.owner,
    })
    suggestions.value = suggestions.value.filter((x) => x !== s)
    await page.reload()
    toast.success(tl('已采纳入库'))
  } catch (ex: unknown) {
    toast.error(`${tl('入库失败')}：${toErrorMessage(ex)}`)
  }
}
</script>

<style scoped>
.view-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}
.vh-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

/* ===== 主体: 宽屏左右, 1280 以下堆叠 ===== */
.risk-body {
  display: grid;
  grid-template-columns: minmax(340px, 400px) 1fr;
  gap: 12px;
  align-items: start;
  margin-top: 4px;
}

/* ===== 风险矩阵 ===== */
.mx-panel {
  padding-bottom: 10px;
}
.mx-wrap {
  display: flex;
  gap: 6px;
  align-items: stretch;
}
.mx-axis-y {
  writing-mode: vertical-rl;
  font-size: 11px;
  color: var(--muted);
  text-align: center;
  padding: 2px 0;
  letter-spacing: 2px;
}
.mx-axis-x {
  font-size: 11px;
  color: var(--muted);
  text-align: center;
  letter-spacing: 2px;
  margin-top: 4px;
}
.mx-grid {
  flex: 1;
  min-width: 0;
  display: grid;
  grid-template-columns: 34px repeat(4, 1fr);
  gap: 4px;
}
.mx-head {
  font-size: 10.5px;
  color: var(--muted);
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
}
.mx-row-head {
  justify-content: flex-end;
  padding-right: 4px;
}
.mx-cell {
  aspect-ratio: 1 / 1;
  min-height: 40px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg2);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition:
    transform 0.12s,
    box-shadow 0.12s,
    opacity 0.12s;
  font-variant-numeric: tabular-nums;
}
.mx-cell:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}
.mx-cell.is-sel {
  outline: 2px solid var(--blue);
  outline-offset: 1px;
}
/* 空格: 置灰且不可点 */
.mx-cell.is-empty {
  background: transparent;
  border-style: dashed;
  color: var(--muted);
  font-weight: 400;
  cursor: default;
  opacity: 0.5;
}
.lv-low {
  background: rgba(82, 196, 26, 0.14);
  color: var(--green);
  border-color: rgba(82, 196, 26, 0.3);
}
.lv-mid {
  background: rgba(250, 173, 20, 0.14);
  color: var(--amber);
  border-color: rgba(250, 173, 20, 0.3);
}
.lv-high {
  background: rgba(255, 77, 79, 0.16);
  color: var(--red);
  border-color: rgba(255, 77, 79, 0.35);
}
.mx-legend {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 8px;
}
.lg {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  color: var(--text2);
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  border: 1px solid var(--border);
}

/* ===== 列表 ===== */
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.panel-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.f-ipt {
  min-width: 110px;
  padding: 5px 9px;
  font-size: 12px;
}
.f-ipt.grow {
  flex: 1 1 160px;
  min-width: 0;
}
.tbl {
  max-height: 460px;
  overflow-y: auto;
}
.tbl-head,
.tbl-row {
  display: flex;
  align-items: center;
  padding: 9px 6px;
  font-size: 12.5px;
  gap: 6px;
}
.tbl-head {
  font-weight: 600;
  color: var(--muted);
  border-bottom: 2px solid var(--border);
  font-size: 12px;
}
.tbl-row {
  border-bottom: 1px solid var(--border-light, rgba(255, 255, 255, 0.04));
}
.tbl-row:hover {
  background: rgba(255, 255, 255, 0.02);
}
.col {
  flex-shrink: 0;
  min-width: 0;
}
.w-code {
  width: 88px;
}
.w-risk {
  flex: 1 1 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.w-cat {
  width: 74px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.w-num {
  width: 50px;
  text-align: center;
}
.w-lv {
  width: 52px;
  text-align: center;
}
.w-stat {
  width: 66px;
  text-align: center;
}
.w-ctrl {
  width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.w-op {
  width: 88px;
}
.sortable {
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
  text-align: left;
  display: inline-flex;
  align-items: center;
}
.sortable:hover {
  color: var(--blue);
}
.w-num.sortable,
.w-lv.sortable,
.w-stat.sortable {
  justify-content: center;
}
.p-ops {
  display: flex;
  gap: 8px;
}

/* ===== 通用 ===== */
.btn-sm {
  padding: 5px 12px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--bg2);
  color: var(--text2);
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
}
.btn-sm.primary {
  background: var(--blue);
  color: #fff;
  border-color: var(--blue);
  font-weight: 600;
}
.btn-sm.sm {
  padding: 3px 10px;
  font-size: 11px;
}
.btn-sm:disabled {
  opacity: 0.6;
  cursor: default;
}
.link {
  background: none;
  border: none;
  color: var(--blue);
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}
.link.danger {
  color: var(--red);
}
.mono {
  font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;
  font-size: 11.5px;
}
.fw {
  font-weight: 500;
}
.muted {
  color: var(--muted);
}
.sm {
  font-size: 11px;
}
.pill-tag {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 9px;
  background: var(--bg2);
  white-space: nowrap;
}
.pill-tag.g {
  background: rgba(82, 196, 26, 0.12);
  color: var(--green);
}
.pill-tag.a {
  background: rgba(250, 173, 20, 0.12);
  color: var(--amber);
}
.pill-tag.r {
  background: rgba(255, 77, 79, 0.12);
  color: var(--red);
}
.empty {
  text-align: center;
  padding: 32px;
  color: var(--muted);
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

/* ===== 分页 ===== */
.pager {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-light, rgba(255, 255, 255, 0.04));
}
.pg-ipt {
  min-width: 84px;
  padding: 4px 8px;
  font-size: 12px;
}
.pg-btn {
  min-width: 64px;
}
.pg-info {
  font-size: 12px;
  color: var(--text2);
  font-variant-numeric: tabular-nums;
  min-width: 48px;
  text-align: center;
}

/* ===== 抽屉 ===== */
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(6, 11, 20, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6vh 16px;
  z-index: 40;
}
.drawer {
  width: 420px;
  max-width: 92vw;
  background: var(--card-bg);
  height: 100%;
  padding: 18px;
  overflow: auto;
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.3);
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 14px;
}
.x {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--text2);
}
.row {
  display: flex;
  gap: 10px;
}
.row label {
  flex: 1;
}
.ipt {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 7px 9px;
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
}
.lv-preview {
  font-size: 12px;
  color: var(--text2);
  padding: 7px 10px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--bg2);
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.err {
  color: var(--red);
  font-size: 12px;
}
.drawer-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}
.sug-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sug {
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.sug-main {
  display: flex;
  gap: 8px;
  align-items: center;
}
.sug-title {
  font-size: 13px;
  font-weight: 500;
}
.sug-meta {
  font-size: 11px;
}

/* ===== 响应式 ===== */
@media (max-width: 1280px) {
  .risk-body {
    grid-template-columns: 1fr;
  }
  .mx-panel {
    max-width: none;
  }
}
@media (max-width: 760px) {
  .view-head {
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }
  .tbl-head,
  .tbl-row {
    flex-wrap: wrap;
    gap: 4px;
  }
  .w-ctrl {
    display: none;
  }
  .w-risk {
    flex: 1 1 100%;
    white-space: normal;
  }
  .filters {
    flex-direction: column;
  }
  .f-ipt {
    width: 100%;
  }
  .mx-axis-y {
    writing-mode: horizontal-tb;
    letter-spacing: 0;
    font-size: 10px;
  }
}
</style>
