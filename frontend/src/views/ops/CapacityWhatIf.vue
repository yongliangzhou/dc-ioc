<template>
  <div class="page-wrap">
    <!-- ===== 标题区 ===== -->
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
          <path d="m12 14 4-4" stroke-linecap="round" />
          <path d="M3.34 19a10 10 0 1 1 17.32 0" stroke-linecap="round" />
        </svg>
      </div>
      <div>
        <h1>{{ t('whatIf.title') }}</h1>
        <div class="sub">{{ t('whatIf.sub') }}</div>
      </div>
      <div class="vh-right">
        <template v-if="base.loading.value">
          <span class="baseline-note">{{ t('whatIf.baselineLoading') }}</span>
        </template>
        <template v-else-if="isRealBase">
          <span class="baseline-real"><i class="dot"></i>{{ t('whatIf.realBaseline') }}</span>
        </template>
        <template v-else>
          <DataBadge
            tone="sample"
            :label="t('whatIf.generatedBaseline')"
            :tip="t('whatIf.generatedTip')"
          />
        </template>
      </div>
    </div>

    <div class="wi-layout">
      <!-- ===== 左: 推演参数 ===== -->
      <div class="card wi-params">
        <div class="section-title">{{ t('whatIf.params') }}</div>

        <div class="slider-block">
          <div class="slider-head">
            <label>{{ t('whatIf.cabinets') }}</label>
            <span class="slider-val"
              >{{ form.cabinets }}<em>{{ t('whatIf.cabinetsUnit') }}</em></span
            >
          </div>
          <input v-model.number="form.cabinets" type="range" min="1" max="500" step="1" />
        </div>

        <div class="slider-block">
          <div class="slider-head">
            <label>{{ t('whatIf.kwPerCabinet') }}</label>
            <span class="slider-val"
              >{{ form.kwPerCabinet.toFixed(1) }}<em>{{ t('whatIf.kwUnit') }}</em></span
            >
          </div>
          <input v-model.number="form.kwPerCabinet" type="range" min="2" max="30" step="0.5" />
        </div>

        <div class="slider-block">
          <div class="slider-head">
            <label>{{ t('whatIf.monthsHorizon') }}</label>
            <span class="slider-val"
              >{{ form.monthsHorizon }}<em>{{ t('whatIf.monthsUnit') }}</em></span
            >
          </div>
          <input v-model.number="form.monthsHorizon" type="range" min="6" max="36" step="1" />
        </div>

        <button class="btn-primary wi-run" :disabled="runBusy" @click="runNow">
          <svg
            v-if="runBusy"
            class="run-spin"
            viewBox="0 0 24 24"
            width="14"
            height="14"
            fill="none"
            stroke="currentColor"
            stroke-width="2.4"
          >
            <path d="M21 12a9 9 0 1 1-6.2-8.56" stroke-linecap="round" />
          </svg>
          {{ runBusy ? t('whatIf.running') : t('whatIf.run') }}
        </button>
      </div>

      <!-- ===== 右: 推演结果 (AsyncSection 三态) ===== -->
      <div class="wi-result">
        <AsyncSection
          :loading="runBusy"
          :error="runError"
          :empty="!runLoaded && !runBusy"
          :loading-text="t('whatIf.running')"
          :empty-title="t('whatIf.emptyTitle')"
          :empty-desc="t('whatIf.emptyDesc')"
          min-height="320px"
          @retry="runNow"
        >
          <div v-if="result" class="wi-body">
            <!-- a. 维度双层条 -->
            <div class="dims-grid">
              <div
                v-for="d in sortedDims"
                :key="d.id"
                class="dim-card card"
                :class="{ bottleneck: d.id === result.bottleneck }"
              >
                <span v-if="d.id === result.bottleneck" class="bn-badge">
                  {{ t('whatIf.bottleneck') }}
                </span>
                <div class="dim-head">
                  <span class="dim-name">{{ d.id }}</span>
                  <span class="dim-usage mono">
                    {{ fmt(d.usedNow) }} → {{ fmt(d.usedAfter) }} {{ d.unit }}
                  </span>
                </div>
                <div class="bar-track">
                  <div class="bar-row">
                    <i class="bar-now" :style="{ width: clampPct(d.pctNow) + '%' }"></i>
                  </div>
                  <div class="bar-row">
                    <i
                      class="bar-after"
                      :class="pctClass(d.pctAfter)"
                      :style="{ width: clampPct(d.pctAfter) + '%' }"
                    ></i>
                  </div>
                </div>
                <div class="dim-foot">
                  <span class="cap mono"
                    >{{ t('whatIf.capacityNow') }} / {{ fmt(d.capacity) }} {{ d.unit }}</span
                  >
                  <span class="pct mono" :class="pctClass(d.pctAfter)"
                    >{{ d.pctAfter.toFixed(1) }}%</span
                  >
                </div>
                <div class="dim-extra mono">
                  {{ t('whatIf.addedBy') }} +{{ fmt(d.addedByRacks) }} · {{ t('whatIf.headroom') }}
                  {{ d.headroomPercent.toFixed(1) }}%
                </div>
              </div>
            </div>

            <!-- b. 到达阈值时间 -->
            <div class="card reach-card">
              <div class="section-title">{{ t('whatIf.reach') }}</div>
              <div class="reach-rows">
                <div v-for="d in sortedDims" :key="d.id" class="reach-row">
                  <span class="dim-name">{{ d.id }}</span>
                  <span class="reach-cell">
                    <b>{{ t('whatIf.reach85') }}</b>
                    <em :class="monthClass(d.reach85Month)" class="mono">{{
                      monthText(d.reach85Month)
                    }}</em>
                  </span>
                  <span class="reach-cell">
                    <b>{{ t('whatIf.reach100') }}</b>
                    <em :class="monthClass(d.reach100Month)" class="mono">{{
                      monthText(d.reach100Month)
                    }}</em>
                  </span>
                </div>
              </div>
            </div>

            <!-- c. 处置建议 -->
            <div v-if="result.suggestions?.length" class="card sugg-card">
              <div class="section-title">{{ t('whatIf.suggestions') }}</div>
              <ul class="sugg-list">
                <li v-for="(s, i) in result.suggestions" :key="i">{{ s }}</li>
              </ul>
            </div>
          </div>
        </AsyncSection>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * CapacityWhatIf — 上架模拟器 (容量 What-if)
 *
 * 纯查询交互页: 基线 GET 一次 + 推演 POST 按需触发。
 * 交互: 滑块变化 debounce 400ms 自动重推演, 「立即推演」按钮兜底;
 * 结果区用 AsyncSection 三态 (首推前 EmptyStateCard 引导, 失败可重试, 禁止静默)。
 * 注意: 后端 dims[].id 为中文字符串 (机柜空间/电力容量/...), 直接展示, 不按英文 key 匹配。
 */
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AsyncSection from '@/components/common/AsyncSection.vue'
import DataBadge from '@/components/common/DataBadge.vue'
import { useAsyncPage } from '@/composables/useAsyncPage'
import { getCapacityWhatIfBaseline, postCapacityWhatIf } from '@/api'
import type { WhatIfResult, WhatIfResultDim } from '@/types/capacity'

