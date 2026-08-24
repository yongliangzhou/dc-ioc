<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.risk') }}</h1>
      <span class="sub">{{ tl('风险识别与评估管控') }}</span>
    </div>
    <div class="grid cols-5" v-if="stats">
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
        :label="tl('严重')"
        :value="stats.critical"
        :quality="stats.critical ? 'bad' : 'good'"
        :severity="'crit'"
        :online="true"
      />
      <MetricCard
        metric-name="risk-high"
        :label="tl('高风险')"
        :value="stats.high"
        :quality="stats.high ? 'uncertain' : 'good'"
        :severity="'warn'"
        :online="true"
      />
    </div>
    <Panel style="margin-top: 16px">
      <div class="panel-head">
        <h5 class="section-title">{{ tl('风险评估列表') }}</h5>
        <div class="panel-actions">
          <button class="btn-sm" v-bind="authState('write')" @click="runAnalyze">
            {{ analyzing ? tl('分析中…') : tl('自动分析') }}
          </button>
          <button class="btn-sm primary" v-bind="authState('write')" @click="openCreate">
            {{ tl('新建') }}
          </button>
        </div>
      </div>
      <div class="tbl" v-if="risks.length">
        <div class="tbl-head">
          <span class="col w-risk-code">{{ tl('编号') }}</span
          ><span class="col w-risk-title">{{ tl('标题') }}</span
          ><span class="col w-risk-cat">{{ tl('类别') }}</span
          ><span class="col w-risk-sev">{{ tl('严重性') }}</span
          ><span class="col w-risk-prob">{{ tl('可能性') }}</span
          ><span class="col w-risk-stat">{{ tl('状态') }}</span
          ><span class="col w-risk-op">{{ tl('操作') }}</span>
        </div>
        <div v-for="r in risks" :key="r.id" class="tbl-row">
          <span class="col w-risk-code">{{ r.code }}</span>
          <span class="col w-risk-title fw">{{ r.title }}</span>
          <span class="col w-risk-cat muted">{{ r.category }}</span>
          <span class="col w-risk-sev"
            ><span
              class="pill-tag"
              :class="r.severity === 'critical' ? 'r' : r.severity === 'high' ? 'a' : 'g'"
              >{{ sevLabel(r.severity) }}</span
            ></span
          >
          <span class="col w-risk-prob muted">{{ probLabel(r.probability) }}</span>
          <span class="col w-risk-stat"
            ><span class="pill-tag" :class="r.status === 'open' ? 'a' : 'g'">{{
              r.status === 'open' ? '未关闭' : '已缓解'
            }}</span></span
          >
          <span class="col w-risk-op p-ops">
            <button class="link" v-bind="authState('write')" @click="openEdit(r)">{{ tl('编辑') }}</button>
            <button class="link danger" v-bind="authState('write')" @click="remove(r)">{{ tl('删除') }}</button>
          </span>
        </div>
      </div>
      <div class="empty" v-else>{{ tl('暂无风险') }}</div>
    </Panel>

    <!-- 风险抽屉 -->
    <div class="drawer-mask" v-if="drawer" @click.self="drawer = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ form.id ? tl('编辑风险') : tl('新建风险') }}</span>
          <button class="x" @click="drawer = false">✕</button>
        </div>
        <div class="form">
          <label>{{ tl('风险描述') }}
            <input v-model.trim="form.risk" class="ipt" :placeholder="tl('如 空调冗余不足')" />
          </label>
          <label>{{ tl('类别') }}
            <input v-model.trim="form.cat" class="ipt" :placeholder="tl('如 暖通 / 电力')" />
          </label>
          <div class="row">
            <label>{{ tl('可能性') }}
              <select v-model.number="form.prob" class="ipt">
                <option :value="1">低</option>
                <option :value="2">中</option>
                <option :value="3">高</option>
                <option :value="4">极高</option>
              </select>
            </label>
            <label>{{ tl('影响') }}
              <select v-model.number="form.impact" class="ipt">
                <option :value="1">低</option>
                <option :value="2">中</option>
                <option :value="3">高</option>
                <option :value="4">极高</option>
              </select>
            </label>
          </div>
          <label>{{ tl('缓解措施') }}
            <textarea v-model.trim="form.ctrl" class="ipt" rows="2"></textarea>
          </label>
          <label>{{ tl('责任人') }}
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
              <span class="pill-tag" :class="s.level === '高' ? 'r' : s.level === '中' ? 'a' : 'g'">{{
                s.level
              }}</span>
              <span class="sug-title">{{ s.risk }}</span>
            </div>
            <div class="sug-meta muted">P{{ s.prob }} × I{{ s.impact }} · {{ s.ctrl }}</div>
            <button class="btn-sm primary sm" @click="acceptSuggestion(s)">{{ tl('采纳入库') }}</button>
          </div>
        </div>
      </div>
    </div>
    <Panel v-if="!risks.length && !e"
      ><div class="flex center" style="padding: 40px">
        <span class="muted">{{ tl('common.loading') }}</span>
      </div></Panel
    >
    <Panel v-if="e"
      ><div class="flex center" style="padding: 40px">
        <span class="muted" style="color: var(--red)">{{ e }}</span>
      </div></Panel
    >
  </div>
