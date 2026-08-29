<template>
  <div class="bigscreen" :class="cfg.theme">
    <header class="bs-head">
      <div class="bs-title">{{ cfg.title }}</div>
      <div class="bs-meta">
        <span class="live"><i /> {{ tl('实时') }}</span>
        <span>{{ refreshTime }}</span>
        <router-link to="/monitor/visual/designer" class="edit">{{ tl('定制') }}</router-link>
      </div>
    </header>

    <ErrorBanner v-if="error" :count="1" :labels="['实时数据']" @retry="refresh" />

    <div class="bs-grid" :style="gridStyle">
      <div
        v-for="w in widgets"
        :key="w.id"
        class="bs-card"
        :class="'type-' + w.type"
      >
        <div class="bs-card-label">{{ w.label }}</div>
        <!-- KPI -->
        <div v-if="w.type === 'kpi'" class="bs-kpi">
          <span class="val">{{ fmt(w.value) }}</span>
          <span class="unit">{{ w.unit }}</span>
        </div>
        <!-- Gauge -->
        <div v-else-if="w.type === 'gauge'" class="bs-gauge">
          <svg viewBox="0 0 120 70">
            <path d="M10 65 A50 50 0 0 1 110 65" fill="none" stroke="rgba(255,255,255,.08)" stroke-width="10" stroke-linecap="round" />
            <path
              d="M10 65 A50 50 0 0 1 110 65"
              fill="none"
              :stroke="accent"
              stroke-width="10"
              stroke-linecap="round"
              :stroke-dasharray="gaugeDash(w.value, w.max)"
            />
          </svg>
          <div class="bs-gauge-val">{{ fmt(w.value) }}<small>{{ w.unit }}</small></div>
        </div>
        <!-- Line / Bar 趋势 -->
        <div v-else class="bs-chart">
          <div class="bars">
            <span
              v-for="(v, i) in w.seriesData"
              :key="i"
              class="bar"
              :style="{ height: barH(v, w.max ?? 100) + '%', background: accent }"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  SOURCE_POOL,
  fetchOverview,
  loadConfig,
  applySkin,
  type BigScreenConfig,
  type DataSourceTemplate,
} from '@/bigscreen/sources'
import { themeMode, applyTheme } from '@/theme'
import { toErrorMessage } from '@/composables/useAsyncPage'
import ErrorBanner from '@/components/common/ErrorBanner.vue'

const { t: tl } = useI18n()
const cfg = ref<BigScreenConfig>(loadConfig())
const refreshTime = ref('--:--:--')
const values = ref<Record<string, number>>({})
const error = ref('')

const accent = computed(
  () => cfg.value.customColor || (SOURCE_POOL.find(() => false), SKIN_COLOR(cfg.value.skin)),
)
function SKIN_COLOR(skin: string) {
  const map: Record<string, string> = {
    cyan: '#22e3ff',
    blue: '#3b82f6',
    green: '#2bd47a',
    purple: '#a855f7',
    orange: '#fb923c',
  }
  return map[skin] || '#22e3ff'
}

interface Widget extends DataSourceTemplate {
  value: number
  seriesData: number[]
  max?: number
}
const widgets = computed<Widget[]>(() => {
  const tpls = SOURCE_POOL.filter((s) => cfg.value.sourceIds.includes(s.id))
  return tpls.map((s) => {
    const v = values.value[s.id] ?? 0
    const base = s.type === 'gauge' ? v : Math.max(v, 1)
    const seriesData =
      s.type === 'line' || s.type === 'bar'
        ? Array.from({ length: 16 }, (_, i) => +(base * (0.85 + 0.3 * Math.sin(i / 2) + (i % 3) * 0.05)).toFixed(2))
        : []
    return { ...s, value: v, seriesData, max: s.max }
  })
})

const gridStyle = computed(() => {
  const n = Math.max(widgets.value.length, 1)
  const cols = n <= 3 ? n : n <= 6 ? 3 : 4
  return { gridTemplateColumns: `repeat(${cols}, 1fr)` }
})

function fmt(v: number) {
  if (v == null || isNaN(v)) return '--'
  return v >= 100 ? Math.round(v).toLocaleString() : v.toFixed(2)
}
function barH(v: number, max: number) {
  return Math.max(4, Math.min(100, (v / max) * 100))
}
function gaugeDash(v: number, max = 100) {
  const pct = Math.max(0, Math.min(1, v / max))
  const len = Math.PI * 50 // 半圆周长
  const filled = len * pct
  return `${filled} ${len - filled}`
}

async function refresh() {
  try {
    const { overview, activeAlarms, cop } = await fetchOverview()
    const extra = { activeAlarms, cop }
    const next: Record<string, number> = {}
    for (const s of SOURCE_POOL) {
      if (cfg.value.sourceIds.includes(s.id)) {
        next[s.id] = s.pick(overview, extra) || 0
      }
    }
    values.value = next
    refreshTime.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    error.value = ''
  } catch (e) {
    error.value = toErrorMessage(e) || '实时数据刷新失败'
  }
}

let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  applySkin(cfg.value)
  applyTheme(cfg.value.theme)
  themeMode.value = cfg.value.theme
  refresh()
  timer = setInterval(refresh, (cfg.value.refreshSec || 10) * 1000)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.bigscreen { min-height: 100vh; background: #060b16; color: #e2e8f0; padding: 18px 22px; }
.bigscreen.light { background: #eef2f7; color: #0f172a; }
.bs-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.bs-title { font-size: 22px; font-weight: 800; letter-spacing: 2px; color: var(--cyan, #22e3ff); text-shadow: 0 0 12px rgba(34,227,255,.4); }
.bs-meta { display: flex; align-items: center; gap: 14px; font-size: 13px; color: #94a3b8; }
.live { display: inline-flex; align-items: center; gap: 5px; color: #2bd47a; }
.live i { width: 8px; height: 8px; border-radius: 50%; background: #2bd47a; box-shadow: 0 0 8px #2bd47a; animation: blink 1.4s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
.edit { color: var(--cyan, #22e3ff); border: 1px solid rgba(34,227,255,.4); border-radius: 8px; padding: 4px 12px; text-decoration: none; font-size: 12px; }
.bs-grid { display: grid; gap: 16px; }
.bs-card { background: linear-gradient(160deg, rgba(15,30,50,.9), rgba(10,18,32,.9)); border: 1px solid rgba(34,227,255,.18); border-radius: 14px; padding: 18px; min-height: 150px; display: flex; flex-direction: column; }
.bigscreen.light .bs-card { background: #fff; border-color: rgba(8,145,178,.2); }
.bs-card-label { font-size: 13px; color: #94a3b8; margin-bottom: 10px; }
.bs-kpi { display: flex; align-items: baseline; gap: 6px; margin-top: auto; }
.bs-kpi .val { font-size: 38px; font-weight: 800; color: #e2e8f0; }
.bs-kpi .unit { font-size: 14px; color: #64748b; }
.bs-gauge { position: relative; flex: 1; display: flex; align-items: center; justify-content: center; }
.bs-gauge svg { width: 100%; max-width: 180px; }
.bs-gauge-val { position: absolute; bottom: 4px; font-size: 22px; font-weight: 700; color: #e2e8f0; }
.bs-gauge-val small { font-size: 12px; color: #64748b; margin-left: 2px; }
.bs-chart .bars { display: flex; align-items: flex-end; gap: 4px; height: 90px; }
.bs-chart .bar { flex: 1; border-radius: 3px 3px 0 0; opacity: .85; min-height: 4px; }
</style>
