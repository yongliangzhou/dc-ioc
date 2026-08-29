<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('运维作业') }} {{ tl('·') }} {{ tl('设备遥测') }}</h1>
      <span class="sub"
        >{{ tl('物模型驱动') }} {{ tl('·') }} WebSocket {{ tl('实时') }} + HTTP
        {{ tl('轮询降级') }}</span
      >
      <span class="pill" :class="selected ? 'g' : ''">{{
        selected ? '监控中' : '请选择设备'
      }}</span>
    </div>

    <!-- 设备选择面板 -->
    <Panel style="margin-bottom: 14px">
      <div class="flex gap8 wrap" style="align-items: center">
        <span class="section-title-inline" style="margin: 0">{{ tl('设备选择') }}</span>
        <input
          v-model.trim="search"
          class="ipt"
          :placeholder="tl('搜索设备 ID / 名称 / IP…')"
          style="width: 240px"
          @input="onSearch"
        />
        <select v-model="filterCategory" class="ipt" style="width: 120px" @change="onSearch">
          <option value="">{{ tl('全部类别') }}</option>
          <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="filterProtocol" class="ipt" style="width: 120px" @change="onSearch">
          <option value="">{{ tl('全部协议') }}</option>
          <option v-for="p in protocols" :key="p" :value="p">{{ p }}</option>
        </select>
        <button class="btn-sm" @click="refresh">{{ tl('刷新列表') }}</button>
        <span class="muted" style="margin-left: auto; font-size: 11px"
          >{{ filtered.length }} {{ tl('台设备') }} {{ tl('·') }} {{ onlineCount }}
          {{ tl('在线') }}</span
        >
      </div>
    </Panel>

    <!-- 设备卡片网格 -->
    <AsyncSection :loading="loading" :error="error" :empty="!filtered.length" @retry="refresh">
      <div class="grid cols-6">
        <div
          v-for="d in paginatedDevices"
          :key="d.device_id"
          class="dev-card"
          :class="{ active: selected?.device_id === d.device_id }"
          @click="selectDevice(d)"
        >
          <div class="dc-head">
            <span class="dot" :class="d.online ? 'g' : 'o'"></span>
            <span class="dc-id mono">{{ d.device_id }}</span>
          </div>
          <div class="dc-name">{{ d.name || d.device_id }}</div>
          <div class="dc-meta">
            <span class="tag b">{{ d.protocol || '—' }}</span>
            <span class="tag">{{ d.domain || '—' }}</span>
          </div>
          <div class="dc-stats">
            <span>{{ d.metric_count }} {{ tl('测点') }}</span>
            <span class="mono muted" style="font-size: 10px">{{ d.ip }}</span>
          </div>
        </div>
      </div>
    </AsyncSection>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="flex center gap8" style="margin: 10px 0">
      <button class="btn-sm" :disabled="page <= 1" @click="page--">{{ tl('上一页') }}</button>
      <span class="muted" style="font-size: 11px">{{ page }} / {{ totalPages }}</span>
      <button class="btn-sm" :disabled="page >= totalPages" @click="page++">
        {{ tl('下一页') }}
      </button>
    </div>

    <!-- DeviceMonitor -->
    <div v-if="selected && deviceThingModels.length" style="margin-top: 14px">
      <DeviceMonitor
        :device-id="selected.device_id"
        :device-name="selected.name || selected.device_id"
        :thing-models="deviceThingModels"
        :metric-labels="metricLabelMap"
        :category="selected.category || ''"
        :protocol="selected.protocol || ''"
        :kpi-metrics="kpiMetricNames"
      />
    </div>
    <Panel
      v-else-if="selected && !deviceThingModels.length"
      class="muted"
      style="text-align: center; padding: 22px; margin-top: 14px"
    >
      {{ tl('该设备未匹配到物模型') }}，{{ tl('或物模型加载失败') }}。
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()

import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getExternalDevices, getThingModels } from '@/api'
import DeviceMonitor from '@/components/business/DeviceMonitor.vue'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { toErrorMessage } from '@/composables/useAsyncPage'
import { THING_MODELS, type ThingModel } from '@/constants/thingModels'
import type { DeviceListResponse, ExternalDeviceView, ThingModelDef } from '@/types'
/* ---- 设备列表 ---- */
const list = ref<DeviceListResponse | null>(null)
const loading = ref(false)
const search = ref('')
const filterCategory = ref('')
const filterProtocol = ref('')
const page = ref(1)
const pageSize = 12

const filtered = computed(() => {
  if (!list.value) return []
  let items = [...list.value.items]
  if (search.value) {
    const q = search.value.toLowerCase()
    items = items.filter(
      (d) =>
        d.device_id.toLowerCase().includes(q) ||
        (d.name || '').toLowerCase().includes(q) ||
        d.ip.includes(q),
    )
  }
  if (filterCategory.value) {
    items = items.filter((d) => d.category === filterCategory.value)
  }
  if (filterProtocol.value) {
    items = items.filter((d) => d.protocol === filterProtocol.value)
  }
  return items
})

const totalPages = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize)))
const paginatedDevices = computed(() => {
  const start = (page.value - 1) * pageSize
  return filtered.value.slice(start, start + pageSize)
})

