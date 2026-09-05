<template>
  <div class="page-wrap">
    <div class="view-head">
      <div class="vh-icon">
        <svg
          viewBox="0 0 24 24"
          width="22"
          height="22"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
        >
          <path
            d="M12 2v6M12 22v-6M2 12h6M22 12h-6M5 5l4 4M19 5l-4 4M5 19l4-4M19 19l-4-4"
            stroke-linecap="round"
          />
        </svg>
      </div>
      <div>
        <h1>{{ t.title }}</h1>
        <div class="sub">{{ t.sub }}</div>
      </div>
      <div class="vh-right">
        <button v-if="result" class="btn-ghost" @click="exportReport">{{ t.export }}</button>
      </div>
    </div>

    <!-- 控制区: 候选故障源 + 传播范围 -->
    <div class="card">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div class="lg:col-span-2">
          <label class="block text-xs mb-1" style="color: var(--txt2)">{{ t.selectFault }}</label>
          <select v-model="selectedIds" multiple class="inp" style="height: 160px" size="8">
            <option v-for="s in sources" :key="s.id" :value="s.id">
              [{{ s.category }}] {{ s.label }} · {{ s.roomCode || '—' }}
              <template v-if="s.riskHint"> ⚠ {{ s.riskHint }}</template>
              <template v-else> (H{{ s.health }})</template>
            </option>
          </select>
          <p class="text-xs mt-1" style="color: var(--txt3)">{{ t.multiSelectHint }}</p>
        </div>
        <div>
          <label class="block text-xs mb-2" style="color: var(--txt2)">{{ t.scope }}</label>
          <div class="space-y-2">
            <label class="flex items-center gap-2 text-sm" style="color: var(--txt)">
              <input type="checkbox" v-model="scope.power" /> {{ t.scopePower }}
            </label>
            <label class="flex items-center gap-2 text-sm" style="color: var(--txt)">
              <input type="checkbox" v-model="scope.cool" /> {{ t.scopeCool }}
            </label>
            <label class="flex items-center gap-2 text-sm" style="color: var(--txt)">
              <input type="checkbox" v-model="scope.network" /> {{ t.scopeNetwork }}
            </label>
            <label class="flex items-center gap-2 text-sm" style="color: var(--txt)">
              <input type="checkbox" v-model="scope.business" /> {{ t.scopeBusiness }}
            </label>
          </div>
          <div class="flex gap-2 mt-3">
            <button
              class="btn-primary flex-1"
              @click="analyze"
              :disabled="!selectedIds.length || loading"
            >
              {{ loading ? t.analyzing : t.analyze }}
            </button>
            <button class="btn-ghost" @click="reset">{{ t.reset }}</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 故障源遥测可视化 (选中单个源时展示健康/负载 + 实时测点趋势) -->
    <div v-if="selectedIds.length === 1 && selSource" class="card">
      <div class="card-head">
        <div class="card-title">{{ t.telemetry }}</div>
        <span class="text-xs" style="color: var(--txt3)">{{ t.telemetryTip }}</span>
      </div>
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="card" style="padding: 12px; text-align: center; border-color: var(--line)">
          <div class="text-2xl font-bold" :style="{ color: healthColor(selSource.health) }">
            {{ selSource.health }}
          </div>
          <div class="text-xs mt-1" style="color: var(--txt2)">{{ t.health }}</div>
        </div>
        <div class="card" style="padding: 12px; text-align: center; border-color: var(--line)">
          <div class="text-2xl font-bold" :style="{ color: loadColor(selSource.loadPct) }">
            {{ selSource.loadPct }}%
          </div>
          <div class="text-xs mt-1" style="color: var(--txt2)">{{ t.load }}</div>
        </div>
        <div class="card" style="padding: 12px; text-align: center; border-color: var(--line)">
          <div class="text-2xl font-bold" style="color: var(--txt-strong)">
            {{ selSource.status || '—' }}
          </div>
          <div class="text-xs mt-1" style="color: var(--txt2)">{{ t.colStatus }}</div>
        </div>
        <div class="card" style="padding: 12px; text-align: center; border-color: var(--line)">
          <div class="text-2xl font-bold" style="color: var(--txt-strong)">
            {{ selSource.roomCode || '—' }}
          </div>
          <div class="text-xs mt-1" style="color: var(--txt2)">{{ t.room }}</div>
        </div>
      </div>
      <div class="mt-3 space-y-2">
        <div>
          <div class="flex justify-between text-xs" style="color: var(--txt2)">
            <span>{{ t.health }}</span
            ><span>{{ selSource.health }}/100</span>
          </div>
          <div class="pbar">
            <i
              :style="{ width: selSource.health + '%', background: healthBar(selSource.health) }"
            ></i>
          </div>
        </div>
        <div>
          <div class="flex justify-between text-xs" style="color: var(--txt2)">
            <span>{{ t.load }}</span
            ><span>{{ selSource.loadPct }}%</span>
          </div>
          <div class="pbar">
            <i
              :style="{
                width: Math.min(100, selSource.loadPct) + '%',
                background: loadBar(selSource.loadPct),
              }"
            ></i>
          </div>
        </div>
      </div>
      <div class="mt-3">
        <div class="text-xs mb-1" style="color: var(--txt2)">{{ t.telemetryRealtime }}</div>
        <div v-if="realtimeLoading" class="text-xs" style="color: var(--txt3)">
          {{ t.analyzing }}
        </div>
        <div v-else-if="realtimePoints.length" class="flex flex-wrap gap-2">
          <span v-for="p in realtimePoints" :key="p.metric_name" class="tag"
            >{{ p.metric_name }}: {{ p.value }}{{ p.unit || '' }}</span
          >
        </div>
        <div v-else class="text-xs" style="color: var(--txt3)">{{ telemetryNote }}</div>
      </div>
    </div>

    <div v-if="loading" class="loading-box">
      <div class="spinner"></div>
      <span>{{ t.analyzing }}</span>
    </div>

    <div v-if="analyzeError" class="result bad" style="margin-top: 8px">
      <span class="r-ic">!</span>{{ analyzeError }}
      <button class="btn-ghost" style="margin-left: 8px; padding: 4px 10px" @click="analyze">
        {{ t.retry || '重试' }}
      </button>
    </div>

    <template v-else-if="result">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <!-- 影响链路图 (按 hop 分层) -->
        <div class="lg:col-span-2 card">
          <h3 class="card-title mb-3">{{ t.impactChain }}</h3>
          <svg
            :viewBox="`0 0 ${svgW} ${svgH}`"
            class="w-full"
            style="min-height: 320px"
            role="img"
            :aria-label="`${t.impactChain} · ${t.affectedCount} ${result.summary.affectedCount}`"
          >
            <!-- 跳数轴：纵向分层代表影响传播跳数，此前无任何层级标签 -->
            <text
              v-for="(L, i) in layerNodes"
              :key="'hk' + i"
              x="6"
              :y="50 + i * LAYER_GAP - 24"
              fill="#8595ad"
              font-size="10"
            >
              {{ hopText(L.hop) }}
            </text>
            <line
              v-for="(e, i) in drawEdges"
              :key="'e' + i"
              :x1="e.x1"
              :y1="e.y1"
              :x2="e.x2"
              :y2="e.y2"
              :stroke="e.type === 'it_feed' ? '#f59e0b' : e.critical ? '#dc2626' : '#cbd5e1'"
              :stroke-width="e.type === 'it_feed' ? 1.2 : e.critical ? 3 : 1.5"
              :stroke-dasharray="e.type === 'it_feed' ? '4 3' : ''"
            />
            <g v-for="d in drawNodes" :key="d.id">
              <title>{{ nodeTitle(d) }}</title>
              <circle
                :cx="d.x"
                :cy="d.y"
                r="13"
                :fill="
                  d.state === 'fault' ? '#dc2626' : d.state === 'affected' ? '#f59e0b' : '#3b82f6'
                "
                :stroke="d.critical ? '#7f1d1d' : '#fff'"
                :stroke-width="d.critical ? 2.5 : 1"
              />
              <text :x="d.x" :y="d.y + 4" text-anchor="middle" fill="#fff" font-size="9">
                {{ d.short }}
              </text>
              <text :x="d.x" :y="d.y + 28" text-anchor="middle" fill="#9fb3d1" font-size="10">
                {{ d.label }}
              </text>
            </g>
          </svg>
          <div class="flex gap-4 mt-2 text-xs flex-wrap" style="color: var(--txt2)">
            <span class="flex items-center gap-1"
              ><span class="w-3 h-3 rounded-full bg-red-600 inline-block"></span
              >{{ t.faultNode }}</span
            >
            <span class="flex items-center gap-1"
              ><span class="w-3 h-3 rounded-full bg-amber-500 inline-block"></span
              >{{ t.affectedNode }}</span
            >
            <span class="flex items-center gap-1"
              ><span
                class="w-3 h-3 rounded-full border-2 border-red-900 bg-gray-100 inline-block"
              ></span
              >{{ t.critical }}</span
            >
          </div>
          <!-- 连线图例：橙虚线 / 红粗线 / 灰细线 三种编码此前完全无说明 -->
          <div class="flex gap-4 mt-1 text-xs flex-wrap" style="color: var(--txt2)">
            <span class="flex items-center gap-1"
              ><span
                style="display: inline-block; width: 18px; border-top: 2px dashed #f59e0b"
              ></span
              >{{ t.edgeItFeed }}</span
            >
            <span class="flex items-center gap-1"
              ><span
                style="display: inline-block; width: 18px; border-top: 3px solid #dc2626"
              ></span
              >{{ t.edgeCritical }}</span
            >
            <span class="flex items-center gap-1"
              ><span
                style="display: inline-block; width: 18px; border-top: 1.5px solid #cbd5e1"
              ></span
              >{{ t.edgeNormal }}</span
            >
          </div>
        </div>

        <!-- 影响评估 -->
        <div class="card">
          <h3 class="card-title mb-3">{{ t.impactEval }}</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xs" style="color: var(--txt2)">{{ t.severity }}</span>
              <span class="tag" :class="sevClass(String(result.summary.severity))">{{
                sevText(String(result.summary.severity))
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-xs" style="color: var(--txt2)">{{ t.affectedCount }}</span>
              <span class="text-sm font-semibold" style="color: var(--txt-strong)">{{
                result.summary.affectedCount
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-xs" style="color: var(--txt2)">{{ t.criticalPaths }}</span>
              <span class="text-sm font-semibold" style="color: var(--txt-strong)">{{
                result.summary.criticalPaths
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-xs" style="color: var(--txt2)">{{ t.bizCount }}</span>
              <span class="text-sm font-semibold" style="color: var(--txt-strong)">{{
                result.summary.bizCount
              }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-xs" style="color: var(--txt2)">{{ t.slaRisk }}</span>
              <span
                class="text-sm font-semibold"
                :style="{
                  color: result.summary.slaRisk === 'high' ? 'var(--red)' : 'var(--green)',
                }"
              >
                {{
                  result.summary.slaRisk === 'high'
                    ? t.sevHigh
                    : result.summary.slaRisk === 'medium'
                      ? t.sevMedium
                      : t.sevLow
                }}
              </span>
            </div>
            <div class="pt-2" style="border-top: 1px solid var(--line)">
              <p class="text-xs mb-1" style="color: var(--txt2)">{{ t.suggestion }}</p>
              <p class="text-sm leading-relaxed" style="color: var(--txt)">
                {{ result.suggestion }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- 受影响业务域 / SLA 风险 -->
      <div v-if="result.businesses.length" class="card mt-4">
        <h3 class="card-title mb-3">{{ t.bizDomain }}</h3>
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          <div
            v-for="b in result.businesses"
            :key="b.business"
            class="card"
            style="padding: 12px; border-color: var(--line)"
            :style="
              b.severity === 'critical'
                ? 'border-color:rgba(255,77,94,.5);background:rgba(255,77,94,.06)'
                : ''
            "
          >
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold" style="color: var(--txt-strong)">{{
                b.business
              }}</span>
              <span class="tag" :class="sevClass(b.severity)">{{ sevText(b.severity) }}</span>
            </div>
            <div class="mt-2 text-xs space-y-1" style="color: var(--txt2)">
              <div class="flex justify-between">
                <span>{{ t.bizSla }}</span
                ><span style="color: var(--txt)">{{ b.sla }}</span>
              </div>
              <div class="flex justify-between">
                <span>{{ t.bizAffected }}</span
                ><span style="color: var(--txt)">{{ b.affectedDevices }}</span>
              </div>
              <div class="flex justify-between">
                <span>{{ t.critical }}</span
                ><span style="color: var(--txt)">{{ b.criticalDevices }}</span>
              </div>
              <p class="pt-1" style="color: var(--txt3)">{{ b.note }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 处置缓解建议 (结构化动作清单) -->
      <div v-if="result.mitigations && result.mitigations.length" class="card mt-4">
        <h3 class="card-title mb-3">{{ t.mitigations }}</h3>
        <div class="space-y-2">
          <div
            v-for="m in result.mitigations"
            :key="m.seq"
            class="flex items-start gap-3 card"
            style="padding: 12px; border-color: var(--line)"
            :style="
              m.priority === 'P0'
                ? 'border-color:rgba(255,77,94,.5);background:rgba(255,77,94,.06)'
                : m.priority === 'P1'
                  ? 'border-color:rgba(255,176,32,.5);background:rgba(255,176,32,.06)'
                  : ''
            "
          >
            <span class="prio" :class="'p-' + m.priority">{{ m.priority }}</span>
            <div class="min-w-0">
              <div class="text-sm font-semibold" style="color: var(--txt-strong)">
                {{ m.action }} ·
                <span class="font-normal" style="color: var(--txt2)">{{ m.target }}</span>
              </div>
              <div class="text-xs mt-0.5 leading-relaxed" style="color: var(--txt2)">
                {{ m.detail }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 受影响资产清单 -->
      <div class="card mt-4">
        <h3 class="card-title mb-3">{{ t.affectedList }}</h3>
        <div class="table-wrap" style="max-height: 320px">
          <table class="w-full">
            <thead>
              <tr>
                <th>{{ t.colAsset }}</th>
                <th>{{ t.colType }}</th>
                <th>{{ t.colRoom }}</th>
                <th>{{ t.colHealth }}</th>
                <th>{{ t.colHop }}</th>
                <th>{{ t.colCritical }}</th>
                <th>{{ t.colService }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="n in affectedNodes" :key="n.id">
                <td class="cell-strong">{{ n.label }}</td>
                <td>{{ n.category }}</td>
                <td>{{ n.roomCode || '—' }}</td>
                <td>{{ n.health }}</td>
                <td>{{ n.hop }}</td>
                <td>
                  <span class="tag" :class="n.critical ? 'r' : ''">{{
                    n.critical ? t.critical : t.normal
                  }}</span>
                </td>
                <td>{{ n.business || '—' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 分析报告存档 + 会签 + 分级推送 -->
      <div class="card mt-4">
        <div class="card-head">
          <div class="card-title">{{ t.history }}</div>
          <button
            :disabled="savingHistory || !result.faultIds.length"
            @click="saveReport"
            class="btn-primary"
          >
            {{ t.historySave }}
          </button>
        </div>
        <div v-if="historyLoading" class="text-xs" style="color: var(--txt3)">
          {{ t.analyzing }}
        </div>
        <div v-else-if="historyError" class="result bad" style="margin-top: 8px">
          <span class="r-ic">!</span>{{ historyError }}
          <button
            class="btn-ghost"
            style="margin-left: 8px; padding: 4px 10px"
            @click="loadHistory"
          >
            {{ t.retry || '重试' }}
          </button>
        </div>
        <div v-else-if="!historyList.length" class="empty-box">{{ t.historyEmpty }}</div>
        <div v-else class="space-y-2">
          <div v-for="h in historyList" :key="h.id" class="card" style="padding: 12px">
            <div class="flex items-center justify-between">
              <div class="text-sm font-medium" style="color: var(--txt-strong)">
                {{ h.title || '#' + h.id }}
                <span class="tag" style="margin-left: 8px" :class="sevClass(h.severity)">{{
                  h.severity
                }}</span>
              </div>
              <div class="text-xs" style="color: var(--txt3)">{{ h.createdAt }}</div>
            </div>
            <div class="text-xs mt-1" style="color: var(--txt2)">
              {{ t.historyCreatedBy }}: {{ h.createdBy || '—' }} · {{ t.historySigners }}:
              {{ h.signers.length ? h.signers.join('、') : '—' }}
              <span v-if="h.pushed" class="ml-2" style="color: var(--green)"
                >· {{ t.historyPushed }}</span
              >
            </div>
            <div class="flex items-center gap-2 mt-2">
              <input
                v-model="signerName"
                :placeholder="t.signPlaceholder"
                class="inp"
                style="flex: 1"
              />
              <button @click="signReport(h.id)" class="btn-ghost" style="padding: 7px 12px">
                {{ t.historySign }}
              </button>
              <button @click="pushReport(h)" class="btn-ghost" style="padding: 7px 12px">
                {{ t.historyPush }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <div v-else class="card empty-box">{{ t.emptyHint }}</div>

    <div v-if="srcError" class="result bad" style="margin-top: 8px">
      <span class="r-ic">!</span>{{ t.offlineMsg || '后端不可达, 已使用离线模拟数据。' }}
      <button class="btn-ghost" style="margin-left: 8px; padding: 4px 10px" @click="loadSources">
        {{ t.retry || '重试' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  getFaultSources,
  analyzeFaultImpact,
  getFaultImpactHistory,
  saveFaultImpactHistory,
  signFaultImpactHistory,
  pushFaultImpactHistory,
  getDeviceRealtime,
} from '@/api'
import type { FaultImpactResp, FaultSourceNode, AnalysisHistory } from '@/types'
import { toErrorMessage } from '@/composables/useAsyncPage'
import { downloadText } from '@/utils/export'
import { useToast } from '@/hooks/useToast'

const toast = useToast()
const { tm } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (tm('faultImpact') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})

const sources = ref<FaultSourceNode[]>([])
const selectedIds = ref<number[]>([])
const scope = reactive({ power: true, cool: true, network: true, business: true })
const loading = ref(false)
const result = ref<FaultImpactResp | null>(null)
const srcError = ref(false) // 仅拓扑(故障源)加载失败
const analyzeError = ref('') // 仅影响分析(analyze)失败, 与 srcError 解耦

// ---- 故障源遥测可视化 ----
const realtimePoints = ref<{ metric_name: string; value: number; unit?: string }[]>([])
const realtimeLoading = ref(false)
const telemetryNote = ref('')
const selSource = computed(() =>
  selectedIds.value.length === 1
    ? sources.value.find((s) => s.id === selectedIds.value[0]) || null
    : null,
)

watch(selectedIds, async (ids) => {
  realtimePoints.value = []
  telemetryNote.value = ''
  if (ids.length !== 1) return
  const src = sources.value.find((s) => s.id === ids[0])
  if (!src) return
  // twin_graph 节点 id 通常无外部设备映射 -> 实时遥测 best-effort
  realtimeLoading.value = true
  try {
    const r = await getDeviceRealtime(String(src.id))
    if (r && r.points && r.points.length) {
      realtimePoints.value = r.points.slice(0, 8)
      telemetryNote.value = ''
    } else {
      telemetryNote.value = t.telemetryNoDevice
    }
  } catch {
    telemetryNote.value = t.telemetryOffline
  } finally {
    realtimeLoading.value = false
  }
})

// ---- 颜色辅助 ----
const healthColor = (h: number) =>
  h <= 40 ? 'var(--red)' : h <= 70 ? 'var(--amber)' : 'var(--green)'
const loadColor = (l: number) =>
  l >= 90 ? 'var(--red)' : l >= 75 ? 'var(--amber)' : 'var(--green)'
const healthBar = (h: number) =>
  h <= 40 ? 'var(--red)' : h <= 70 ? 'var(--amber)' : 'var(--green)'
const loadBar = (l: number) => (l >= 90 ? 'var(--red)' : l >= 75 ? 'var(--amber)' : 'var(--green)')
const sevClass = (s: string | number) => {
  const k = String(s)
  return k === 'critical' ? 'r' : k === 'high' ? 'a' : ''
}

// ---- 分析报告存档 + 会签 ----
const historyList = ref<AnalysisHistory[]>([])
const historyLoading = ref(false)
const historyError = ref('')
const savingHistory = ref(false)
const signerName = ref('')

async function loadHistory() {
  historyLoading.value = true
  historyError.value = ''
  try {
    historyList.value = await getFaultImpactHistory(50)
  } catch (e) {
    historyError.value = toErrorMessage(e) || '历史报告加载失败'
    historyList.value = []
  } finally {
    historyLoading.value = false
  }
}

async function saveReport() {
  if (!result.value) return
  savingHistory.value = true
  try {
    await saveFaultImpactHistory({
      title: `${t.previewFromDrill || '影响分析'} ${new Date().toLocaleString()}`,
      faultIds: result.value.faultIds,
      severity: String(result.value.summary.severity || 'low'),
      summary: result.value.summary,
      businesses: result.value.businesses,
      mitigations: result.value.mitigations,
      createdBy: 'current_user',
    })
    await loadHistory()
    toast.success(t.saveSuccess)
  } catch (e) {
    toast.error(toErrorMessage(e) || '报告保存失败')
  } finally {
    savingHistory.value = false
  }
}

async function signReport(id: number) {
  if (!signerName.value.trim()) return
  try {
    await signFaultImpactHistory(id, signerName.value.trim())
    await loadHistory()
    toast.success(t.signSuccess)
  } catch (e) {
    toast.error(toErrorMessage(e) || '会签失败')
  }
}

/** 推送通道展示名 (后端按 severity 返回通道编码, 此处仅做展示映射) */
const PUSH_CHANNEL_NAMES: Record<string, string> = {
  wecom: '企业微信',
  sms: '短信',
  email: '邮件',
}

async function pushReport(h: AnalysisHistory) {
  try {
    // 真实推送: 后端持久化 pushed 标记并按 severity 返回实际送达通道, 不做假成功
    const r = await pushFaultImpactHistory(h.id)
    const hh = historyList.value.find((x) => x.id === h.id)
    if (hh && r) hh.pushed = true
    const channels = (r?.pushedChannels || []).map((c) => PUSH_CHANNEL_NAMES[c] || c)
    toast.success(channels.length ? `${t.pushSuccess}（${channels.join(' / ')}）` : t.pushSuccess)
  } catch (e) {
    toast.error(toErrorMessage(e) || '分级推送失败')
  }
}

async function loadSources() {
  try {
    const r = await getFaultSources()
    sources.value = r.nodes || []
    srcError.value = false
  } catch {
    srcError.value = true
    sources.value = []
  }
}

onMounted(() => {
  // D7: 拓扑与历史无依赖, 并发发起避免串行瀑布 (原重复拉拓扑的第二处 onMounted 已移除)
  void Promise.all([loadSources(), loadHistory()])
})

// ---- SVG 布局: 按 hop 分层, 每层最多 10 个, 其余折叠为 "+N" ----
const MAX_PER_LAYER = 10
const layerNodes = computed(() => {
  const res = result.value
  if (!res) return []
  // fault 层 (hop0) + 各 affected 层
  const byHop: Record<number, typeof res.nodes> = {}
  for (const n of res.nodes) {
    if (n.state === 'normal') continue
    const h = n.hop
    ;(byHop[h] ||= []).push(n)
  }
  const maxHop = Math.max(0, ...Object.keys(byHop).map(Number))
  const layers: Array<{ hop: number; nodes: typeof res.nodes; hidden: number }> = []
  for (let h = 0; h <= maxHop; h++) {
    const arr = byHop[h] || []
    const shown = arr.slice(0, MAX_PER_LAYER)
    layers.push({ hop: h, nodes: shown, hidden: Math.max(0, arr.length - shown.length) })
  }
  return layers
})

const svgW = 760
const svgH = computed(() => Math.max(320, layerNodes.value.length * 110))
const LAYER_GAP = 110
const NODE_GAP = 70

const drawNodes = computed(() => {
  const out: Array<{
    id: number
    x: number
    y: number
    label: string
    short: string
    state: string
    critical: boolean
    hop: number
    full: string
    hidden: number
  }> = []
  layerNodes.value.forEach((layer, li) => {
    const y = 50 + li * LAYER_GAP
    const total = layer.nodes.length
    layer.nodes.forEach((n, ni) => {
      const x = svgW / 2 + (ni - (total - 1) / 2) * NODE_GAP
      out.push({
        id: n.id,
        x,
        y,
        label: n.label.length > 10 ? n.label.slice(0, 9) + '…' : n.label,
        short: String(n.id).slice(-2),
        state: n.state,
        critical: n.critical,
        hop: layer.hop,
        full: n.label,
        hidden: 0,
      })
    })
    if (layer.hidden > 0) {
      const x = svgW / 2 + (total - (total - 1) / 2) * NODE_GAP + NODE_GAP / 2
      out.push({
        id: -layer.hop - 1,
        x,
        y,
        label: `+${layer.hidden}`,
        short: '+',
        state: 'affected',
        critical: false,
        hop: layer.hop,
        full: '',
        hidden: layer.hidden,
      })
    }
  })
  return out
})
/** 跳数轴标签：纵向分层即传播跳数，无标签则读不出层级含义 */
function hopText(n: number) {
  return String(t.hopLabel || '第 {n} 跳').replace('{n}', String(n))
}
/** 折叠节点提示：仅有 "+" 号无法得知还有多少节点被折叠 */
function moreText(n: number) {
  return String(t.moreNodes || '另有 {n} 个节点未展示').replace('{n}', String(n))
}
/** 节点悬停文案：标签超 10 字会被截断，用 title 兜底显示全名与跳数 */
function nodeTitle(d: {
  full: string
  state: string
  critical: boolean
  hop: number
  hidden: number
}) {
  if (d.hidden) return moreText(d.hidden)
  const st = d.state === 'fault' ? String(t.faultNode) : String(t.affectedNode)
  return `${d.full} · ${st} · ${hopText(d.hop)}${d.critical ? ' · ' + String(t.critical) : ''}`
}

const nodePos = computed(() => {
  const m: Record<number, { x: number; y: number }> = {}
  drawNodes.value.forEach((d) => (m[d.id] = { x: d.x, y: d.y }))
  return m
})

const drawEdges = computed(() => {
  const res = result.value
  const out: Array<{
    x1: number
    y1: number
    x2: number
    y2: number
    type: string
    critical: boolean
  }> = []
  if (!res) return out
  const pos = nodePos.value
  for (const e of res.edges) {
    const a = pos[e.source]
    const b = pos[e.target]
    if (!a || !b) continue
    out.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, type: e.type, critical: false })
  }
  return out
})

const affectedNodes = computed(() =>
  (result.value?.nodes || [])
    .filter((n) => n.state !== 'normal')
    .sort((a, b) => a.hop - b.hop || a.label.localeCompare(b.label)),
)

async function analyze() {
  if (!selectedIds.value.length) return
  loading.value = true
  analyzeError.value = ''
  try {
    const r = await analyzeFaultImpact({ faultIds: selectedIds.value, scope: { ...scope } })
    result.value = r
  } catch (e) {
    analyzeError.value = toErrorMessage(e) || '影响分析失败'
  } finally {
    loading.value = false
  }
}

function reset() {
  selectedIds.value = []
  result.value = null
}

function sevText(s: string | number) {
  const key = String(s)
  const m: Record<string, string> = {
    critical: t.sevCritical,
    high: t.sevHigh,
    medium: t.sevMedium,
    low: t.sevLow,
  }
  return m[key] || key
}

function exportReport() {
  const r = result.value
  if (!r) return
  const lines: string[] = []
  lines.push('==== 故障影响分析报告 ====')
  lines.push(`生成时间: ${r.generatedAt}`)
  lines.push(`严重级别: ${sevText(String(r.summary.severity))}`)
  lines.push(
    `故障源数: ${r.summary.faultCount}  受影响节点: ${r.summary.affectedCount}  关键链路: ${r.summary.criticalPaths}  SLA风险: ${r.summary.slaRisk}`,
  )
  lines.push('')
  lines.push('--- 故障源 ---')
  r.nodes
    .filter((n) => n.state === 'fault')
    .forEach((n) => lines.push(`  [${n.category}] ${n.label} (${n.roomCode || '—'})`))
  lines.push('')
  lines.push('--- 受影响业务域 ---')
  r.businesses.forEach((b) =>
    lines.push(
      `  ${b.business} (SLA ${b.sla}) 受影响设备 ${b.affectedDevices} 关键 ${b.criticalDevices} [${sevText(b.severity)}]`,
    ),
  )
  lines.push('')
  lines.push('--- 受影响资产 ---')
  affectedNodes.value.forEach((n) =>
    lines.push(
      `  ${n.label} | ${n.category} | 机房 ${n.roomCode || '—'} | 跳数 ${n.hop} | ${n.critical ? '关键' : '普通'} | ${n.business || '—'}`,
    ),
  )
  lines.push('')
  lines.push('--- 处置建议 ---')
  lines.push(`  ${r.suggestion}`)
  if (r.mitigations && r.mitigations.length) {
    lines.push('')
    lines.push('--- 处置缓解措施清单 ---')
    r.mitigations.forEach((m) =>
      lines.push(`  [${m.priority}] ${m.action} · ${m.target} — ${m.detail}`),
    )
  }
  downloadText(`fault-impact-${Date.now()}.txt`, lines.join('\n'))
}
</script>
