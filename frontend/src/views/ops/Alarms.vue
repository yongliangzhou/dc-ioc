<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('智能运营') }} {{ tl('·') }} {{ tl('告警中心') }}</h1>
      <span class="sub"
        >{{ tl('规则引擎') }} / {{ tl('阈值基线') }} / {{ tl('告警持久化') }} {{ tl('·') }}
        {{ tl('按业务系统') }}&{{ tl('等级分组') }}</span
      >
      <span class="pill">{{
        activeTab === 'rules' ? '规则引擎' : activeTab === 'active' ? '活动告警' : '告警历史'
      }}</span>
      <button class="go-rule-btn" @click="goRuleEngine" title="进入告警规则引擎管理页面">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>
        {{ tl('进入规则引擎') }}
      </button>
    </div>

    <!-- KPI 行 -->
    <div class="grid cols-5" v-if="a">
      <MetricCard
        metric-name="alarm-raw"
        :label="tl('24h 原始告警')"
        :value="a.convergence.raw"
        unit="条"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="alarm-converged"
        :label="tl('收敛后')"
        :value="a.convergence.converged"
        unit="条"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="alarm-rate"
        :label="tl('收敛率')"
        :value="a.convergence.rate"
        unit="%"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="alarm-mtta"
        label="MTTA"
        :value="a.sla.mttaMin"
        unit="min"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="alarm-mttr"
        label="MTTR"
        :value="a.sla.mttrMin"
        unit="min"
        quality="good"
        :online="true"
      />
    </div>

    <!-- 规则引擎统计 -->
    <div class="grid cols-4" v-if="engineState">
      <MetricCard
        metric-name="alarm-eng-rules"
        :label="tl('规则总数')"
        :value="engineState.totalRules"
        unit="条"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="alarm-eng-enabled"
        :label="tl('已启用')"
        :value="engineState.enabledCount"
        unit="条"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="alarm-eng-triggered"
        :label="tl('已触发')"
        :value="engineState.triggeredCount"
        unit="条"
        :quality="engineState.triggeredCount ? 'uncertain' : 'good'"
        :online="true"
        :severity="engineState.triggeredCount ? 'warn' : 'normal'"
      />
      <MetricCard
        metric-name="alarm-eng-silenced"
        :label="tl('静默中')"
        :value="engineState.silencedCount"
        unit="条"
        :quality="engineState.silencedCount ? 'uncertain' : 'good'"
        :online="true"
      />
    </div>

    <!-- Tab 切换 -->
    <Panel style="margin-bottom: 12px">
      <div class="flex gap8 center wrap">
        <button class="tv-btn" :class="{ on: activeTab === 'rules' }" @click="activeTab = 'rules'">
          {{ tl('规则引擎') }} ({{ engineState?.totalRules ?? 0 }})
        </button>
        <button
          class="tv-btn"
          :class="{ on: activeTab === 'active' }"
          @click="activeTab = 'active'"
        >
          {{ tl('活动告警') }} ({{ activeCount }})
        </button>
        <button
          class="tv-btn"
          :class="{ on: activeTab === 'history' }"
          @click="activeTab = 'history'; loadHistory()"
        >
          {{ tl('告警历史') }}
        </button>
      </div>
    </Panel>

    <!-- ===== Tab: 规则引擎 (Presentational 子组件) ===== -->
    <AlarmRulePanel v-if="activeTab === 'rules'" :rules="localRules" @toggle="toggleRule" />

    <!-- ===== Tab: 活动告警 ===== -->
    <template v-if="activeTab === 'active'">
      <!-- 收敛策略 · 按收敛规则分组 -->
      <div class="section-title">
        {{ tl('收敛策略与规则链') }} {{ tl('·') }} {{ tl('预测告警') }}
      </div>
      <div class="grid cols-2" v-if="a">
        <Panel>
          <template #ct
            >{{ tl('收敛规则链') }} ({{ tl('共') }} {{ a.rules.length }} {{ tl('条') }})</template
          >
          <div class="flex gap8 wrap" style="margin: 8px 0 12px">
            <span v-for="r in a.rules" :key="r" class="tag p" style="padding: 6px 12px">{{
              r
            }}</span>
          </div>
          <div class="kvs">
            <span class="k">{{ tl('自动闭环率') }}</span
            ><span class="v" style="color: var(--green)">{{ a.sla.autoCloseRate }}%</span>
            <span class="k">{{ tl('误报抑制') }}</span
            ><span class="v" style="font-size: 11.5px"
              >AI {{ tl('过滤小动物') }}/{{ tl('扬尘等') }} 38 {{ tl('条') }}/{{ tl('日') }}</span
            >
          </div>
        </Panel>
        <Panel>
          <template #ct>AI {{ tl('趋势预测告警') }} ({{ tl('置信度排序') }})</template>
          <div class="alarm" v-for="(t, i) in a.trend" :key="i">
            <span class="lv info">{{ lvText('info') }}</span>
            <div class="txt">
              {{ t.id }} {{ tl('—') }} {{ t.pred }}
              <span class="tag" :class="t.conf > 85 ? 'g' : t.conf > 70 ? 'a' : 'b'"
                >{{ tl('置信') }} {{ t.conf }}%</span
              >
              <div class="meta">{{ tl('建议') }}: {{ t.sug }}</div>
            </div>
          </div>
        </Panel>
      </div>

      <!-- 活动告警 · 按系统/等级分组 -->
      <div class="section-title">
        {{ tl('活动告警') }} {{ tl('·') }} {{ tl('按业务系统') }} & {{ tl('等级分组') }} ({{
          activeCount
        }}
        {{ tl('条') }})
      </div>

      <!-- 实时越限联动引擎 -->
      <Panel style="margin-bottom: 12px">
        <div class="flex gap8 center wrap" style="margin-bottom: 10px">
          <span class="pill g"><span class="dot g"></span>{{ tl('联动引擎在线') }}</span>
          <span class="pill"
            >{{ tl('活动联动告警') }} {{ realtimeLinkage.active.length }} {{ tl('条') }}</span
          >
          <span class="pill"
            >{{ tl('规则') }}
            {{ realtimeLinkage.rules.filter((r) => r.status === 'enabled').length }}/{{
              realtimeLinkage.rules.length
            }}
            {{ tl('启用') }}</span
          >
          <span class="muted" style="font-size: 11px"
            >{{ tl('遥测测点越限') }} → {{ tl('自动生成告警') }} → {{ tl('一键转工单') }}</span
          >
        </div>
        <div class="grid cols-2">
          <div v-for="r in realtimeLinkage.rules" :key="r.id" class="rule-row">
            <div class="rule-info">
              <div class="rule-name">
                <span class="dot" :class="r.enabled ? 'g' : 'a'"></span>
                <span>{{ r.ruleCode || r.metric }}</span>
              </div>
              <div class="rule-meta">
                <span class="mono">{{ r.metric }} {{ ruleBandLabel(r) }}</span>
                <span class="muted">{{ r.category }}</span>
              </div>
            </div>
            <div class="rule-actions">
              <button
                class="rule-btn"
                :class="r.status === 'enabled' ? 'on' : 'off'"
                @click="realtimeLinkage.toggleRule(String(r.id))"
                :title="r.status === 'enabled' ? '点击静默' : '点击启用'"
              >
                {{ r.status === 'enabled' ? '已启用' : '已静默' }}
              </button>
            </div>
          </div>
        </div>
      </Panel>

      <AlarmListPanel
        :alarms="sortedActive"
        @ack="handleAck"
        @resolve="handleResolve"
        @runbook="openRunbooks"
        @ticket="openTicketFromAlarm"
        @feedback="openFeedback"
        @goDevice="handleGoDevice"
      />
    </template>

    <!-- ===== Tab: 告警历史 ===== -->
    <template v-if="activeTab === 'history'">
      <!-- 告警趋势 -->
      <div class="section-title">24h 告警趋势 · 按系统分组</div>
      <TrendChart
        v-if="history"
        :metrics="historyTrendMetrics"
        :active="trendActive"
        :series="trendSeries"
        :loading="historyLoading"
        @select="trendActive = $event"
        @range-change="onRangeChange"
      />

      <!-- 历史统计 -->
      <div class="section-title">告警历史 · 按业务系统统计</div>
      <div class="grid cols-4" v-if="history">
        <KpiCard
          v-for="(cnt, sys) in history.stats.bySystem"
          :key="sys"
          :title="sys"
          :value="cnt"
          unit="条/24h"
        />
      </div>

      <!-- 历史列表 (虚拟滚动, 千条数据不卡顿) -->
      <div class="section-title">近期告警记录 ({{ history?.total ?? history?.items.length ?? 0 }})</div>
      <Panel class="scroll-x" v-if="history">
        <div class="hist-thead">
          <div class="hc w-lv">级别</div>
          <div class="hc w-sys">系统</div>
          <div class="hc w-msg">告警内容</div>
          <div class="hc w-time">触发时间</div>
          <div class="hc w-st">状态</div>
          <div class="hc w-time">解决时间</div>
          <div class="hc w-auto">自动</div>
        </div>
        <VirtualList
          class="hist-virtual"
          :items="history.items"
          :item-height="48"
          :height="460"
          key-field="id"
        >
          <template #default="{ item: evt }">
            <div class="hist-row">
              <div class="hc w-lv">
                <span class="tag" :class="lvClass(evt.level)">{{ lvText(evt.level) }}</span>
              </div>
              <div class="hc w-sys">
                <span class="sys-badge">{{ evt.system }}</span>
              </div>
              <div class="hc w-msg desc-cell">
                {{ evt.message }}
                <div class="meta mono" style="font-size: 9px">
                  {{ evt.metric }}: {{ evt.value }}{{ evt.unit }} → 阈值 {{ evt.threshold
                  }}{{ evt.unit }}
                </div>
              </div>
              <div class="hc w-time mono" style="font-size: 11px">{{ evt.triggeredAt }}</div>
              <div class="hc w-st">
                <span class="tag" :class="stateTagClass(evt.status)">{{
                  stateLabel(evt.status)
                }}</span>
              </div>
              <div class="hc w-time mono" style="font-size: 11px">{{ evt.resolvedAt ?? '—' }}</div>
              <div class="hc w-auto">{{ evt.autoResolved ? '是' : '否' }}</div>
            </div>
          </template>
          <template #empty>暂无告警历史记录</template>
        </VirtualList>
      </Panel>
    </template>

    <KnowledgePanels :knowledge="a?.knowledge" />

    <div class="footer-note">
      智能运营·告警中心 — 规则引擎 {{ engineState?.enabledCount ?? 0 }}/{{
        engineState?.totalRules ?? 0
      }}
      启用 · 活动告警 {{ activeCount }} 条 (含联动 {{ realtimeLinkage.active.length }}) · 数据每
      {{ refreshSec }}s 刷新
    </div>

    <transition name="fade">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>

    <!-- 告警转工单弹窗 -->
    <TicketFormModal
      :open="ticketModalOpen"
      title="告警转工单"
      :initial="ticketInitial"
      initial-source="alarm"
      @close="ticketModalOpen = false"
      @submit="onTicketSubmit"
    />

    <!-- 关联处置预案 -->
    <transition name="fade">
      <div v-if="relModalOpen" class="modal-mask" @click.self="relModalOpen = false">
        <div class="modal">
          <div class="modal-h">关联处置预案 · {{ relAlarm?.system }}</div>
          <div class="rel-list">
            <div class="rel-item" v-for="kb in relRunbooks" :key="kb.id">
              <div class="rel-top">
                <span class="tag" :class="'ty-' + kb.type">{{ kbType(kb.type) }}</span>
                <b>{{ kb.code }} {{ kb.title }}</b>
                <span class="tag hot" v-if="kb.hot">HOT</span>
              </div>
              <div class="rel-sum">{{ kb.summary || '—' }}</div>
              <ol class="rel-steps" v-if="kb.steps && kb.steps.length">
                <li v-for="(s, i) in kb.steps" :key="i">{{ s }}</li>
              </ol>
              <button class="btn primary sm" @click="linkToTicket(kb)">转工单并关联此预案</button>
            </div>
            <div class="muted center" v-if="!relLoading && !relRunbooks.length">
              未匹配到相关预案，可直接转工单
            </div>
            <div class="muted center" v-if="relLoading">加载中…</div>
          </div>
          <div class="modal-f"><button class="btn" @click="relModalOpen = false">关闭</button></div>
        </div>
      </div>
    </transition>

    <!-- 处理反馈 / 经验沉淀 -->
    <transition name="fade">
      <div v-if="fbModalOpen" class="modal-mask" @click.self="fbModalOpen = false">
        <div class="modal fb-modal">
          <div class="modal-h">处理反馈 · 经验沉淀 · {{ fbAlarm?.system }}</div>
          <div class="fb-subj">{{ fbAlarm?.message }}</div>

          <!-- 智能匹配的场景化根因 / 排查 / 修复 -->
          <div class="fb-scn" v-if="fbScenario">
            <div class="fb-scn-tabs">
              <button :class="{ on: fbTab === 'cause' }" @click="fbTab = 'cause'">根因分析</button>
              <button :class="{ on: fbTab === 'steps' }" @click="fbTab = 'steps'">排查步骤</button>
              <button :class="{ on: fbTab === 'fix' }" @click="fbTab = 'fix'">修复方案</button>
            </div>
            <div class="fb-scn-body">
              <p v-if="fbTab === 'cause'" class="cause">{{ fbScenario.rootCause }}</p>
              <ol v-else-if="fbTab === 'steps'" class="steps">
                <li v-for="(s, i) in fbScenario.steps" :key="i">{{ s }}</li>
              </ol>
              <p v-else class="fix">{{ fbScenario.fix }}</p>
            </div>
            <button class="btn primary sm" @click="gotoKb(fbScenario.kbQuery)">
              一键跳转知识库
            </button>
          </div>

          <!-- 标注处理结果 -->
          <div class="fb-row">
            <span class="fb-label">处理结果</span>
            <div class="fb-tags">
              <button
                v-for="opt in fbOptions"
                :key="opt"
                class="fb-tag"
                :class="{ on: fbResult === opt }"
                @click="fbResult = opt"
              >
                {{ opt }}
              </button>
            </div>
          </div>
          <div class="fb-row col">
            <span class="fb-label">处理备注 / 经验</span>
            <textarea
              v-model="fbNote"
              rows="3"
              class="fb-text"
              placeholder="记录根因确认、处置动作、后续优化建议…"
            ></textarea>
          </div>

          <!-- 已有处理记录 -->
          <div class="fb-records" v-if="fbRecords.length">
            <div class="fb-rec-title">已沉淀处理记录 ({{ fbRecords.length }})</div>
            <div class="fb-rec" v-for="(r, i) in fbRecords" :key="i">
              <span class="fb-rec-tag">{{ r.result }}</span>
              <span class="fb-rec-note">{{ r.note || '—' }}</span>
              <span class="fb-rec-time">{{ fmtTs(r.ts) }}</span>
            </div>
          </div>

          <div class="modal-f">
            <button class="btn" @click="fbModalOpen = false">取消</button>
            <button class="btn primary" :disabled="!fbResult || fbSaving" @click="submitFeedback">
              {{ fbSaving ? '提交中…' : '提交并记录' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

interface RtAlarm extends Alarm {
  rt?: boolean
  domain?: string
  metric?: string
}
import { useRouter } from 'vue-router'
import {
  getAlarms,
  getAlarmRules,
  getAlarmHistory,
  acknowledgeAlarm,
  resolveAlarm,
  toggleAlarmRule,
  getRelatedRunbooks,
  submitAlarmFeedback,
} from '@/api'
import MetricCard from '@/components/common/MetricCard.vue'
import TrendChart from '@/components/charts/TrendChart.vue'
import type { TrendMetric } from '@/components/charts/TrendChart.vue'
import type { MetricHistoryPoint } from '@/types'
import KnowledgePanels from '@/components/KnowledgePanels.vue'
import { KpiCard } from '@dc-ioc/ui'
import Panel from '@/components/common/Panel.vue'
import { lvClass, lvText } from '@/utils/state'
import { useTicketsStore } from '@/stores/modules/tickets'
import TicketFormModal from '@/components/business/TicketFormModal.vue'
import AlarmRulePanel from './components/AlarmRulePanel.vue'
import AlarmListPanel from './components/AlarmListPanel.vue'
import VirtualList from '@/components/common/VirtualList.vue'
import { matchScenario } from '@/engine/alarmNotifier'
import type { TicketCreateRequest, KnowledgeItem } from '@/types'

/** 按阈值带格式显示规则范围, 兼容 AlarmRuleDef 的可选字段类型 */
function ruleBandLabel(r: AlarmRuleDef): string {
  const lo = r.warnLo ?? r.critLo
  const hi = r.warnHi ?? r.critHi
  const haveCrit = r.critLo != null || r.critHi != null
  const parts: string[] = []
  if (lo != null && hi != null) parts.push(`${lo}~${hi}`)
  else if (lo != null) parts.push(`≥${lo}`)
  else if (hi != null) parts.push(`≤${hi}`)
  if (parts.length === 0) return '—'
  return haveCrit ? `${parts[0]} ⚠` : parts[0]
}

const router = useRouter()
const ticketsStore = useTicketsStore()

function goRuleEngine() {
  router.push('/ops/alarm-rules')
}

const ticketModalOpen = ref(false)
const ticketInitial = ref<Partial<TicketCreateRequest>>({})
const currentAlarm = ref<Alarm | null>(null)
const toast = ref('')
let toastTimer = 0

function showToast(msg: string) {
  toast.value = msg
  if (toastTimer) clearTimeout(toastTimer)
  toastTimer = window.setTimeout(() => (toast.value = ''), 4000)
}

function openTicketFromAlarm(alarm: Alarm) {
  currentAlarm.value = alarm
  ticketInitial.value = {
    title: `[告警转工单] ${alarm.message}`,
    sys: alarm.system,
    lv: alarm.level,
    owner: alarm.owner ?? '待分配',
    sla: alarm.level === 'crit' ? '1h' : alarm.level === 'warn' ? '4h' : '8h',
    description: `来源告警系统: ${alarm.system}\n告警内容: ${alarm.message}\n触发时间: ${alarm.time ?? '—'}\n原始状态: ${alarm.status}`,
  }
  ticketModalOpen.value = true
}

async function onTicketSubmit(data: TicketCreateRequest) {
  const t = await ticketsStore.create({ ...data, source: 'alarm' })
  // 联动告警转工单后标记为已确认, 形成闭环
  if (currentAlarm.value && (currentAlarm.value as RtAlarm).rt) {
    realtimeLinkage.ack((currentAlarm.value as RtAlarm).id ?? '')
  }
  ticketModalOpen.value = false
  currentAlarm.value = null
  showToast(`已生成工单 ${t.id} 并关联告警`)
}

/* ---- 关联处置预案 (告警 -> 知识库) ---- */
const relModalOpen = ref(false)
const relRunbooks = ref<KnowledgeItem[]>([])
const relAlarm = ref<Alarm | null>(null)
const relLoading = ref(false)
const KB_TYPE: Record<string, string> = {
  sop: '运行SOP',
  drawing: '竣工图纸',
  manual: '设备手册',
  emergency: '应急预案',
  case: '故障案例',
  training: '培训',
}
function kbType(t: string) {
  return KB_TYPE[t] || t
}

async function openRunbooks(alarm: Alarm) {
  relAlarm.value = alarm
  relModalOpen.value = true
  relRunbooks.value = []
  relLoading.value = true
  try {
    relRunbooks.value = await getRelatedRunbooks({
      system: alarm.system,
      domain: (alarm as RtAlarm).domain,
      metric: (alarm as RtAlarm).metric,
    })
  } catch (_) {
    /* ignore */
  } finally {
    relLoading.value = false
  }
}

function linkToTicket(kb: KnowledgeItem) {
  relModalOpen.value = false
  const alarm = relAlarm.value
  if (!alarm) return
  openTicketFromAlarm(alarm)
  ticketInitial.value = {
    ...ticketInitial.value,
    description: `${ticketInitial.value.description || ''}\n关联处置预案: ${kb.code} ${kb.title}\n步骤: ${(kb.steps || []).join(' / ')}`,
  }
}

/* ---- 处理反馈 / 经验沉淀 (闭环入口) ---- */
const fbModalOpen = ref(false)
const fbAlarm = ref<Alarm | null>(null)
const fbScenario = ref<ReturnType<typeof matchScenario> | null>(null)
const fbTab = ref<'cause' | 'steps' | 'fix'>('cause')
const fbOptions = ['已处理修复', '误报', '转工单', '持续观察']
const fbResult = ref('')
const fbNote = ref('')
const fbSaving = ref(false)
const fbRecords = ref<{ result: string; note: string; ts: number }[]>([])

function fbKey(id: string) {
  return `alarm_feedback_${id}`
}
function loadFbRecords(id: string) {
  try {
    const raw = localStorage.getItem(fbKey(id))
    fbRecords.value = raw ? JSON.parse(raw) : []
  } catch {
    fbRecords.value = []
  }
}
function fmtTs(ts: number) {
  const d = new Date(ts)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function openFeedback(alarm: Alarm) {
  const id = (alarm as RtAlarm).rt ? ((alarm as RtAlarm).id ?? '') : `evt-${alarm.time}-${alarm.system}`
  fbAlarm.value = alarm
  fbScenario.value = matchScenario(alarm)
  fbTab.value = 'cause'
  fbResult.value = ''
  fbNote.value = ''
  loadFbRecords(id)
  fbModalOpen.value = true
}

function gotoKb(query: string) {
  if (query) router.push({ path: '/ops/knowledge', query: { q: query } })
  else router.push({ path: '/ops/knowledge' })
}

async function submitFeedback() {
  if (!fbAlarm.value || !fbResult.value) return
  const id = (fbAlarm.value as RtAlarm).rt
  ? ((fbAlarm.value as RtAlarm).id ?? '')
    : `evt-${fbAlarm.value.time}-${fbAlarm.value.system}`
  fbSaving.value = true
  try {
    const rec = { result: fbResult.value, note: fbNote.value, ts: Date.now() }
    const all = [...fbRecords.value, rec]
    try {
      localStorage.setItem(fbKey(id), JSON.stringify(all))
    } catch {
      /* ignore */
    }
    // 后端持久化 (失败不阻断本地闭环)
    try {
      await submitAlarmFeedback({
        alarmId: String(id),
        system: fbAlarm.value.system || '',
        result: fbResult.value,
        note: fbNote.value,
      })
    } catch {
      /* 后端未就绪时忽略, 本地已记录 */
    }
    // 闭环：确认 + 关单
    handleAck(fbAlarm.value)
    handleResolve(fbAlarm.value)
    fbModalOpen.value = false
    showToast(`已记录处理反馈 (${fbResult.value}) 并关闭告警`)
  } finally {
    fbSaving.value = false
  }
}

/** 从活动告警跳转到关联设备页面 (1.5.3) */
const DEVICE_ROUTE_MAP: Record<string, string> = {
  chiller: '/monitor/hvac/chiller',
  crac: '/monitor/hvac/crac',
  liquid: '/monitor/hvac/liquid',
  power: '/monitor/power',
  fire: '/ops/fire',
  security: '/ops/security',
  network: '/monitor/network',
  hvac: '/monitor/hvac/chiller',
}
function handleGoDevice(payload: { sys: string; deviceId: string }) {
  const s = (payload.sys || '').toLowerCase()
  let path = ''
  for (const [key, route] of Object.entries(DEVICE_ROUTE_MAP)) {
    if (s.includes(key)) {
      path = route
      break
    }
  }
  if (!path) path = '/monitor/hvac/chiller' // fallback
  if (payload.deviceId) path += `?device=${payload.deviceId}`
  router.push(path)
}
import { realtimeLinkage } from '@/engine/realtimeLinkage'
import type {
  AlarmCenter,
  Alarm,
  AlarmRuleDef,
  AlarmEngineState,
  AlarmHistoryResponse,
} from '@/types'

const a = ref<AlarmCenter | null>(null)
const engineState = ref<AlarmEngineState | null>(null)
const refreshSec = Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000) / 1000
const activeTab = ref<'rules' | 'active' | 'history'>('rules')
const trendActive = ref('alarm-total')

/* ---- 规则列表: 判定统一在后端执行, 前端仅展示 + 启停 (onMounted 拉取) ---- */
const localRules = ref<AlarmRuleDef[]>([])

async function toggleRule(rule: AlarmRuleDef) {
  const idx = localRules.value.findIndex((r) => r.id === rule.id)
  if (idx < 0) return
  const next = rule.status === 'enabled' ? 'disabled' : 'enabled'
  localRules.value[idx] = { ...rule, status: next, updated: new Date().toISOString().slice(0, 16) }
  // 尝试同步远端
  try {
    await toggleAlarmRule(String(rule.id), next)
  } catch (_) {
    /* 本地已更新 */
  }
  refreshEngineState()
}

function refreshEngineState() {
  engineState.value = {
    totalRules: localRules.value.length,
    enabledCount: localRules.value.filter((r) => r.enabled).length,
    triggeredCount: 0,
    silencedCount: localRules.value.filter((r) => r.status === 'silenced').length,
  }
}

/* ---- 活动告警: 统一消费真实联动告警引擎 (B1: 不再混入 generated 假告警) ---- */
const activeCount = computed(() => realtimeLinkage.active.length)

const sortedActive = computed<Alarm[]>(() => {
  const all = [...realtimeLinkage.active] as Alarm[]
  const order = { crit: 0, warn: 1, info: 2 }
  return all.sort((x, y) => (order[x.level as 'crit'] ?? 3) - (order[y.level as 'crit'] ?? 3))
})

/* ---- 告警操作 (兼容实时联动告警) ---- */
async function handleAck(alarm: Alarm) {
  const rt = (alarm as RtAlarm).rt
  if (rt) {
    realtimeLinkage.ack((alarm as RtAlarm).id ?? '')
    return
  }
  try {
    await acknowledgeAlarm(`evt-${alarm.time}-${alarm.system}`, '运维人员')
  } catch (_) {}
  if (a.value) {
    const idx = a.value.active.findIndex((x) => x === alarm)
    if (idx >= 0) a.value.active[idx] = { ...alarm, status: 'acknowledged' }
  }
}

async function handleResolve(alarm: Alarm) {
  const rt = (alarm as RtAlarm).rt
  if (rt) {
    realtimeLinkage.resolve((alarm as RtAlarm).id ?? '')
    return
  }
  try {
    await resolveAlarm(`evt-${alarm.time}-${alarm.system}`, '运维人员')
  } catch (_) {}
  if (a.value) {
    a.value.active = a.value.active.filter((x) => x !== alarm).concat({ ...alarm, status: 'resolved' })
  }
}

/* ---- 告警历史 ---- */
const history = ref<AlarmHistoryResponse | null>(null)
const historyLoading = ref(false)

async function loadHistory() {
  historyLoading.value = true
  try {
    history.value = await getAlarmHistory({})
  } catch (_) {
    // 模拟历史数据
    history.value = {
      items: (a.value?.active ?? []).map((x, i) => ({
        id: `evt-hist-${i}`,
        ruleId: `r-hist-${i}`,
        ruleName: `规则-${x.system}`,
        metric: x.system,
        level: x.level,
        system: x.system,
        message: x.message,
        value: 0,
        threshold: 0,
        unit: undefined,
        status:
          x.status === 'resolved'
            ? ('resolved' as const)
            : x.status === 'acknowledged'
              ? ('acknowledged' as const)
              : ('active' as const),
        triggeredAt: x.time ?? '',
        resolvedAt: x.status === 'resolved' ? '2026-07-25 14:30' : undefined,
        autoResolved: false,
        escalationCount: 0,
      })),
      total: a.value?.active.length ?? 0,
      page: 1,
      limit: 50,
      stats: {
        total24h: (a.value?.active.length ?? 0) + 12,
        active24h: a.value?.active.filter((x) => x.status !== 'resolved').length ?? 0,
        resolved24h: a.value?.active.filter((x) => x.status === 'resolved').length ?? 0,
        mttaMin: a.value?.sla.mttaMin ?? 15,
        mttrMin: a.value?.sla.mttrMin ?? 30,
        bySystem:
          a.value?.active.reduce(
            (acc, x) => {
              acc[x.system] = (acc[x.system] ?? 0) + 1
              return acc
            },
            {} as Record<string, number>,
          ) ?? {},
        byLevel: {
          crit: a.value?.active.filter((x) => x.level === 'crit').length ?? 0,
          warn: a.value?.active.filter((x) => x.level === 'warn').length ?? 0,
          info: a.value?.active.filter((x) => x.level === 'info').length ?? 0,
        },
      },
    }
  }
  historyLoading.value = false
}

function stateLabel(s: string) {
  return s === 'active'
    ? '活跃'
    : s === 'acknowledged'
      ? '已确认'
      : s === 'resolved'
        ? '已解决'
        : '已抑制'
}
function stateTagClass(s: string) {
  return s === 'active' ? 'r' : s === 'acknowledged' ? 'a' : 'g'
}

/* ---- 历史趋势 ---- */
const historyTrendMetrics: TrendMetric[] = [
  {
    name: 'alarm-total',
    label: tl('告警总数'),
    unit: '条/10min',
    latest: history.value?.stats.total24h,
  },
  {
    name: 'alarm-active',
    label: tl('活动告警'),
    unit: '条',
    latest: history.value?.stats.active24h,
  },
]

const trendSeries = computed(() => {
  const n = 24
  return {
    'alarm-total': Array.from({ length: n }, (_, i) => ({
      ts: `H-${n - i}`,
      quality: 'good' as const,
      value: Math.round(5 + Math.random() * 20),
    })),
    'alarm-active': Array.from({ length: n }, (_, i) => ({
      ts: `H-${n - i}`,
      quality: 'good' as const,
      value: Math.round(2 + Math.random() * 8),
    })),
  } as Record<string, MetricHistoryPoint[]>
})

function onRangeChange(_range: string) {
  /* 可选 */
}

let timer = 0
async function load() {
  try {
    a.value = await getAlarms()
  } catch (_) {
    /* mock兜底 */
  }
}
onMounted(() => {
  refreshEngineState()
  load()
  timer = window.setInterval(load, Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000))
  // 规则配置统一由后端管理 (判定/收敛/升级均在服务端执行)
  getAlarmRules()
    .then((rules) => {
      if (Array.isArray(rules) && rules.length) {
        localRules.value = rules
        refreshEngineState()
      }
    })
    .catch(() => {})
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
/* Tab 切换 */
.tv-btn {
  padding: 6px 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg2);
  color: var(--txt2);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.15s;
}
.tv-btn:hover {
  border-color: var(--cyan);
  color: #fff;
}
.tv-btn.on {
  background: rgba(34, 227, 255, 0.12);
  border-color: var(--cyan);
  color: var(--cyan);
  font-weight: 600;
}

/* 跳转规则引擎按钮 */
.go-rule-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid rgba(34, 227, 255, 0.5);
  border-radius: 8px;
  background: linear-gradient(90deg, rgba(34, 227, 255, 0.18), rgba(34, 227, 255, 0.06));
  color: var(--cyan);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}
.go-rule-btn:hover {
  background: linear-gradient(90deg, rgba(34, 227, 255, 0.32), rgba(34, 227, 255, 0.12));
  box-shadow: 0 0 12px rgba(34, 227, 255, 0.25);
  color: #fff;
}
.go-rule-btn svg {
  flex-shrink: 0;
}

/* 规则卡片 */
.pwr-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
}
.pwr-card.primary {
  border-left: 3px solid var(--cyan);
}
.pwr-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.pwr-head h3 {
  font-size: 14px;
  font-weight: 700;
  margin: 0;
}
.pwr-head .sub {
  font-size: 11px;
  color: var(--txt3);
  display: block;
  margin-top: 2px;
}