const { t } = useI18n()

/* ---------- 基线 ---------- */
const base = useAsyncPage(getCapacityWhatIfBaseline, { autoLoad: true })
const isRealBase = computed(() => base.data.value?._source === 'real')

/* ---------- 表单参数 ---------- */
const form = reactive({
  cabinets: 50,
  kwPerCabinet: 8,
  monthsHorizon: 24,
  idcCode: 'DC1',
})

/* ---------- 推演 (按需触发) ---------- */
const result = ref<WhatIfResult | null>(null)

const run = useAsyncPage<WhatIfResult>(() => postCapacityWhatIf({ ...form }), {
  autoLoad: false,
  keepDataOnError: true,
  onSuccess: (d) => {
    result.value = d
  },
})

const runBusy = computed(() => run.busy.value)
const runError = computed(() => run.error.value)
const runLoaded = computed(() => run.loaded.value)

function runNow() {
  run.reload()
}

/* 滑块变化 debounce 400ms 自动重推演 */
let debounceTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => [form.cabinets, form.kwPerCabinet, form.monthsHorizon],
  () => {
    if (debounceTimer) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(() => {
      debounceTimer = null
      runNow()
    }, 400)
  },
)

/* ---------- 派生 ---------- */
/** 按 headroomPercent 升序: 余量最小的维度最优先展示 */
const sortedDims = computed<WhatIfResultDim[]>(() =>
  [...(result.value?.dims ?? [])].sort((a, b) => a.headroomPercent - b.headroomPercent),
)

function clampPct(p: number): number {
  return Math.max(0, Math.min(100, p))
}

function pctClass(p: number): string {
  if (p >= 100) return 'lv-over'
  if (p >= 85) return 'lv-warn'
  return 'lv-ok'
}

function fmt(n: number): string {
  return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

/** "now" → 当前已超(红); null → 24 个月内安全(灰); "YYYY-MM" → 到达月份 */
function monthText(m: string | null): string {
  if (m === 'now') return t('whatIf.now')
  if (!m) return t('whatIf.safe')
  return t('whatIf.withinHorizon', { month: m })
}

function monthClass(m: string | null): string {
  if (m === 'now') return 'lv-over'
  if (!m) return 'lv-safe'
  return 'lv-warn'
}
</script>

<style scoped>
.wi-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 14px;
  align-items: start;
}
@media (max-width: 900px) {
  .wi-layout {
    grid-template-columns: 1fr;
  }
}