</template>
<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import {
  getRisks,
  getRiskStats,
  createRisk,
  updateRisk,
  deleteRisk,
  analyzeRisk,
  type RiskView,
  type RiskStats,
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
const risks = ref<RiskView[]>([])
const stats = ref<RiskStats | null>(null)
const e = ref('')

// 抽屉
const drawer = ref(false)
const saving = ref(false)
const err = ref('')
const form = ref<Partial<RiskView> & RiskCreate>({
  risk: '', cat: '', prob: 2, impact: 2, ctrl: '', owner: '',
})

// 自动分析
const analyzeDrawer = ref(false)
const analyzing = ref(false)
const suggestions = ref<any[]>([])

function sevLabel(s: string) {
  const m: Record<string, string> = { low: '低', medium: '中', high: '高', critical: '严重' }
  return m[s] || s
}
function probLabel(p: string | number) {
  const m: Record<string, string> = { 1: '低', 2: '中', 3: '高', 4: '极高' }
  return m[String(p)] || String(p)
}

function openCreate() {
  form.value = { risk: '', cat: '', prob: 2, impact: 2, ctrl: '', owner: '' }
  err.value = ''
  drawer.value = true
}
function openEdit(r: RiskView) {
  form.value = {
    id: r.id, risk: r.title, cat: r.category,
    prob: Number(r.probability) || 2, impact: Number(r.severity === 'critical' ? 4 : r.severity === 'high' ? 3 : 2),
    ctrl: r.mitigation ?? '', owner: '',
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
    await load()
    toast.success(tl('已保存'))
  } catch (ex: unknown) {
    err.value = (ex as ErrorLike)?.message || tl('保存失败')
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
    onConfirm: async () => { await deleteRisk(r.id) },
  })
  if (ok) {
    await load()
    toast.success(tl('已删除'))
  }
}

async function runAnalyze() {
  analyzing.value = true
  try {
    const res: any = await analyzeRisk()
    suggestions.value = res.suggestions || []
    analyzeDrawer.value = true
  } catch (ex: unknown) {
    e.value = (ex as ErrorLike)?.message || tl('分析失败')
  } finally {
    analyzing.value = false
  }
}
async function acceptSuggestion(s: any) {
  try {
    await createRisk({
      risk: s.risk, cat: s.cat, prob: s.prob, impact: s.impact, ctrl: s.ctrl, owner: s.owner,
    })
    suggestions.value = suggestions.value.filter((x) => x !== s)
    await load()
    toast.success(tl('已采纳入库'))
  } catch (ex: unknown) {
    e.value = (ex as ErrorLike)?.message || tl('入库失败')
  }
}

async function load() {
  try {
    const [r, s] = await Promise.all([getRisks(), getRiskStats()])
    risks.value = r
    stats.value = s
  } catch (ex: unknown) {
    e.value = (ex as ErrorLike)?.message || String(ex)
  }
}
onMounted(load)
</script>
<style scoped>
.tbl {
  max-height: 420px;
  overflow-y: auto;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.panel-actions {
  display: flex;
  gap: 8px;
}
.p-ops {
  display: flex;
  gap: 8px;
}
.btn-sm {
  padding: 5px 12px;
  border-radius: 7px;
  border: 1px solid var(--border);
  background: var(--bg2);
  color: var(--text2);
  cursor: pointer;
  font-size: 12px;
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
.ipt {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 7px 9px;
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
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
.tbl-head,
.tbl-row {
  display: flex;
  align-items: center;
  padding: 9px 6px;
  font-size: 12.5px;
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
.col {
  flex-shrink: 0;
}
.w-risk-code {
  width: 100px;
}
.w-risk-title {
  width: 200px;
}
.w-risk-cat {
  width: 90px;
}
.w-risk-sev {
  width: 70px;
}
.w-risk-prob {
  width: 70px;
}
.w-risk-stat {
  width: 80px;
}
.w-risk-op {
  width: 100px;
}
.w-risk-mit {
  flex: 1;
}
.fw {
  font-weight: 500;
}
.pill-tag {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 9px;
  background: var(--bg2);
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
}
</style>
