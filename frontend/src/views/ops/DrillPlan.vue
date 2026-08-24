<template>
  <div class="page-wrap">
    <div class="view-head">
      <div class="vh-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M4 5h16M4 12h16M4 19h10" stroke-linecap="round"/><circle cx="19" cy="19" r="2"/>
        </svg>
      </div>
      <div>
        <h1>{{ t.title }}</h1>
        <div class="sub">{{ t.sub }}</div>
      </div>
      <div class="vh-right">
        <button class="btn-primary" @click="openCreate">{{ t.newPlan }}</button>
      </div>
    </div>

    <!-- 统计卡 -->
    <div class="grid cols-4">
      <div class="card" style="padding:14px;text-align:center">
        <div class="text-2xl font-bold" style="color:var(--txt-strong)">{{ stats.year }}</div>
        <div class="text-xs mt-1" style="color:var(--txt2)">{{ t.total }}</div>
      </div>
      <div class="card" style="padding:14px;text-align:center">
        <div class="text-2xl font-bold" style="color:var(--green)">{{ stats.done }}</div>
        <div class="text-xs mt-1" style="color:var(--txt2)">{{ t.done }}</div>
      </div>
      <div class="card" style="padding:14px;text-align:center">
        <div class="text-2xl font-bold" style="color:var(--blue)">{{ stats.pass }}</div>
        <div class="text-xs mt-1" style="color:var(--txt2)">{{ t.passed }}</div>
      </div>
      <div class="card" style="padding:14px;text-align:center">
        <div class="text-xs font-semibold mt-1" style="color:var(--txt2)">{{ t.next }}</div>
        <div class="text-sm mt-1 truncate" style="color:var(--txt-strong)">{{ stats.next }}</div>
      </div>
    </div>

    <!-- 演练模板 -->
    <div class="card">
      <div class="card-head">
        <div class="card-title">{{ t.plans }}</div>
        <input v-model="kw" @input="debouncedLoad" :placeholder="t.search || '搜索'" class="inp" style="width:200px" />
      </div>
      <div class="table-wrap">
        <table class="w-full">
          <thead>
            <tr>
              <th>{{ t.type }}</th>
              <th>{{ t.plans }}</th>
              <th>{{ t.level }}</th>
              <th>{{ t.scope }}</th>
              <th>{{ t.estDuration }}</th>
              <th>{{ t.steps }}</th>
              <th>状态</th>
              <th>{{ t.result }}</th>
              <th style="width:112px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in plans" :key="p.id">
              <td><span class="tag b">{{ p.type }}</span></td>
              <td class="cell-strong">
                {{ p.name }}
                <span v-if="p.source === 'real'" class="pill g" style="margin-left:4px">{{ t.suggest || '建议' }}</span>
              </td>
              <td>{{ p.level || '—' }}</td>
              <td>{{ p.scope || '—' }}</td>
              <td>{{ p.duration ? p.duration + 'min' : '—' }}</td>
              <td>{{ (p.steps || []).length }}</td>
              <td><span class="tag" :class="stateClass(p.state)">{{ p.state }}</span></td>
              <td><span class="tag" :class="resultClass(p.result)">{{ p.result }}</span></td>
              <td>
                <div class="flex gap-1">
                  <button class="btn-sm btn-primary" @click="openPreview(p)">{{ t.preview || '演练预演' }}</button>
                  <button class="btn-sm" @click="openEdit(p)">{{ t.edit }}</button>
                  <button class="btn-sm btn-danger" @click="remove(p)">{{ t.del }}</button>
                </div>
              </td>
            </tr>
            <tr v-if="!plans.length"><td colspan="9" class="empty-box">{{ t.empty }}</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 执行记录 -->
    <div class="card">
      <div class="card-head">
        <div class="card-title">{{ t.logs }}</div>
        <div class="flex gap-2 items-center">
          <select v-model="recFilter" @change="loadRecords" class="inp" style="width:180px">
            <option :value="null">{{ t.allPlan || '全部模板' }}</option>
            <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
          <button class="btn-ghost" @click="openRecord">{{ t.startDrill }}</button>
        </div>
      </div>
      <div class="table-wrap">
        <table class="w-full">
          <thead>
            <tr>
              <th>{{ t.colPlan }}</th>
              <th>{{ t.colDate }}</th>
              <th>{{ t.colOwner }}</th>
              <th>{{ t.colDuration }}</th>
              <th>{{ t.colResult }}</th>
              <th>{{ t.colScore }}</th>
              <th>{{ t.colNote }}</th>
              <th style="width:96px"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in records" :key="r.id">
              <td class="cell-strong">{{ planName(r.planId) }}</td>
              <td>{{ r.date }}</td>
              <td>{{ r.participants }} 人</td>
              <td>{{ r.startAt }}-{{ r.endAt }}</td>
              <td><span class="tag" :class="resultClass(r.result)">{{ r.result }}</span></td>
              <td>{{ r.score }}</td>
              <td class="clip">{{ r.note }}</td>
              <td>
                <div class="flex gap-1">
                  <button class="btn-sm" @click="openRecordEdit(r)">{{ t.edit }}</button>
                  <button class="btn-sm btn-danger" @click="removeRecord(r)">{{ t.del }}</button>
                </div>
              </td>
            </tr>
            <tr v-if="!records.length"><td colspan="8" class="empty-box">{{ t.empty }}</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 计划 编辑抽屉 -->
    <div v-if="showPlan" class="modal-mask" @click.self="showPlan = false">
      <div class="modal">
        <h3>{{ editing ? t.editPlan : t.newPlan }}</h3>
        <div class="space-y">
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>{{ t.plans }}</span><input v-model="form.name" class="inp" placeholder="科目名称" /></div>
            <div class="field"><span>{{ t.type }}</span>
              <select v-model="form.type" class="inp">
                <option>电力</option><option>暖通</option><option>消防</option><option>安防</option><option>网络</option>
              </select>
            </div>
          </div>
          <div class="grid grid-cols-3" style="gap:12px">
            <div class="field"><span>{{ t.level }}</span>
              <select v-model="form.level" class="inp">
                <option>一级</option><option>二级</option><option>三级</option><option>四级</option><option>—</option>
              </select>
            </div>
            <div class="field"><span>{{ t.scope }}</span><input v-model="form.scope" class="inp" placeholder="如 全园区供电" /></div>
            <div class="field"><span>{{ t.estDuration }}</span><input v-model.number="form.duration" type="number" class="inp" placeholder="分钟" /></div>
          </div>
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>计划日期</span><input v-model="form.date" class="inp" placeholder="YYYY-MM-DD" /></div>
            <div class="field"><span>状态</span>
              <select v-model="form.state" class="inp">
                <option>计划中</option><option>已编排</option><option>已完成</option>
              </select>
            </div>
          </div>
          <div class="field"><span>{{ t.steps }}</span>
            <div class="space-y-2">
              <div v-for="(s, i) in form.steps" :key="i" class="flex gap-2 items-center">
                <input v-model="s.title" class="inp flex-1" placeholder="步骤名称" />
                <input v-model.number="s.minutes" type="number" class="inp" style="width:64px" placeholder="分" />
                <input v-model="s.desc" class="inp flex-1" placeholder="说明" />
                <button class="btn-danger" style="padding:6px 10px" @click="form.steps.splice(i, 1)">×</button>
              </div>
              <button class="btn-ghost" style="padding:6px 12px" @click="form.steps.push({ title: '', minutes: 0, desc: '' })">+ {{ t.addStep || '添加步骤' }}</button>
            </div>
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn-ghost" @click="showPlan = false">{{ t.cancel || '取消' }}</button>
          <button class="btn-primary" @click="savePlan" :disabled="saving">{{ saving ? '...' : t.save || '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 执行记录 编辑抽屉 -->
    <div v-if="showRecord" class="modal-mask" @click.self="showRecord = false">
      <div class="modal" style="max-width:480px">
        <h3>{{ t.startDrill }}</h3>
        <div class="space-y">
          <div class="field"><span>{{ t.colPlan }}</span>
            <select v-model="recForm.planId" class="inp">
              <option v-for="p in plans" :key="p.id" :value="p.id">{{ p.name }}</option>
            </select>
          </div>
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>{{ t.colDate }}</span><input v-model="recForm.date" class="inp" placeholder="YYYY-MM-DD" /></div>
            <div class="field"><span>{{ t.colOwner }}</span><input v-model.number="recForm.participants" type="number" class="inp" placeholder="人数" /></div>
          </div>
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>开始</span><input v-model="recForm.startAt" class="inp" placeholder="HH:mm" /></div>
            <div class="field"><span>结束</span><input v-model="recForm.endAt" class="inp" placeholder="HH:mm" /></div>
          </div>
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>{{ t.colScore }}</span><input v-model.number="recForm.score" type="number" class="inp" placeholder="0-100" /></div>
            <div class="field"><span>{{ t.colResult }}</span>
              <select v-model="recForm.result" class="inp">
                <option>通过</option><option>未通过</option><option>—</option>
              </select>
            </div>
          </div>
          <div class="field"><span>{{ t.colNote }}</span><input v-model="recForm.note" class="inp" /></div>
        </div>
        <div class="modal-actions">
          <button class="btn-ghost" @click="showRecord = false">{{ t.cancel || '取消' }}</button>
          <button class="btn-primary" @click="saveRecord" :disabled="saving">{{ saving ? '...' : t.save || '保存' }}</button>
        </div>
      </div>
    </div>

    <!-- 演练预演 - 链路影响联动 -->
    <div v-if="showPreview" class="modal-mask" @click.self="showPreview = false">
      <div class="modal" style="max-width:680px">
        <h3>{{ t.previewTitle }}</h3>
        <div class="text-xs mb-3" style="color:var(--txt2)">
          {{ t.previewFromDrill }}: <b style="color:var(--txt-strong)">{{ previewPlan?.name }}</b>
          <span class="pill b" style="margin-left:8px">{{ previewPlan?.type }}</span>
          <span class="pill" style="margin-left:4px">{{ previewPlan?.scope }}</span>
        </div>

        <div v-if="previewLoading" class="loading-box"><div class="spinner"></div><span>{{ t.analyzing || '分析中…' }}</span></div>
        <div v-else-if="previewError" class="result bad"><span class="r-ic">!</span>{{ previewError }}</div>
        <div v-else-if="previewRes" class="space-y">
          <div class="grid cols-3">
            <div class="card" style="padding:12px;text-align:center;border-color:rgba(255,77,94,.4)">
              <div class="text-xl font-bold" style="color:var(--red)">{{ previewRes.summary?.severity ?? '—' }}</div>
              <div class="text-xs mt-1" style="color:var(--txt2)">{{ t.sevLevel || '严重级别' }}</div>
            </div>
            <div class="card" style="padding:12px;text-align:center;border-color:rgba(255,176,32,.4)">
              <div class="text-xl font-bold" style="color:var(--amber)">{{ previewRes.summary?.affectedCount ?? '—' }}</div>
              <div class="text-xs mt-1" style="color:var(--txt2)">{{ t.affectedNodes || '受影响节点' }}</div>
            </div>
            <div class="card" style="padding:12px;text-align:center;border-color:rgba(139,92,246,.4)">
              <div class="text-xl font-bold" style="color:var(--blue)">{{ previewRes.summary?.criticalPaths ?? '—' }}</div>
              <div class="text-xs mt-1" style="color:var(--txt2)">{{ t.criticalPaths || '关键链路' }}</div>
            </div>
          </div>

          <div v-if="(previewRes.businesses || []).length" class="card" style="padding:12px">
            <div class="text-xs mb-2" style="color:var(--txt2)">{{ t.affectedBiz || '受影响业务域' }}</div>
            <div class="space-y-1">
              <div v-for="b in previewRes.businesses" :key="b.business" class="flex items-center justify-between text-sm">
                <span style="color:var(--txt)">{{ b.business }} <span style="color:var(--txt3)">(SLA {{ b.sla }})</span></span>
                <span class="tag" :class="b.severity === 'critical' ? 'r' : 'a'">{{ b.severity }}</span>
              </div>
            </div>
          </div>

          <div v-if="(previewRes.mitigations || []).length" class="card" style="padding:12px">
            <div class="text-xs mb-2" style="color:var(--txt2)">{{ t.suggestActions || '建议处置措施' }}</div>
            <div class="space-y-1">
              <div v-for="m in previewRes.mitigations.slice(0, 5)" :key="m.seq" class="flex items-start gap-2 text-sm" style="color:var(--txt)">
                <span class="prio" :class="'p-' + m.priority">{{ m.priority }}</span>
                <span>{{ m.action }} · {{ m.target }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-ghost" @click="showPreview = false">{{ t.previewClose }}</button>
          <button class="btn-primary" @click="runPreview" :disabled="previewLoading">{{ t.previewRun }}</button>
        </div>
      </div>
    </div>

    <div v-if="offline" class="result bad" style="margin-top:8px"><span class="r-ic">!</span>{{ t.offlineMsg || '后端不可达, 已使用离线模拟数据 (刷新后端后重试)。' }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getDrills, createDrill, updateDrill, deleteDrill, getDrillRecords, createDrillRecord, updateDrillRecord, deleteDrillRecord, getFaultSources, analyzeFaultImpact } from '@/api'
import type { DrillPlan, DrillRecord, DrillStep, FaultImpactResp, FaultSourceNode } from '@/types'

const { t: raw } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (raw('drillPlan') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})

const stats = reactive({ year: 0, done: 0, pass: 0, next: '—' })
const plans = ref<DrillPlan[]>([])
const records = ref<DrillRecord[]>([])
const kw = ref('')
const offline = ref(false)
const saving = ref(false)
const recFilter = ref<number | null>(null)

let loadTimer: any = null
function debouncedLoad() {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(loadPlans, 300)
}

// ---- 演练预演联动 (演练 -> 故障影响分析) ----
const showPreview = ref(false)
const previewPlan = ref<DrillPlan | null>(null)
const previewLoading = ref(false)
const previewError = ref('')
const previewRes = ref<FaultImpactResp | null>(null)
const _DRILL_TYPE_CATS: Record<string, string[]> = {
  电力: ['hv_incomer', 'transformer', 'ups', 'lv_feeder', 'bus_tie', 'ats'],
  暖通: ['chiller', 'crac', 'cooling_tower', 'chw_pump', 'hex', 'sec_pump'],
  网络: ['switch', 'router', 'core_switch'],
  消防: ['fcu', 'sec_pump'],
}

function mapDrillToFaults(drill: DrillPlan, sources: FaultSourceNode[]): number[] {
  const type = (drill.type || '').trim()
  const cats = _DRILL_TYPE_CATS[type] || []
  // 宽松匹配：若类型未命中预设分类，则尝试按类型名子串匹配拓扑节点 category/label
  const typeMatch = (n: FaultSourceNode) =>
    cats.length
      ? cats.includes(n.category)
      : (n.category || '').includes(type) || (n.label || '').includes(type)
  const scope = (drill.scope || '').trim()
  const picked = sources.filter((n) => {
    if (!typeMatch(n)) return false
    if (scope && scope !== (n.roomCode || '') && !((n.label || '').includes(scope)) && !((n.domain || '').toLowerCase().includes(scope.toLowerCase()))) return false
    return true
  })
  picked.sort((a, b) => (a.riskHint ? 0 : 1) - (b.riskHint ? 0 : 1) || a.health - b.health)
  return picked.slice(0, 3).map((n) => n.id)
}

function openPreview(p: DrillPlan) {
  previewPlan.value = p
  previewRes.value = null
  previewError.value = ''
  showPreview.value = true
  runPreview()
}

async function runPreview() {
  if (!previewPlan.value) return
  previewLoading.value = true
  previewError.value = ''
  previewRes.value = null
  try {
    const srcRes = await getFaultSources()
    const sources = srcRes.nodes || []
    if (!sources.length) {
      previewError.value = '暂无可用的故障源拓扑数据 (后端 /api/fault-impact/sources 为空)'
      return
    }
    const faultIds = mapDrillToFaults(previewPlan.value, sources)
    if (!faultIds.length) {
      previewError.value = '未匹配到对应故障源 (类型/范围未命中拓扑节点)'
      return
    }
    previewRes.value = await analyzeFaultImpact({
      faultIds,
      scope: { power: true, cool: true, network: true, business: true },
    })
  } catch (e: any) {
    previewError.value = (e && e.message) || '分析失败'
  } finally {
    previewLoading.value = false
  }
}

async function loadPlans() {
  try {
    const r = await getDrills()
    plans.value = (r.plans || []).filter((p) => !kw.value || (p.name + p.code).includes(kw.value))
    Object.assign(stats, r.stats || stats)
    offline.value = false
  } catch {
    offline.value = true
  }
}

async function loadRecords() {
  try {
    const r = await getDrillRecords(recFilter.value ?? undefined)
    records.value = r.records || []
  } catch {
    /* 离线: 不影响计划展示 */
  }
}

function planName(id: number) {
  return plans.value.find((p) => p.id === id)?.name || `计划#${id}`
}

// ---- 计划编辑 ----
const showPlan = ref(false)
const editing = ref<DrillPlan | null>(null)
const form = reactive<{ name: string; type: string; level: string; scope: string; duration: number; date: string; state: string; steps: DrillStep[] }>({
  name: '', type: '电力', level: '二级', scope: '', duration: 60, date: '', state: '计划中', steps: [],
})

function resetForm() {
  Object.assign(form, { name: '', type: '电力', level: '二级', scope: '', duration: 60, date: '', state: '计划中', steps: [] })
}

function openCreate() {
  editing.value = null
  resetForm()
  showPlan.value = true
}

function openEdit(p: DrillPlan) {
  editing.value = p
  Object.assign(form, {
    name: p.name, type: p.type, level: p.level || '二级', scope: p.scope || '',
    duration: p.duration || 60, date: p.date, state: p.state,
    steps: (p.steps || []).map((s) => ({ ...s })),
  })
  showPlan.value = true
}

async function savePlan() {
  if (!form.name) return
  saving.value = true
  try {
    const payload = { ...form }
    if (editing.value && editing.value.id > 0) {
      await updateDrill(editing.value.id, payload)
    } else {
      await createDrill(payload)
    }
    showPlan.value = false
    await loadPlans()
    offline.value = false
  } catch {
    offline.value = true
  } finally {
    saving.value = false
  }
}

async function remove(p: DrillPlan) {
  if (p.id < 0) { // 建议项不可删
    plans.value = plans.value.filter((x) => x.id !== p.id)
    return
  }
  if (!confirm('确认删除该演练计划？')) return
  try {
    await deleteDrill(p.id)
    await loadPlans()
  } catch {
    offline.value = true
  }
}

// ---- 执行记录编辑 ----
const showRecord = ref(false)
const editingRec = ref<DrillRecord | null>(null)
const recForm = reactive<{ planId: number; date: string; participants: number; startAt: string; endAt: string; score: number; result: string; note: string }>({
  planId: 0, date: '', participants: 0, startAt: '', endAt: '', score: 0, result: '通过', note: '',
})

function openRecord() {
  editingRec.value = null
  recForm.planId = plans.value[0]?.id || 0
  recForm.date = new Date().toISOString().slice(0, 10)
  recForm.participants = 0; recForm.startAt = ''; recForm.endAt = ''; recForm.score = 0; recForm.result = '通过'; recForm.note = ''
  showRecord.value = true
}

function openRecordEdit(r: DrillRecord) {
  editingRec.value = r
  Object.assign(recForm, { planId: r.planId, date: r.date, participants: r.participants, startAt: r.startAt, endAt: r.endAt, score: r.score, result: r.result, note: r.note })
  showRecord.value = true
}

async function saveRecord() {
  if (!recForm.planId) return
  saving.value = true
  try {
    const payload = { ...recForm, planName: planName(recForm.planId) }
    if (editingRec.value && editingRec.value.id > 0) {
      await updateDrillRecord(editingRec.value.id, payload)
    } else {
      await createDrillRecord(payload)
    }
    showRecord.value = false
    await loadRecords()
  } catch {
    offline.value = true
  } finally {
    saving.value = false
  }
}

async function removeRecord(r: DrillRecord) {
  if (!confirm('确认删除该执行记录？')) return
  try {
    await deleteDrillRecord(r.id)
    await loadRecords()
  } catch {
    offline.value = true
  }
}

function stateClass(s: string) {
  return {
    '计划中': '',
    '已编排': 'b',
    '已完成': 'g',
  }[s] || ''
}
function resultClass(r: string) {
  return r === '通过' ? 'g' : r === '未通过' ? 'r' : ''
}

onMounted(() => {
  loadPlans()
  loadRecords()
})
</script>