/* 规则行 */
.rule-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}
.rule-row:last-child {
  border-bottom: none;
}
.rule-info {
  flex: 1;
  min-width: 0;
}
.rule-name {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--txt);
  display: flex;
  align-items: center;
  gap: 6px;
}
.rule-meta {
  font-size: 10.5px;
  color: var(--txt3);
  margin-top: 2px;
  display: flex;
  gap: 8px;
}
.rule-meta .mono {
  color: var(--txt2);
  font-size: 10px;
}
.rule-actions {
  flex-shrink: 0;
}
.rule-btn {
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--line);
  font-size: 10.5px;
  cursor: pointer;
  background: var(--bg2);
  color: var(--txt2);
  transition: all 0.15s;
}
.rule-btn.on {
  background: rgba(43, 212, 122, 0.12);
  border-color: var(--green);
  color: var(--green);
}
.rule-btn.off {
  background: rgba(255, 176, 32, 0.08);
  border-color: rgba(255, 176, 32, 0.3);
  color: var(--amber);
}
.rule-btn:hover {
  border-color: var(--cyan);
}
.tag.tiny {
  font-size: 8px;
  padding: 1px 5px;
}

/* 系统徽章 */
.sys-badge {
  font-size: 10.5px;
  color: var(--cyan);
  font-weight: 600;
}

