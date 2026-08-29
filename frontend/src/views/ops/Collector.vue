<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('运维作业') }} {{ tl('·') }} {{ tl('采集器接入') }} / {{ tl('设备注册状态') }}</h1>
      <span class="sub"
        >{{ tl('外部设备注册') }} {{ tl('·') }} {{ tl('在线状态') }} {{ tl('·') }}
        {{ tl('实时测点落地') }} ({{ tl('契约') }}: /api/external/*)</span
      >
      <span class="pill">HTTP + Kafka {{ tl('双通道') }}</span>
    </div>

    <!-- 概览指标 (容器层展示) -->
    <LoadingState
      v-if="loading && !list"
      variant="skeleton"
      :rows="1"
      row-height="56px"
      min-height="64px"
      style="margin-bottom: 4px"
    />
    <div class="grid cols-4" v-else-if="list">
      <KpiCard :title="tl('已注册设备')" :value="list.total" unit="台" />
      <KpiCard :title="tl('在线')" :value="list.online" unit="台" status="normal" />
      <KpiCard :title="tl('离线')" :value="list.offline" unit="台" />
      <KpiCard :title="tl('累计测点')" :value="list.total_metrics.toLocaleString()" unit="条" />
    </div>

    <!-- 筛选 (容器层状态) -->
    <div class="section-title">{{ tl('设备注册状态') }}</div>
    <Panel>
      <div class="flex gap8 wrap" style="align-items: center">
        <button class="btn-sm primary" @click="openAdd">＋ {{ tl('添加设备') }}</button>
        <input
          v-model.trim="filters.domain"
          class="ipt"
          placeholder="业务域 (如 hvac_terminal)"
          style="width: 220px"
          @keyup.enter="load"
        />
        <input
          v-model.trim="filters.protocol"
          class="ipt"
          placeholder="协议 (如 modbus/snmp/kafka)"
          style="width: 200px"
          @keyup.enter="load"
        />
        <button class="btn-sm" @click="load">{{ tl('查询') }}</button>
        <button class="btn-sm" @click="resetFilters">{{ tl('重置') }}</button>
        <button class="btn-sm primary" :disabled="!selected" @click="metricDefsOpen = true">
          {{ tl('测点管理') }}
        </button>
        <span class="muted" style="margin-left: auto; font-size: 11px">{{
          loading ? '刷新中…' : `最近刷新 ${lastRefresh}`
        }}</span>
      </div>
    </Panel>

    <!-- 设备表格 (Presentational 子组件) -->
    <AsyncSection
      :loading="loading"
      :error="loadError"
      :empty="!list || (list?.items.length ?? 0) === 0"
      empty-title="暂无注册设备"
      empty-desc="点击「添加设备」经外部契约端点注册第一台设备，采集器方可上报测点。"
      @retry="load"
    >
      <CollectorDeviceTable
        :items="list ? list.items : []"
        :selected-id="selected?.device_id"
        @select="selectDevice"
        @open-metrics="openMetrics"
        @open-edit="openEdit"
        @confirm-delete="confirmDelete"
      />
      <template #empty-actions>
        <button class="btn-sm primary" @click="openAdd">＋ 添加设备</button>
      </template>
    </AsyncSection>

    <!-- 查看测点弹窗 (Presentational) -->
    <CollectorMetricsModal
      :device="modalDevice"
      :metrics="modalMetrics"
      :loading="modalLoading"
      @close="closeMetrics"
      @refresh="loadModalMetrics"
    />

    <!-- 测点定义管理 (增删改查) -->
    <CollectorMetricDefsModal
      v-if="metricDefsOpen && selected"
      :device="selected"
      @close="metricDefsOpen = false"
    />

    <!-- 添加 / 编辑设备表单 (Presentational 合并) -->
    <CollectorDeviceForm
      :open="addOpen || editOpen"
      :mode="editOpen ? 'edit' : 'add'"
      :device="editOpen ? editDevice : null"
      :submitting="editOpen ? editing : adding"
      :result="editOpen ? null : addResult"
      :error="editOpen ? editError : addError"
      :ok-msg="editOpen ? editOk : ''"
      @close="closeForm"
      @submit-single="onSubmitSingle"
      @submit-batch="onSubmitBatch"
      @submit-edit="onSubmitEdit"
    />

    <!-- 删除确认弹窗 -->
    <teleport to="body">
      <div class="modal-mask" v-if="deleteConfirmOpen" @click.self="deleteConfirmOpen = false">
        <div class="modal" style="width: min(420px, 94vw)">
          <div class="modal-head">
            <div class="modal-title">{{ tl('确认删除') }}</div>
            <button class="btn-sm" @click="deleteConfirmOpen = false">{{ tl('关闭') }} ✕</button>
          </div>
          <div class="modal-body">
            <p>
              {{ tl('确定要删除设备') }} <strong>{{ deleteTarget?.device_id }}</strong>
              {{ tl('吗') }}？
            </p>
            <p class="muted" style="font-size: 11px; margin-top: 4px">
              {{ tl('该操作将同时删除此设备的所有测点数据') }}，{{ tl('且不可恢复') }}。
            </p>
            <div v-if="deleteError" class="result warn" style="margin-top: 12px">
              {{ deleteError }}
            </div>
          </div>
          <div class="modal-foot">
            <button class="btn-sm" @click="deleteConfirmOpen = false">{{ tl('取消') }}</button>
            <button class="btn-sm danger" :disabled="deleting" @click="doDelete">
              {{ deleting ? '删除中…' : '确认删除' }}
            </button>
          </div>
        </div>
      </div>
    </teleport>

    <div class="footer-note">
      {{ tl('运维作业·采集器接入') }} {{ tl('—') }} {{ tl('数据每') }} {{ refreshSec }}s
      {{ tl('刷新') }}, {{ tl('接入后端') }} /api/external/devices
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { toErrorMessage } from '@/composables/useAsyncPage'
import {
  deleteDevice,
  getDeviceMetrics,
  getExternalDevices,
  registerDevice,
  updateDevice,
} from '@/api'
import type {
  DeviceListResponse,
  ExternalDevice,
  ExternalDeviceView,
  MetricRecordView,
} from '@/types'
import CollectorDeviceTable from './components/CollectorDeviceTable.vue'
import CollectorMetricsModal from './components/CollectorMetricsModal.vue'
import CollectorMetricDefsModal from './components/CollectorMetricDefsModal.vue'
import CollectorDeviceForm from './components/CollectorDeviceForm.vue'
import { KpiCard } from '@dc-ioc/ui'
import Panel from '@/components/common/Panel.vue'
import LoadingState from '@/components/common/LoadingState.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'

// ===================== 容器层: 状态 + 数据 + API =====================
const list = ref<DeviceListResponse | null>(null)
const loading = ref(false)
const loadError = ref('')
const lastRefresh = ref('--:--:--')
const filters = reactive<{ domain: string; protocol: string }>({ domain: '', protocol: '' })
const selected = ref<ExternalDeviceView | null>(null)
const metricDefsOpen = ref(false)

// 查看测点 (Presentational 子组件接收)
const modalOpen = ref(false)
const modalDevice = ref<ExternalDeviceView | null>(null)
const modalMetrics = ref<MetricRecordView[]>([])
const modalLoading = ref(false)

// 添加 / 编辑 (Presentational 子组件接收)
const addOpen = ref(false)
const adding = ref(false)
const addError = ref('')
const addResult = ref<{ ok: number; dup: number; fail: number } | null>(null)
const editOpen = ref(false)
const editing = ref(false)
const editError = ref('')
const editOk = ref('')
const editDevice = ref<ExternalDeviceView | null>(null)

// 删除
const deleteConfirmOpen = ref(false)
const deleteTarget = ref<ExternalDeviceView | null>(null)
const deleting = ref(false)
const deleteError = ref('')

const refreshSec = Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000) / 1000

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    list.value = await getExternalDevices({
      domain: filters.domain || undefined,
      protocol: filters.protocol || undefined,
    })
    lastRefresh.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    if (modalOpen.value && modalDevice.value) {
      const still = list.value.items.find((i) => i.device_id === modalDevice.value!.device_id)
      if (still) loadModalMetrics()
      else closeMetrics()
    }
  } catch (e: unknown) {
    loadError.value =
      toErrorMessage(e) || '设备列表加载失败，请检查外部契约端点是否就绪'
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  filters.domain = ''
  filters.protocol = ''
  load()
}

function selectDevice(d: ExternalDeviceView) {
  selected.value = d
}

async function openMetrics(d: ExternalDeviceView) {
  selected.value = d
  modalDevice.value = d
  modalOpen.value = true
  await loadModalMetrics()
}

async function loadModalMetrics() {
  if (!modalDevice.value) return
  modalLoading.value = true
  try {
    modalMetrics.value = await getDeviceMetrics(modalDevice.value.device_id, 20)
  } catch {
    modalMetrics.value = []
  } finally {
    modalLoading.value = false
  }
}

function closeMetrics() {
  modalOpen.value = false
  // 必须清空 modalDevice: CollectorMetricsModal 的显示条件是 v-if="device",
  // 若仅置 modalOpen=false 而 device 仍非 null, 弹窗不会关闭 (关闭按钮失效根因)
  modalDevice.value = null
}

// 添加
function openAdd() {
  addOpen.value = true
  addError.value = ''
  addResult.value = null
}

function closeForm() {
  addOpen.value = false
  editOpen.value = false
}

/** 字段名中文映射 (后端 422 校验路径 -> 可读字段名) */
const FIELD_LABELS: Record<string, string> = {
  device_id: '设备 ID',
  ip: 'IP 地址',
  sn: '序列号',
  model: '型号',
  name: tl('名称'),
  vendor: '厂商',
  domain: '业务域',
  category: '类别',
  location: '位置',
  protocol: '协议',
  tags: '标签',
  description: '描述',
}

interface ValidationErr {
  loc?: unknown[]
  msg?: string
  type?: string
}

function parseValidationError(e: unknown): string {
  const detail = (e as ErrorLike)?.detail
  if (typeof detail === 'string' && detail.includes('token')) {
    return '采集器鉴权失败，请联系管理员配置 EXTERNAL_COLLECTOR_TOKEN'
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((d: ValidationErr) => {
        const field = (d.loc?.slice(-1)[0] || '') as string
        const label = FIELD_LABELS[field] || field || '未知字段'
        const msgMap: Record<string, string> = {
          string_too_short: `${label} 长度不足`,
          string_too_long: `${label} 超出最大长度`,
          value_error: `${label}: ${(d.msg ?? '').replace(/^Value error,\s*/i, '')}`,
          string_pattern_mismatch: `${label}: 须以字母或数字开头，仅允许字母/数字/._:-`,
          type_error: `${label} 类型不正确`,
        }
        return msgMap[d.type ?? ''] || `${label}: ${d.msg ?? ''}`
      })
      .join('；')
  }
  if (typeof detail === 'string') return detail
  if (typeof (e as ErrorLike)?.message === 'string') return (e as ErrorLike).message ?? ''
  return '注册失败，请检查网络连接或联系管理员'
}

async function onSubmitSingle(payload: ExternalDevice) {
  adding.value = true
  addError.value = ''
  addResult.value = null
  try {
    const res = await registerDevice(payload)
    const dup = res.status === 'duplicate'
    addResult.value = { ok: dup ? 0 : 1, dup: dup ? 1 : 0, fail: 0 }
    await load()
  } catch (e: unknown) {
    addError.value = parseValidationError(e)
    addResult.value = { ok: 0, dup: 0, fail: 1 }
  } finally {
    adding.value = false
  }
}

async function onSubmitBatch(payloads: ExternalDevice[]) {
  adding.value = true
  addError.value = ''
  addResult.value = null
  try {
    const results = await Promise.allSettled(payloads.map((p) => registerDevice(p)))
    let ok = 0,
      dup = 0,
      fail = 0
    const failReasons: string[] = []
    for (let i = 0; i < results.length; i++) {
      const r = results[i]
      if (r.status === 'fulfilled') {
        if (r.value.status === 'duplicate') dup++
        else ok++
      } else {
        fail++
        if (failReasons.length < 3) {
          const reason = parseValidationError(r.reason)
          const id = payloads[i]?.device_id || `#${i}`
          failReasons.push(`${id}: ${reason}`)
        }
      }
    }
    addResult.value = { ok, dup, fail }
    if (failReasons.length > 0) {
      addError.value = failReasons.join('；') + (fail > 3 ? ` 等 ${fail} 条错误` : '')
    }
    await load()
  } catch (e: unknown) {
    addError.value = parseValidationError(e)
    addResult.value = { ok: 0, dup: 0, fail: 1 }
  } finally {
    adding.value = false
  }
}

async function onSubmitEdit(deviceId: string, payload: Record<string, unknown>) {
  editing.value = true
  editError.value = ''
  editOk.value = ''
  try {
    await updateDevice(deviceId, payload)
    editOk.value = '设备信息已更新'
    await load()
  } catch (e: unknown) {
    editError.value = parseValidationError(e)
  } finally {
    editing.value = false
  }
}

// 编辑
function openEdit(d: ExternalDeviceView) {
  editError.value = ''
  editOk.value = ''
  editDevice.value = d
  editOpen.value = true
}

// 删除
function confirmDelete(d: ExternalDeviceView) {
  deleteTarget.value = d
  deleteError.value = ''
  deleteConfirmOpen.value = true
}

async function doDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  deleteError.value = ''
  try {
    await deleteDevice(deleteTarget.value.device_id)
    deleteConfirmOpen.value = false
    await load()
  } catch (e: unknown) {
    deleteError.value = parseValidationError(e)
  } finally {
    deleting.value = false
  }
}