const onlineCount = computed(() => list.value?.online ?? 0)
const categories = computed(() => [
  ...new Set((list.value?.items ?? []).map((d) => d.category).filter(Boolean) as string[]),
])
const protocols = computed(() => [
  ...new Set((list.value?.items ?? []).map((d) => d.protocol).filter(Boolean) as string[]),
])

function onSearch() {
  page.value = 1
}

/* ---- 选中设备 ---- */
const selected = ref<ExternalDeviceView | null>(null)

function selectDevice(d: ExternalDeviceView) {
  selected.value = d
}

/* ---- 物模型 (后端 API + 前端常量融合) ---- */
const backendThingModels = ref<ThingModelDef[]>([])

// 将前端 THING_MODELS 转为 DeviceMonitor 期望的 ThingModelDef 格式
function convertFrontendModels(models: ThingModel[]): ThingModelDef[] {
  return models.map((m) => ({
    category: m.category,
    category_label: m.name,
    domain: m.domain,
    protocol: m.protocol,
    metrics: m.metrics.map((mt) => ({
      metric_name: mt.name,
      unit: mt.unit,
      description: mt.desc,
    })),
  }))
}

const frontendThingModels = computed<ThingModelDef[]>(() => convertFrontendModels(THING_MODELS))

const deviceThingModels = computed<ThingModelDef[]>(() => {
  if (!selected.value) return []
  // 后端 API 返回的物模型优先 (真实数据源, 更准确)
  if (backendThingModels.value.length) {
    const matched = backendThingModels.value.filter((t) => t.category === selected.value!.category)
    if (matched.length) return matched
  }
  // 降级到前端常量物模型
  const cat = selected.value.category || ''
  return frontendThingModels.value.filter((t) => t.category === cat)
})

// 测点中文标签映射 (metric_name → Label)
// 单一事实源: 优先使用物模型 API 返回的 description (后端 deviceThingModels 已优先后端),
// 前端 THING_MODELS 常量仅作离线兜底, 避免两套标签漂移。
const metricLabelMap = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  // 通用名兜底 (与具体物模型无关)
  const common: Record<string, string> = {
    supply_temp: '送水温度',
    return_temp: '回水温度',
    inlet_temp: '进风温度',
    outlet_temp: '出风温度',
    humidity: '湿度',
    power_kw: '功耗',
    cpu_usage: 'CPU 使用率',
    temp: '温度',
  }
  Object.assign(map, common)
  // 物模型描述优先 (后端 API 或前端常量, deviceThingModels 已优先后端)
  for (const t of deviceThingModels.value) {
    for (const mt of t.metrics) {
      if (mt.description) map[mt.metric_name] = mt.description
    }
  }
  // 前端常量补充 (离线兜底)
  for (const m of THING_MODELS) {
    for (const mt of m.metrics) {
      if (!map[mt.name]) map[mt.name] = mt.desc
    }
  }
  return map
})

// KPI 测点名列表 (展示在顶部的摘要指标)
const kpiMetricNames = computed(() => {
  const models = deviceThingModels.value
  if (!models.length) return []
  return models[0].metrics.slice(0, 4).map((m) => m.metric_name)
})

/* ---- 数据加载 ---- */
const error = ref<string>('')

async function fetchDevices(showLoading: boolean) {
  if (showLoading) loading.value = true
  try {
    list.value = await getExternalDevices()
    error.value = ''
  } catch (e) {
    // 仅显式加载（首次 / 手动刷新）暴露错误；后台轮询失败静默，避免每 5s 闪烁错误态
    if (showLoading) error.value = toErrorMessage(e) || '加载设备列表失败'
  } finally {
    if (showLoading) loading.value = false
  }
}
// 首次加载 + 手动「刷新列表」：可见加载态与错误态（由 AsyncSection 呈现）
function refresh() {
  return fetchDevices(true)
}
// 后台轮询：静默更新列表，不触发骨架屏闪烁
async function poll() {
  await fetchDevices(false)
}

async function loadThingModels() {
  try {
    backendThingModels.value = await getThingModels()
  } catch {
    /* 后端不可用时使用前端常量 */
  }
}

watch(search, onSearch)
watch(filterCategory, onSearch)
watch(filterProtocol, onSearch)

let timer = 0
onMounted(() => {
  refresh()
  loadThingModels()
  timer = window.setInterval(poll, Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 5000))
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
select.ipt {
  appearance: none;
  cursor: pointer;
}

.section-title-inline {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--cyan);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

/* 设备卡片 */
.dev-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.dev-card:hover {
  border-color: rgba(34, 227, 255, 0.35);
  box-shadow: var(--glow);
  transform: translateY(-1px);
}
.dev-card.active {
  border-color: var(--cyan);
  background: linear-gradient(180deg, rgba(34, 227, 255, 0.1), var(--panel));
  box-shadow: 0 0 16px rgba(34, 227, 255, 0.15);
}
.dc-head {
  display: flex;
  align-items: center;
  gap: 6px;
}
.dc-id {
  font-size: 12px;
  font-weight: 700;
  color: var(--cyan);
}
.dc-name {
  font-size: 11.5px;
  color: var(--txt);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.dc-meta {
  display: flex;
  gap: 4px;
}
.dc-stats {
  display: flex;
  justify-content: space-between;
  font-size: 10.5px;
  color: var(--txt2);
}
</style>
