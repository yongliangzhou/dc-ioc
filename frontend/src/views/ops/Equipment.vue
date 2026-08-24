<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('资产管理') }} {{ tl('·') }} {{ tl('统一设备台账') }}</h1>
      <span class="sub"
        >{{ tl('按域') }} / {{ tl('类别') }} / {{ tl('状态检索设备') }} {{ tl('·') }}
        {{ tl('遥测跳转') }}</span
      >
      <span class="pill">{{ tl('共') }} {{ total }} {{ tl('台') }}</span>
    </div>

    <!-- 筛选 -->
    <Panel class="toolbar">
      <select v-model="domain" class="ipt" style="width: 150px" @change="reload()">
        <option value="">{{ tl('全部业务域') }}</option>
        <option v-for="d in domainOptions" :key="d" :value="d">{{ d }}</option>
      </select>
      <select v-model="category" class="ipt" style="width: 150px" @change="reload()">
        <option value="">{{ tl('全部类别') }}</option>
        <option v-for="c in categoryOptions" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="status" class="ipt" style="width: 120px" @change="reload()">
        <option value="">{{ tl('全部状态') }}</option>
        <option value="运行">{{ tl('运行') }}</option>
        <option value="待机">{{ tl('待机') }}</option>
        <option value="故障">{{ tl('故障') }}</option>
        <option value="维保">{{ tl('维保') }}</option>
        <option value="库房备件">{{ tl('库房备件') }}</option>
      </select>
      <input
        v-model.trim="kw"
        class="ipt"
        :placeholder="tl('搜索编码 / 名称 / 厂商')"
        style="width: 220px"
        @keyup.enter="reload()"
      />
      <button class="btn-sm primary" @click="reload()">{{ tl('查询') }}</button>
    </Panel>

    <!-- 列表 -->
    <Panel class="scroll-x">
      <table>
        <thead>
          <tr>
            <th scope="col">{{ tl('设备编码') }}</th>
            <th scope="col">{{ tl('名称') }}</th>
            <th scope="col">{{ tl('业务域') }}</th>
            <th scope="col">{{ tl('类别') }}</th>
            <th scope="col">{{ tl('厂商') }} / {{ tl('型号') }}</th>
            <th scope="col">{{ tl('状态') }}</th>
            <th scope="col">{{ tl('负载率') }}</th>
            <th scope="col">{{ tl('运行小时') }}</th>
            <th scope="col">{{ tl('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in items" :key="e.id" @click="openEq(e)" style="cursor: pointer">
            <td class="mono">{{ e.code }}</td>
            <td>{{ e.name }}</td>
            <td>{{ e.domain }}</td>
            <td>
              <span class="tag b">{{ e.category }}</span>
            </td>
            <td class="mono" style="font-size: 11px">{{ e.vendor }} / {{ e.model }}</td>
            <td>
              <span
                class="tag"
                :class="
                  e.status === '运行'
                    ? 'g'
                    : e.status === '故障'
                      ? 'r'
                      : e.status === '维保'
                        ? 'a'
                        : e.status === '库房备件'
                          ? 'p'
                          : 'o'
                "
                >{{ e.status }}</span
              >
            </td>
            <td class="mono">{{ e.load_pct }}%</td>
            <td class="mono muted">{{ e.run_hours.toLocaleString() }}</td>
            <td>
              <button class="btn-sm" @click.stop="openEq(e)">{{ tl('遥测') }}</button>
            </td>
          </tr>
          <tr v-if="!items.length">
            <td colspan="9" class="muted" style="text-align: center; padding: 18px">
              {{ tl('无匹配设备') }}
            </td>
          </tr>
        </tbody>
      </table>
    </Panel>

    <!-- 设备遥测弹窗 -->
    <teleport to="body">
      <div class="tf-mask" v-if="sel" @click.self="sel = null">
        <div class="tf-modal" style="width: min(760px, 96vw)">
          <div class="tf-head">
            <div>
              <h3>{{ tl('设备遥测') }} {{ tl('·') }} {{ sel.name }}</h3>
              <div class="muted" style="font-size: 11px; margin-top: 3px">
                {{ sel.code }} {{ tl('·') }} {{ sel.domain }} / {{ sel.category }} {{ tl('·') }}
                {{ tl('厂商') }} {{ sel.vendor }} {{ tl('·') }} {{ tl('冗余') }}
                {{ sel.redundancy }}
              </div>
              <div
                v-if="
                  sel.attrs?.location ||
                  sel.attrs?.ip ||
                  sel.attrs?.protocol ||
                  sel.attrs?.online === false
                "
                class="muted"
                style="font-size: 11px; margin-top: 2px"
              >
                <span v-if="sel.attrs?.location">{{ tl('位置') }} {{ sel.attrs.location }}</span>
                <span v-if="sel.attrs?.ip"> {{ tl('·') }} IP {{ sel.attrs.ip }}</span>
                <span v-if="sel.attrs?.protocol"> {{ tl('·') }} {{ sel.attrs.protocol }}</span>
                <span v-if="sel.attrs?.online === false"> {{ tl('·') }} {{ tl('离线') }}</span>
              </div>
            </div>
            <button class="tf-x" @click="sel = null">✕</button>
          </div>
          <div class="tf-body">
            <div v-if="eq" style="margin-top: 4px">
              <TrendChart
                :metrics="eqTrendMetrics"
                :active="eqActive"
                :series="eqSeries"
                :unit-map="eqUnitMap"
                :loading="eqLoading"
                @select="eqActive = $event"
              />
            </div>
            <div v-else class="muted" style="text-align: center; padding: 22px">
              {{ eqLoading ? '加载中…' : '暂无数据' }}
            </div>
          </div>
          <div class="tf-foot">
            <span class="muted" style="font-size: 11px"
              >{{ tl('数据源') }} /api/equipment/{{ sel?.id }}/metrics {{ tl('·') }}
              {{ tl('近') }} 60min</span
            >
            <button class="btn-sm" @click="goTelemetry">{{ tl('前往设备遥测页') }} →</button>
          </div>
        </div>
      </div>
    </teleport>

    <div class="footer-note">
      {{ tl('资产管理·统一设备台账') }} {{ tl('—') }} {{ tl('单一事实源') }} external_devices
      {{ tl('·') }} {{ tl('接入后端') }} /api/equipment
    </div>

    <!-- 分页 -->
    <div class="pager">
      <span class="muted"
        >{{ tl('共') }} {{ total }} {{ tl('台') }} {{ tl('·') }} {{ tl('第') }} {{ page }} /
        {{ totalPages }} {{ tl('页') }}</span
      >
      <select v-model.number="pageSize" class="ipt" style="width: 96px" @change="onPageSizeChange">
        <option :value="20">20 / {{ tl('页') }}</option>
        <option :value="50">50 / {{ tl('页') }}</option>
        <option :value="100">100 / {{ tl('页') }}</option>
      </select>
      <button class="btn-sm" :disabled="page <= 1" @click="goPage(1)">« {{ tl('首页') }}</button>
      <button class="btn-sm" :disabled="page <= 1" @click="goPage(page - 1)">
        {{ tl('上一页') }}
      </button>
      <button class="btn-sm" :disabled="page >= totalPages" @click="goPage(page + 1)">
        {{ tl('下一页') }}
      </button>
      <button class="btn-sm" :disabled="page >= totalPages" @click="goPage(totalPages)">
        {{ tl('末页') }} »
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { getEquipmentMetrics, listEquipment } from '@/api'
import TrendChart, { type TrendMetric } from '@/components/charts/TrendChart.vue'
import Panel from '@/components/common/Panel.vue'
import type { Equipment, EquipmentMetrics, MetricHistoryPoint } from '@/types'

const router = useRouter()
const items = ref<Equipment[]>([])
const domain = ref('')
const category = ref('')
const status = ref('')
const kw = ref('')

/* 分页状态 */
const page = ref(1)
const pageSize = ref(50)
const total = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))

/* 下拉选项基于全量 (一次性拉取, 不受分页影响) */
const allItems = ref<Equipment[]>([])
const domainOptions = computed(() => [...new Set(allItems.value.map((e) => e.domain))])
const categoryOptions = computed(() => [...new Set(allItems.value.map((e) => e.category))])

async function loadMeta() {
  try {
    const r = await listEquipment({ page_size: 10000 })
    allItems.value = r.items
  } catch {
    /* 忽略 */
  }
}

async function reload(resetPage = true) {
  if (resetPage) page.value = 1
  try {
    const r = await listEquipment({
      domain: domain.value || undefined,
      category: category.value || undefined,
      status: status.value || undefined,
      kw: kw.value || undefined,
      page: page.value,
      page_size: pageSize.value,
    })
    items.value = r.items
    total.value = r.total
  } catch {
    /* 静态 mock 兜底 */
  }
}

function onPageSizeChange() {
  reload(true)
}
function goPage(p: number) {
  const target = Math.min(Math.max(1, p), totalPages.value)
  if (target === page.value) return
  page.value = target
  reload(false)
}

const METRIC_LABELS: Record<string, { label: string; unit: string }> = {
  inlet_temp: { label: tl('进风温度'), unit: '℃' },
  outlet_temp: { label: tl('出风温度'), unit: '℃' },
  power_kw: { label: tl('功耗'), unit: 'kW' },
  cpu_usage: { label: tl('CPU 使用率'), unit: '%' },
  temp: { label: tl('温度'), unit: '℃' },
}

const sel = ref<Equipment | null>(null)
const eq = ref<EquipmentMetrics | null>(null)
const eqLoading = ref(false)
const eqActive = ref('inlet_temp')

const eqUnitMap = computed<Record<string, string>>(() => {
  const m = eq.value
  const map: Record<string, string> = {}
  if (m) for (const k of m.metrics) map[k] = METRIC_LABELS[k]?.unit ?? ''
  return map
})

const eqTrendMetrics = computed<TrendMetric[]>(() => {
  const m = eq.value
  if (!m) return []
  return m.metrics.map((name) => ({
    name,
    label: METRIC_LABELS[name]?.label ?? name,
    unit: METRIC_LABELS[name]?.unit ?? '',
    latest: m.series[name]?.length ? m.series[name][m.series[name].length - 1].value : undefined,
  }))
})
const eqSeries = computed<Record<string, MetricHistoryPoint[]>>(() => {
  const m = eq.value
  if (!m) return {}
  const out: Record<string, MetricHistoryPoint[]> = {}
  for (const k of m.metrics) {
    out[k] = (m.series[k] ?? []).map((p) => ({
      ts: p.ts,
      value: p.value,
      quality: 'good' as const,
    }))
  }
  return out
})

async function openEq(e: Equipment) {
  sel.value = e
  eq.value = null
  eqLoading.value = true
  eqActive.value = e.category === 'chiller' || e.category === 'crac' ? 'inlet_temp' : 'power_kw'
  try {
    eq.value = await getEquipmentMetrics(e.id, { minutes: 60, step_sec: 60 })
    if (eq.value.metrics.length) eqActive.value = eq.value.metrics[0]
  } catch {
    /* mock 兜底 */
  } finally {
    eqLoading.value = false
  }
}

function goTelemetry() {
  router.push('/ops/telemetry')
}

let timer = 0
onMounted(() => {
  loadMeta()
  reload()
  timer = window.setInterval(
    () => reload(false),
    Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 15000),
  )
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
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
.btn-sm {
  background: var(--bg2);
  border: 1px solid var(--line);
  color: var(--txt);
  padding: 4px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 11px;
}
.btn-sm:hover {
  border-color: var(--cyan);
}
.btn-sm.primary {
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  color: #04121f;
  border-color: transparent;
  font-weight: 700;
}
.pager {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  flex-wrap: wrap;
}
.pager .ipt {
  width: 96px;
}
.pager .muted {
  font-size: 12px;
}
</style>
