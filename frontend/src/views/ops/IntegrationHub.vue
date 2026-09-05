<template>
  <div class="ihub">
    <!-- 顶部标题 -->
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
            d="M9 7H6a3 3 0 0 0-3 3v7a3 3 0 0 0 3 3h12a3 3 0 0 0 3-3v-7a3 3 0 0 0-3-3h-3"
            stroke-linecap="round"
          />
          <path d="M12 3v7M9 7l3-3 3 3" stroke-linecap="round" stroke-linejoin="round" />
          <circle cx="9" cy="14" r="1.2" />
          <circle cx="15" cy="14" r="1.2" />
        </svg>
      </div>
      <div>
        <h1>{{ t.title }}</h1>
        <div class="sub">{{ t.sub }}</div>
      </div>
      <div class="pill" :class="overallCls">
        <span class="dot" :class="overallDot"></span>{{ overallText }}
      </div>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        v-for="tb in tabs"
        :key="tb.k"
        class="tab"
        :class="{ active: activeTab === tb.k }"
        @click="activeTab = tb.k"
      >
        <span class="tab-ic">{{ tb.ic }}</span
        >{{ tb.label }}
      </button>
    </div>

    <!-- 南向接入验证 (依赖外部设备/物模型加载) -->
    <AsyncSection v-if="activeTab === 'south'" :loading="loading" :error="error" @retry="load">
      <!-- 概览统计 -->
      <div class="grid cols-4">
        <div class="card stat" v-for="s in stats" :key="s.k">
          <div class="ct"><span class="dot" :class="s.dot"></span>{{ s.label }}</div>
          <div class="cv" :style="{ color: s.color }">{{ s.value }}</div>
          <div class="cbar"><i :style="{ width: s.bar, background: s.color }"></i></div>
        </div>
      </div>

      <!-- 验证总进度 -->
      <div class="card progress-card">
        <div class="card-head">
          <div class="card-title">{{ t.verifyProgress || '验证进度' }}</div>
          <button class="btn-primary" @click="verifyAll" :disabled="verifying">
            <span v-if="verifying" class="spin-ic">◐</span
            >{{ verifying ? t.verifying : t.verifyAll }}
          </button>
        </div>
        <div class="pv">
          <div class="pv-bar"><i :style="{ width: verifyPct + '%' }"></i></div>
          <div class="pv-meta">
            <span class="tag g" v-if="passCount">{{ t.pass }} {{ passCount }}</span>
            <span class="tag r" v-if="failCount">{{ t.fail }} {{ failCount }}</span>
            <span class="tag" v-if="pendingCount">{{ t.pending }} {{ pendingCount }}</span>
            <span class="pv-pct">{{ verifyPct }}%</span>
          </div>
        </div>
      </div>

      <!-- 子系统分组 -->
      <div class="section-title">{{ t.subsystemStatus }}</div>
      <div class="space-y">
        <div v-for="grp in subsystemGroups" :key="grp.domain" class="card sub-card">
          <div class="sub-head">
            <div class="sub-id">
              <span class="dot" :class="grp.online > 0 ? 'g' : 'o'"></span>
              <span class="sub-name">{{ grp.label }}</span>
              <span class="sub-domain">{{ grp.domain }}</span>
            </div>
            <div class="sub-rate">
              <span class="rate-num" :class="grp.online > 0 ? 'ok' : ''"
                >{{ grp.online }}/{{ grp.total }}</span
              >
              <span class="rate-lab">{{ t.online }}</span>
            </div>
          </div>

          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>{{ t.colDevice }}</th>
                  <th>{{ t.colIp }}</th>
                  <th>{{ t.colProtocol }}</th>
                  <th>{{ t.colMetrics }}</th>
                  <th>{{ t.colRealtime }}</th>
                  <th>{{ t.colVerify }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="d in grp.items" :key="d.device_id">
                  <td class="cell-strong">{{ d.name || d.device_id }}</td>
                  <td class="mono">{{ d.ip }}</td>
                  <td>
                    <span class="tag b">{{ d.protocol }}</span>
                  </td>
                  <td class="mono">{{ d.metric_count }}</td>
                  <td>
                    <span v-if="rtState[d.device_id] === 'ok'" class="tag g">✓ {{ t.landed }}</span>
                    <span v-else-if="rtState[d.device_id] === 'fail'" class="tag r"
                      >✕ {{ t.notLanded }}</span
                    >
                    <span v-else class="tag">—</span>
                  </td>
                  <td>
                    <span class="tag" :class="verifyTagCls(d.device_id)">{{
                      verifyLabel(d.device_id)
                    }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="model-line">
            <span class="ml-k">{{ t.modelMatch }}:</span>
            <span v-if="modelMap[grp.domain]" class="tag g"
              >{{ modelMap[grp.domain].category_label }} ({{ modelMap[grp.domain].metrics.length }}
              {{ t.points }})</span
            >
            <span v-else class="tag r">{{ t.noModel }}</span>
          </div>
        </div>
      </div>
    </AsyncSection>

    <!-- 北向 ITSM 预集成 -->
    <div v-else>
      <div class="grid twin">
        <div class="card">
          <div class="card-head">
            <div class="card-title">{{ t.itsmConfig }}</div>
            <span class="pill b">{{ t.northLabel || 'Northbound' }}</span>
          </div>

          <div class="form-grid">
            <label class="fld">
              <span class="fl">{{ t.endpoint }}</span>
              <input v-model.trim="cfg.endpoint" class="inp" :placeholder="t.endpointPlaceholder" />
            </label>
            <label class="fld">
              <span class="fl">{{ t.authType }}</span>
              <select v-model="cfg.authType" class="inp">
                <option value="token">Bearer Token</option>
                <option value="basic">Basic Auth</option>
                <option value="oauth">OAuth2</option>
              </select>
            </label>
            <label class="fld">
              <span class="fl">{{ t.token }}</span>
              <input
                v-model.trim="cfg.token"
                type="password"
                class="inp"
                :placeholder="t.tokenPlaceholder"
              />
            </label>
            <label class="fld">
              <span class="fl">{{ t.syncScope }}</span>
              <select v-model="cfg.scope" class="inp">
                <option value="alarm">{{ t.scopeAlarm }}</option>
                <option value="ticket">{{ t.scopeTicket }}</option>
                <option value="device">{{ t.scopeDevice }}</option>
                <option value="all">{{ t.scopeAll }}</option>
              </select>
            </label>
          </div>

          <div class="act-row">
            <button class="btn-primary" @click="saveCfg">{{ t.saveCfg }}</button>
            <button class="btn-ghost" @click="testConn" :disabled="testing">
              {{ testing ? t.testing : t.testConn }}
            </button>
            <button class="btn-ghost" @click="pushSample" :disabled="testing">
              {{ t.pushSample }}
            </button>
          </div>

          <div v-if="connResult" class="result" :class="connResult.ok ? 'ok' : 'bad'">
            <span class="r-ic">{{ connResult.ok ? '✓' : '✕' }}</span
            >{{ connResult.msg }}
          </div>
        </div>

        <div class="card">
          <div class="card-head">
            <div class="card-title">{{ t.syncLog }}</div>
            <span class="pill">{{ syncLogs.length }} {{ t.records || '条' }}</span>
          </div>
          <div class="log-scroll">
            <table v-if="syncLogs.length">
              <thead>
                <tr>
                  <th>{{ t.colTime }}</th>
                  <th>{{ t.colAction }}</th>
                  <th>{{ t.colPayload }}</th>
                  <th>{{ t.colStatus }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="l in syncLogs" :key="l.id">
                  <td class="mono dim">{{ l.time }}</td>
                  <td class="cell-strong">{{ l.action }}</td>
                  <td class="mono dim clip">{{ l.payload }}</td>
                  <td>
                    <span class="tag" :class="l.ok ? 'g' : 'r'">{{
                      l.ok ? t.sent : t.failed
                    }}</span>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else class="log-empty">{{ t.emptyLog }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { getExternalDevices, getThingModels, getDeviceRealtime } from '@/api'
import type { DeviceListResponse, ThingModelDef, ExternalDeviceView } from '@/types'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { toErrorMessage } from '@/composables/useAsyncPage'

const { tm } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (tm('integrationHub') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})

const tabs = [
  { k: 'south', label: t.southLabel || '南向接入', ic: '⬇' },
  { k: 'north', label: t.northLabel || '北向 ITSM', ic: '⬆' },
]
const activeTab = ref<string>('south')
const loading = ref(false)
const error = ref('')
const verifying = ref(false)
const testing = ref(false)

const devList = ref<DeviceListResponse | null>(null)
const models = ref<ThingModelDef[]>([])
const modelMap = ref<Record<string, ThingModelDef>>({})
const rtState = ref<Record<string, 'ok' | 'fail'>>({})
const verifyState = ref<Record<string, 'pass' | 'fail' | 'pending'>>({})
const connResult = ref<{ ok: boolean; msg: string } | null>(null)

const KEY_CFG = 'e01_itsm_cfg'
const KEY_LOG = 'e01_itsm_log'
const cfg = ref({ endpoint: '', authType: 'token', token: '', scope: 'alarm' })
const syncLogs = ref<any[]>([])

// 子系统分组（域 → 展示名）
const DOMAIN_LABELS: Record<string, string> = {
  video: '视频监控',
  access: '门禁',
  fire: '消防',
  power: '供配电',
  hvac: '制冷空调',
  network: '网络',
  security: '安防',
}
const subsystemGroups = computed(() => {
  if (!devList.value) return []
  const groups: Record<
    string,
    { domain: string; label: string; total: number; online: number; items: ExternalDeviceView[] }
  > = {}
  devList.value.items.forEach((d) => {
    const domain = d.domain || 'other'
    if (!groups[domain])
      groups[domain] = {
        domain,
        label: DOMAIN_LABELS[domain] || domain,
        total: 0,
        online: 0,
        items: [],
      }
    groups[domain].total++
    if (d.online) groups[domain].online++
    groups[domain].items.push(d)
  })
  return Object.values(groups)
})

// ---- 概览统计 ----
const stats = computed(() => {
  const total = devList.value?.total || 0
  const online = devList.value?.online || 0
  const metrics = devList.value?.total_metrics || 0
  return [
    {
      k: 'reg',
      label: t.registered,
      value: total,
      color: 'var(--txt-strong)',
      dot: 'b',
      bar: '100%',
    },
    {
      k: 'on',
      label: t.online,
      value: online,
      color: 'var(--green)',
      dot: 'g',
      bar: total ? (online / total) * 100 + '%' : '0%',
    },
    {
      k: 'md',
      label: t.models,
      value: models.value.length,
      color: 'var(--blue)',
      dot: 'b',
      bar: '100%',
    },
    {
      k: 'mt',
      label: t.totalMetrics,
      value: metrics.toLocaleString(),
      color: 'var(--cyan)',
      dot: 'c',
      bar: '100%',
    },
  ]
})

// ---- 验证总览 ----
const passCount = computed(
  () => Object.values(verifyState.value).filter((s) => s === 'pass').length,
)
const failCount = computed(
  () => Object.values(verifyState.value).filter((s) => s === 'fail').length,
)
const pendingCount = computed(
  () => Object.values(verifyState.value).filter((s) => !s || s === 'pending').length,
)
const verifyPct = computed(() => {
  const items = devList.value?.items || []
  if (!items.length) return 0
  const done = passCount.value + failCount.value
  return Math.round((done / items.length) * 100)
})
const overallText = computed(() => {
  if (pendingCount.value === (devList.value?.items.length || 0)) return t.overallPending || '待验证'
  if (failCount.value > 0 && passCount.value > 0) return t.overallPartial || '部分通过'
  if (failCount.value > 0) return t.overallFail || '存在异常'
  if (passCount.value > 0) return t.overallOk || '全部通过'
  return t.overallPending || '待验证'
})
const overallCls = computed(() => {
  if (failCount.value > 0 && passCount.value > 0) return ''
  if (failCount.value > 0) return 'a'
  if (passCount.value > 0) return 'g'
  return ''
})
const overallDot = computed(() => {
  if (failCount.value > 0 && passCount.value > 0) return 'a'
  if (failCount.value > 0) return 'r'
  if (passCount.value > 0) return 'g'
  return 'o'
})

function verifyTagCls(id: string) {
  const s = verifyState.value[id]
  return s === 'pass' ? 'g' : s === 'fail' ? 'r' : ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [dl, ms] = await Promise.all([getExternalDevices({ limit: 1000 }), getThingModels()])
    devList.value = dl
    models.value = ms
    ms.forEach((m) => (modelMap.value[m.domain] = m))
  } catch (e: unknown) {
    devList.value = { total: 0, online: 0, offline: 0, total_metrics: 0, items: [] }
    models.value = []
    error.value = toErrorMessage(e) || '加载接入数据失败'
  } finally {
    loading.value = false
  }
}

async function verifyAll() {
  verifying.value = true
  try {
    const items = devList.value?.items || []
    for (const d of items) {
      verifyState.value[d.device_id] = 'pending'
      try {
        const rt = await getDeviceRealtime(d.device_id)
        const hasModel = !!modelMap.value[d.domain || '']
        rtState.value[d.device_id] = rt.online && rt.points.length ? 'ok' : 'fail'
        verifyState.value[d.device_id] = rt.online && rt.points.length && hasModel ? 'pass' : 'fail'
      } catch {
        rtState.value[d.device_id] = 'fail'
        verifyState.value[d.device_id] = 'fail'
      }
    }
  } finally {
    verifying.value = false
  }
}

function verifyLabel(id: string) {
  const s = verifyState.value[id]
  return s === 'pass' ? t.pass : s === 'fail' ? t.fail : t.pending
}

function loadCfg() {
  // 本地 JSON 可能因版本变更/手改损坏: 逐项容错, 损坏时保留默认配置, 避免页面初始化抛错
  try {
    const c = JSON.parse(localStorage.getItem(KEY_CFG) || 'null')
    if (c && typeof c === 'object') cfg.value = { ...cfg.value, ...c }
  } catch {
    /* 忽略损坏配置, 使用默认值 */
  }
  try {
    const logs = JSON.parse(localStorage.getItem(KEY_LOG) || '[]')
    if (Array.isArray(logs)) syncLogs.value = logs
  } catch {
    syncLogs.value = []
  }
}
function saveCfg() {
  localStorage.setItem(KEY_CFG, JSON.stringify(cfg.value))
  connResult.value = { ok: true, msg: t.cfgSaved }
}
function testConn() {
  testing.value = true
  setTimeout(() => {
    const ok = /^https?:\/\/.+/.test(cfg.value.endpoint) && !!cfg.value.token
    connResult.value = ok ? { ok: true, msg: t.connOk } : { ok: false, msg: t.connBad }
    if (ok) pushLog(t.testConn, cfg.value.endpoint, true)
    testing.value = false
  }, 400)
}
function pushSample() {
  const sample = {
    type: 'alarm.sync',
    scope: cfg.value.scope,
    ts: new Date().toISOString(),
    sample_id: 'ALM-' + Date.now(),
  }
  const ok = /^https?:\/\/.+/.test(cfg.value.endpoint) && !!cfg.value.token
  pushLog(t.pushSample, JSON.stringify(sample).slice(0, 60) + '…', ok)
  if (!ok) connResult.value = { ok: false, msg: t.connBad }
}
function pushLog(action: string, payload: string, ok: boolean) {
  syncLogs.value.unshift({
    id: 'sl' + Date.now(),
    time: new Date().toISOString().slice(0, 19).replace('T', ' '),
    action,
    payload,
    ok,
  })
  syncLogs.value = syncLogs.value.slice(0, 50)
  localStorage.setItem(KEY_LOG, JSON.stringify(syncLogs.value))
}

onMounted(() => {
  load()
  loadCfg()
})
</script>

<style scoped>
.ihub {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.vh-icon {
  width: 42px;
  height: 42px;
  border-radius: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--cyan);
  background: linear-gradient(180deg, rgba(34, 227, 255, 0.16), rgba(34, 227, 255, 0.02));
  border: 1px solid rgba(34, 227, 255, 0.35);
  box-shadow: var(--glow);
}
.sub {
  margin-top: 2px;
}
/* tabs */
.tabs {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid var(--line);
  padding-bottom: 0;
}
.tab {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 9px 16px;
  font-size: 13px;
  font-weight: 600;
  color: var(--txt2);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  border-radius: 8px 8px 0 0;
  transition: all 0.15s;
}
.tab:hover {
  color: var(--txt);
}
.tab.active {
  color: var(--cyan);
  border-bottom-color: var(--cyan);
  background: linear-gradient(180deg, rgba(34, 227, 255, 0.08), transparent);
}
.tab-ic {
  font-size: 12px;
  opacity: 0.85;
}
/* empty / loading */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 0;
  color: var(--txt2);
}
.spinner {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 3px solid var(--line);
  border-top-color: var(--cyan);
  animation: spin 1s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
/* stat cards */
.stat .cv {
  font-size: 26px;
}
/* progress */
.progress-card .pv {
  margin-top: 4px;
}
.pv-bar {
  height: 10px;
  border-radius: 6px;
  background: var(--track);
  overflow: hidden;
}
.pv-bar > i {
  display: block;
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  transition: width 0.5s ease;
}
.pv-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.pv-pct {
  margin-left: auto;
  font-size: 15px;
  font-weight: 800;
  color: var(--cyan);
  font-variant-numeric: tabular-nums;
}
/* subsystem */
.space-y {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sub-card {
  padding: 16px;
}
.sub-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.sub-id {
  display: flex;
  align-items: center;
  gap: 9px;
}
.sub-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--txt-strong);
}
.sub-domain {
  font-size: 11px;
  color: var(--txt3);
  font-family: 'SF Mono', Consolas, monospace;
  padding: 1px 7px;
  border: 1px solid var(--line);
  border-radius: 12px;
}
.sub-rate {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.rate-num {
  font-size: 16px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.rate-num.ok {
  color: var(--green);
}
.rate-lab {
  font-size: 11px;
  color: var(--txt2);
}
.cell-strong {
  font-weight: 600;
  color: var(--txt-strong);
}
.dim {
  color: var(--txt2);
}
.clip {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.model-line {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed var(--line);
  font-size: 12px;
  color: var(--txt2);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.ml-k {
  color: var(--txt2);
}
/* buttons */
.btn-primary {
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  color: #04121f;
  font-weight: 700;
  font-size: 12.5px;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  transition: 0.15s;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.btn-primary:hover {
  filter: brightness(1.08);
  box-shadow: var(--glow);
}
.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
  filter: none;
  box-shadow: none;
}
.btn-ghost {
  background: var(--panel);
  color: var(--txt);
  font-size: 12.5px;
  font-weight: 600;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  transition: 0.15s;
}
.btn-ghost:hover {
  border-color: var(--cyan);
  color: var(--txt-strong);
}
.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.spin-ic {
  display: inline-block;
  animation: spin 1s linear infinite;
}
/* north form */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.fld {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.fl {
  font-size: 11.5px;
  color: var(--txt2);
}
.inp {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 9px 11px;
  color: var(--txt);
  font-size: 13px;
  outline: none;
  transition: 0.15s;
}
.inp:focus {
  border-color: var(--cyan);
  box-shadow: var(--glow);
}
.act-row {
  display: flex;
  gap: 9px;
  margin-top: 16px;
  flex-wrap: wrap;
}
.result {
  margin-top: 14px;
  padding: 10px 12px;
  border-radius: 9px;
  font-size: 12.5px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.result.ok {
  background: rgba(43, 212, 122, 0.1);
  color: var(--green);
  border: 1px solid rgba(43, 212, 122, 0.35);
}
.result.bad {
  background: rgba(255, 77, 94, 0.1);
  color: var(--red);
  border: 1px solid rgba(255, 77, 94, 0.35);
}
.r-ic {
  font-weight: 800;
}
/* log */
.log-scroll {
  max-height: 340px;
  overflow-y: auto;
  margin-top: 4px;
}
.log-empty {
  padding: 40px 0;
  text-align: center;
  color: var(--txt3);
  font-size: 13px;
}
@media (max-width: 768px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .clip {
    max-width: 120px;
  }
}
</style>