/* ---------- 左栏参数 ---------- */
.wi-params {
  display: flex;
  flex-direction: column;
  gap: 18px;
  position: sticky;
  top: 14px;
}
.slider-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.slider-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
}
.slider-head label {
  font-size: 12px;
  color: var(--txt2);
}
.slider-val {
  font-size: 22px;
  font-weight: 700;
  color: var(--txt-strong);
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace;
  letter-spacing: 0.5px;
}
.slider-val em {
  font-style: normal;
  font-size: 11px;
  font-weight: 500;
  color: var(--txt3);
  margin-left: 4px;
}
.wi-params input[type='range'] {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: 6px;
  border-radius: 4px;
  background: var(--track, rgba(255, 255, 255, 0.1));
  outline: none;
  cursor: pointer;
}
.wi-params input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: linear-gradient(180deg, #22e3ff, #3b82f6);
  border: 2px solid rgba(255, 255, 255, 0.85);
  box-shadow: 0 0 8px rgba(34, 227, 255, 0.6);
  cursor: pointer;
}
.wi-params input[type='range']::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: linear-gradient(180deg, #22e3ff, #3b82f6);
  border: 2px solid rgba(255, 255, 255, 0.85);
  box-shadow: 0 0 8px rgba(34, 227, 255, 0.6);
  cursor: pointer;
}
.wi-run {
  justify-content: center;
  padding: 11px 16px;
  font-size: 13.5px;
}
.run-spin {
  animation: wi-spin 0.9s linear infinite;
}
@keyframes wi-spin {
  to {
    transform: rotate(360deg);
  }
}

/* ---------- 右栏结果 ---------- */
.wi-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.dims-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 12px;
}
.dim-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: border-color 0.2s;
}
.dim-card.bottleneck {
  border-color: rgba(255, 77, 94, 0.65);
  box-shadow:
    0 0 0 1px rgba(255, 77, 94, 0.25),
    0 0 18px rgba(255, 77, 94, 0.12);
}
.bn-badge {
  position: absolute;
  top: 0;
  right: 0;
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #fff;
  background: linear-gradient(90deg, #ff4d5e, #ff7a45);
  padding: 2px 9px;
  border-radius: 0 11px 0 9px;
}
.dim-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}
.dim-name {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--txt-strong);
}
.dim-usage {
  font-size: 11px;
  color: var(--txt2);
}
.mono {
  font-family: ui-monospace, 'Cascadia Mono', Consolas, monospace;
}

/* 双层条: 上层=当前(青/蓝), 下层=推演后(按阈值着色) */
.bar-track {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  border-radius: 8px;
  background: var(--track, rgba(255, 255, 255, 0.05));
  border: 1px solid var(--line);
}
.bar-row {
  height: 8px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}
.bar-row i {
  display: block;
  height: 100%;
  border-radius: 5px;
  transition: width 0.5s ease;
}
.bar-now {
  background: linear-gradient(90deg, var(--cyan, #22e3ff), var(--blue, #3b82f6));
  opacity: 0.75;
}
.bar-after.lv-ok {
  background: linear-gradient(90deg, #22e3ff, #3b82f6);
}
.bar-after.lv-warn {
  background: linear-gradient(90deg, #d9a441, #f0b95a);
}
.bar-after.lv-over {
  background: linear-gradient(90deg, #ff4d5e, #ff7a45);
}
.dim-foot {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px;
}
.cap {
  font-size: 11px;
  color: var(--txt3);
}
.pct {
  font-size: 16px;
  font-weight: 700;
}
.pct.lv-ok {
  color: var(--cyan, #22e3ff);
}
.pct.lv-warn {
  color: #d9a441;
}
.pct.lv-over {
  color: #ff4d5e;
}
.dim-extra {
  font-size: 10.5px;
  color: var(--txt3);
  border-top: 1px dashed var(--line);
  padding-top: 8px;
}

/* 到达阈值时间 */
.reach-rows {
  display: flex;
  flex-direction: column;
}
.reach-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 10px;
  align-items: center;
  padding: 9px 4px;
  border-bottom: 1px dashed var(--line);
}
.reach-row:last-child {
  border-bottom: none;
}
.reach-cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.reach-cell b {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--txt3);
}
.reach-cell em {
  font-style: normal;
  font-size: 12.5px;
  font-weight: 700;
}
em.lv-warn {
  color: #d9a441;
}
em.lv-over {
  color: #ff4d5e;
}
em.lv-safe {
  color: var(--txt3);
  font-weight: 500;
}

/* 处置建议 */
.sugg-list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sugg-list li {
  position: relative;
  padding-left: 16px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--txt);
}
.sugg-list li::before {
  content: '';
  position: absolute;
  left: 2px;
  top: 7px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #d9a441;
  box-shadow: 0 0 6px rgba(217, 164, 65, 0.7);
}

/* 基线来源标注 */
.baseline-real {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #3ddc97;
  padding: 4px 10px;
  border: 1px solid rgba(61, 220, 151, 0.35);
  border-radius: 999px;
  background: rgba(61, 220, 151, 0.1);
}
.baseline-real .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3ddc97;
  box-shadow: 0 0 6px rgba(61, 220, 151, 0.8);
}
.baseline-note {
  font-size: 11px;
  color: var(--txt3);
}
</style>