let timer = 0
onMounted(() => {
  load()
  timer = window.setInterval(load, Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000))
})
onBeforeUnmount(() => clearInterval(timer))
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
.btn-sm.danger {
  background: rgba(242, 63, 63, 0.15);
  color: var(--red);
  border-color: rgba(242, 63, 63, 0.4);
}
.btn-sm.danger:disabled {
  opacity: 0.6;
  cursor: default;
}
.btn-sm.danger:hover:not(:disabled) {
  background: rgba(242, 63, 63, 0.3);
}
.result {
  margin-top: 12px;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
}
.result.ok {
  background: rgba(43, 212, 122, 0.1);
  color: var(--green);
  border: 1px solid rgba(43, 212, 122, 0.3);
}
.result.warn {
  background: rgba(255, 176, 32, 0.1);
  color: var(--amber);
  border: 1px solid rgba(255, 176, 32, 0.3);
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(6, 11, 20, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6vh 16px;
  z-index: 1000;
}
.modal {
  width: min(420px, 94vw);
  background: linear-gradient(180deg, var(--panel), var(--bg2));
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}
.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
}
.modal-title {
  font-size: 15px;
  font-weight: 700;
}
.modal-body {
  padding: 14px 16px;
}
.modal-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 10px 16px;
  border-top: 1px solid var(--line);
}
</style>