/* 表格行高亮 */
.row-crit {
  background: linear-gradient(90deg, rgba(255, 77, 94, 0.06), transparent);
}
.row-warn {
  background: linear-gradient(90deg, rgba(255, 176, 32, 0.04), transparent);
}
.desc-cell {
  max-width: 280px;
}

/* ===== 告警历史虚拟滚动表格 ===== */
.hist-thead,
.hist-row {
  display: grid;
  grid-template-columns: 70px 70px 1fr 120px 70px 120px 80px;
  align-items: center;
}
.hist-thead {
  position: sticky;
  top: 0;
  z-index: 2;
  background: var(--bg);
  border-bottom: 1px solid var(--line);
}
.hist-thead .hc {
  font-size: 11px;
  color: var(--txt3);
  font-weight: 500;
  padding: 8px 10px;
}
.hist-virtual :deep(.vl-row) {
  border-bottom: 1px solid var(--td-line);
}
.hist-virtual :deep(.vl-row:hover) {
  background: rgba(34, 227, 255, 0.03);
}
.hist-row .hc {
  font-size: 12px;
  color: var(--txt);
  padding: 6px 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hist-row .w-msg {
  white-space: normal;
}
.hist-row .w-lv,
.hist-row .w-st,
.hist-row .w-auto {
  text-align: center;
}

/* 操作按钮 */
.act-btn {
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--line);
  font-size: 10px;
  cursor: pointer;
  background: var(--bg2);
  color: var(--txt2);
  transition: all 0.15s;
}
.act-btn.ack {
  border-color: var(--cyan);
  color: var(--cyan);
}
.act-btn.ticket {
  border-color: var(--purple, #a78bfa);
  color: var(--purple, #a78bfa);
}
.act-btn.ticket:hover {
  background: rgba(167, 139, 250, 0.12);
}
.act-btn.runbook {
  border-color: var(--green, #2bd47a);
  color: var(--green, #2bd47a);
}
.act-btn.runbook:hover {
  background: rgba(43, 212, 122, 0.1);
}

/* 关联处置预案弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 60;
}
.modal {
  width: 560px;
  max-width: 92vw;
  max-height: 86vh;
  overflow: auto;
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 18px;
}
.modal-h {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 12px;
}
.rel-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.rel-item {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
}
.rel-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  font-size: 13px;
}
.rel-sum {
  font-size: 12px;
  color: var(--muted);
  margin: 6px 0;
}
.rel-steps {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--txt2);
}
.rel-steps li {
  margin-bottom: 3px;
}
.modal-f {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
  gap: 10px;
}
.btn {
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt);
  border-radius: 8px;
  padding: 7px 14px;
  cursor: pointer;
  font-size: 13px;
}
.btn.primary {
  background: var(--cyan);
  color: #04222b;
  border-color: var(--cyan);
  font-weight: 600;
}
.btn.sm {
  padding: 5px 12px;
  font-size: 12px;
  margin-top: 4px;
}
.center {
  text-align: center;
  padding: 14px;
}

/* 处理反馈弹窗 */
.fb-modal {
  width: 560px;
}
.fb-subj {
  font-size: 12px;
  color: var(--txt3);
  margin: 4px 0 12px;
}
.fb-scn {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 12px;
}
.fb-scn-tabs {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
}
.fb-scn-tabs button {
  padding: 5px 11px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 12px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt2);
}
.fb-scn-tabs button.on {
  background: rgba(34, 211, 238, 0.14);
  color: var(--cyan);
  border-color: rgba(34, 211, 238, 0.5);
}
.fb-scn-body {
  font-size: 12px;
  line-height: 1.6;
  color: var(--txt2);
  min-height: 60px;
  margin-bottom: 10px;
}
.fb-scn-body .cause {
  color: var(--amber);
}
.fb-scn-body .fix {
  color: var(--green);
}
.fb-scn-body .steps {
  margin: 0;
  padding-left: 18px;
}
.fb-scn-body .steps li {
  margin-bottom: 4px;
}
.fb-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.fb-row.col {
  flex-direction: column;
  align-items: stretch;
}
.fb-label {
  font-size: 12px;
  color: var(--txt2);
  flex: none;
  width: 60px;
}
.fb-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.fb-tag {
  padding: 5px 12px;
  border-radius: 7px;
  cursor: pointer;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt2);
  font-size: 12px;
}
.fb-tag.on {
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  color: #04121f;
  border-color: transparent;
  font-weight: 700;
}
.fb-text {
  width: 100%;
  resize: vertical;
  border-radius: 8px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt);
  padding: 8px 10px;
  font-size: 12px;
  line-height: 1.5;
}
.fb-records {
  border-top: 1px dashed var(--line);
  margin-top: 6px;
  padding-top: 10px;
}
.fb-rec-title {
  font-size: 12px;
  color: var(--txt3);
  margin-bottom: 6px;
}
.fb-rec {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11.5px;
  padding: 4px 0;
}
.fb-rec-tag {
  padding: 2px 8px;
  border-radius: 5px;
  background: rgba(34, 211, 238, 0.14);
  color: var(--cyan);
  flex: none;
}
.fb-rec-note {
  color: var(--txt2);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fb-rec-time {
  color: var(--txt3);
  flex: none;
  font-variant-numeric: tabular-nums;
}
.act-btn.ack:hover {
  background: rgba(34, 227, 255, 0.1);
}
.act-btn.resolve {
  border-color: var(--green);
  color: var(--green);
}
.act-btn.resolve:hover {
  background: rgba(43, 212, 122, 0.1);
}
.act-btn.done {
  border-color: rgba(255, 255, 255, 0.1);
  color: var(--txt3);
  cursor: default;
}

/* 联动成功提示 */
.toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(34, 227, 255, 0.14);
  border: 1px solid var(--cyan);
  color: var(--cyan);
  padding: 10px 20px;
  border-radius: 10px;
  font-size: 13px;
  z-index: 999;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(6px);
}
.fade-enter-active,
.fade-leave-active {
  transition:
    opacity 0.3s,
    transform 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(8px);
}
</style>
