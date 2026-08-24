<template>
  <div class="u-pos">
    <div class="u-pos__head">
      <div>
        <h2 class="u-pos__title">{{ t('ops.uPosition.title') }}</h2>
        <p class="u-pos__sub">
          {{ t('ops.uPosition.subtitle') }} · {{ t('ops.uPosition.multiSource') }}
        </p>
      </div>
      <div class="u-pos__actions">
        <select v-model="selectedCabinet" class="u-pos__select" @change="onSelectCabinet">
          <option v-for="c in cabinets" :key="c.id" :value="c.id">
            {{ c.code }} · {{ c.room }}
          </option>
        </select>
        <button class="btn btn--primary" :disabled="recognizing" @click="runRecognize">
          <BoxesIcon class="ic" /> {{ recognizing ? t('ops.uPosition.recognizing') : t('ops.uPosition.recognize') }}
        </button>
        <button class="btn" :disabled="!result" @click="exportReport">
          <DownloadIcon class="ic" /> {{ t('ops.uPosition.export') }}
        </button>
      </div>
    </div>

    <div v-if="!result && loading" class="u-pos__hint">{{ t('ops.uPosition.loading') }}</div>
    <div v-else-if="!result && !loading" class="u-pos__hint u-pos__hint--err">
      {{ t('ops.uPosition.failed') }}
    </div>

    <div v-else class="u-pos__body">
      <!-- 左: U 位立面图 -->
      <section class="u-pos__rack">
        <div class="rack__head">
          <span class="rack__code">{{ result?.code ?? '' }}</span>
          <span class="rack__meta">{{ result?.room ?? '' }} · {{ t('ops.uPosition.uTotal', { n: result?.uTotal ?? 42 }) }}</span>
        </div>
        <div class="rack__scroll">
          <svg :width="rackW" :height="rackH" class="rack__svg" :viewBox="`0 0 ${rackW} ${rackH}`">
            <!-- 机柜外框 -->
            <rect :x="labelW" :y="pad" :width="rackW - labelW - pad" :height="rackH - pad * 2"
                  rx="6" fill="#0b1220" stroke="#1f2937" stroke-width="2" />
            <g v-for="cell in cellsTopDown" :key="cell.u">
              <rect :x="labelW + 2" :y="cell.y" :width="rackW - labelW - pad - 4" :height="uH - 2"
                    :fill="cellFill(cell)" :stroke="cellStroke(cell)" stroke-width="1"
                    :class="{ 'cell--conflict': cell.status === 'conflict' }" @click="onClickCell(cell)" />
              <text :x="labelW - 6" :y="cell.y + uH / 2 + 4" text-anchor="end"
                    class="u-label" :fill="cell.status === 'conflict' ? '#fca5a5' : '#94a3b8'">
                U{{ cell.u }}
              </text>
              <text v-if="cell.status !== 'empty'" :x="labelW + 12" :y="cell.y + uH / 2 + 4"
                    class="u-dev" fill="#e2e8f0">
                {{ deviceLabel(cell) }}
              </text>
              <text v-if="cell.status === 'conflict'" :x="rackW - pad - 8" :y="cell.y + uH / 2 + 4"
                    text-anchor="end" class="u-warn" fill="#fca5a5">⚠ {{ Math.round(cell.confidence * 100) }}%</text>
              <text v-else-if="cell.status === 'occupied'" :x="rackW - pad - 8" :y="cell.y + uH / 2 + 4"
                    text-anchor="end" class="u-conf" fill="#5eead4">{{ Math.round(cell.confidence * 100) }}%</text>
            </g>
          </svg>
        </div>
        <div class="rack__legend">
          <span><i class="dot dot--occ" /> {{ t('ops.uPosition.occupied') }}</span>
          <span><i class="dot dot--empty" /> {{ t('ops.uPosition.empty') }}</span>
          <span><i class="dot dot--conf" /> {{ t('ops.uPosition.conflict') }}</span>
        </div>
      </section>

      <!-- 右: 多源识别面板 -->
      <section class="u-pos__panel">
        <div class="panel__stats">
          <div class="stat">
            <div class="stat__num">{{ result?.summary?.occupied ?? 0 }}</div>
            <div class="stat__lbl">{{ t('ops.uPosition.occupied') }}</div>
          </div>
          <div class="stat">
            <div class="stat__num stat__num--green">{{ result?.summary?.empty ?? 0 }}</div>
            <div class="stat__lbl">{{ t('ops.uPosition.empty') }}</div>
          </div>
          <div class="stat">
            <div class="stat__num stat__num--red">{{ result?.summary?.conflict ?? 0 }}</div>
            <div class="stat__lbl">{{ t('ops.uPosition.conflict') }}</div>
          </div>
          <div class="stat">
            <div class="stat__num stat__num--blue">{{ Math.round((result?.summary?.avgConfidence ?? 1) * 100) }}%</div>
            <div class="stat__lbl">{{ t('ops.uPosition.avgConf') }}</div>
          </div>
        </div>

        <div class="panel__src">
          <h4>{{ t('ops.uPosition.sources') }}</h4>
          <div v-for="s in (result?.sources ?? [])" :key="s.key" class="src">
            <div class="src__top">
              <span class="src__name">
                <component :is="s.key === 'rfid' ? RadioIcon : FileTextIcon" class="ic" />
                {{ s.name }}
              </span>
              <span class="src__cnt">{{ s.count }} {{ t('ops.uPosition.devices') }}</span>
            </div>
            <div class="src__bar">
              <div class="src__bar-fill" :style="{ width: s.confidence * 100 + '%' }"
                   :class="s.key === 'rfid' ? 'fill--rfid' : 'fill--ledger'" />
            </div>
            <div class="src__conf">{{ t('ops.uPosition.sourceConf', { n: Math.round(s.confidence * 100) }) }}</div>
          </div>
        </div>

        <div class="panel__conflicts">
          <h4>
            {{ t('ops.uPosition.conflictList') }}
            <span class="badge" :class="(result?.conflicts?.length ?? 0) ? 'badge--red' : 'badge--green'">
              {{ result?.conflicts?.length ?? 0 }}
            </span>
          </h4>
          <div v-if="!(result?.conflicts?.length ?? 0)" class="conf-empty">
            {{ t('ops.uPosition.noConflict') }}
          </div>
          <ul v-else class="conf-list">
            <li v-for="(c, i) in (result?.conflicts ?? [])" :key="i" class="conf-item" :class="c.severity === 'crit' ? 'conf-item--crit' : ''">
              <AlertTriangleIcon class="ic ic--warn" />
              <div>
                <div class="conf-item__u">U{{ c.u }} · {{ conflictTypeLabel(c.type) }}</div>
                <div class="conf-item__detail">{{ c.detail }}</div>
                <div class="conf-item__assets">{{ c.assetNos.join(', ') }}</div>
              </div>
            </li>
          </ul>
        </div>

        <div v-if="selectedDevice" class="panel__detail">
          <h4>{{ t('ops.uPosition.deviceDetail') }}</h4>
          <pre class="detail-json">{{ JSON.stringify(selectedDevice, null, 2) }}</pre>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import {
  AlertTriangleIcon,
  BoxesIcon,
  DownloadIcon,
  FileTextIcon,
  RadioIcon,
} from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { getCabinetOptions, getServers, recognizeUPosition, getUPosition } from '@/api'
import type { CabinetOption, RecognizeResp, ServerItem, UCell } from '@/types'

const { t } = useI18n()

const cabinets = ref<CabinetOption[]>([])
const selectedCabinet = ref<number>(1)
const result = ref<RecognizeResp | null>(null)
const loading = ref(false)
const recognizing = ref(false)
const servers = ref<ServerItem[]>([])
const selectedDevice = ref<ServerItem | null>(null)

const uH = 16
const pad = 14
const labelW = 42
const rackW = 320
const rackH = computed(() => pad * 2 + (result.value?.uTotal ?? 42) * uH)

const cellsTopDown = computed(() => {
  if (!result.value) return []
  const total = result.value.uTotal
  // 自下而上: u=1 在最底部; 附加 y 坐标供 SVG 使用
  return result.value.cells
    .map((c) => ({ ...c, y: pad + (total - c.u) * uH }))
    .reverse()
})

function cellFill(cell: UCell): string {
  if (cell.status === 'conflict') return '#7f1d1d'
  if (cell.status === 'occupied') return '#0f3b3b'
  if (cell.status === 'reserved') return '#3b2f0f'
  return '#0b1220'
}
function cellStroke(cell: UCell): string {
  if (cell.status === 'conflict') return '#ef4444'
  if (cell.status === 'occupied') return '#14b8a6'
  if (cell.status === 'reserved') return '#eab308'
  return '#1f2937'
}
function deviceLabel(cell: UCell): string {
  const s = servers.value.find((x) => x.id === cell.deviceRefs[0])
  if (!s) return ''
  if (cell.status === 'conflict') return '⚠ ' + s.hostname
  return s.hostname
}

function conflictTypeLabel(type: string): string {
  return (
    {
      range_overlap: t('ops.uPosition.cRangeOverlap'),
      ledger_mismatch: t('ops.uPosition.cLedgerMismatch'),
      reservation_clash: t('ops.uPosition.cReservationClash'),
    } as Record<string, string>
  )[type] ?? type
}

function onClickCell(cell: UCell & { y: number }) {
  const id = cell.deviceRefs[0]
  selectedDevice.value = servers.value.find((s) => s.id === id) ?? null
}

async function onSelectCabinet() {
  selectedDevice.value = null
  await loadCabinet()
}

async function loadCabinet() {
  loading.value = true
  try {
    const [cab, srv] = await Promise.all([
      getUPosition(selectedCabinet.value),
      getServers(selectedCabinet.value),
    ])
    servers.value = srv
    result.value = {
      ...cab,
      sources: [],
      summary: {
        totalU: cab.uTotal,
        occupied: cab.occupiedU,
        empty: cab.emptyU,
        conflict: cab.conflictU,
        avgConfidence: 1,
        ledgerCount: 0,
        rfidCount: srv.length,
      },
      recognizedAt: cab.generatedAt,
    } as unknown as RecognizeResp
  } catch (e) {
    result.value = null
  } finally {
    loading.value = false
  }
}

async function runRecognize() {
  recognizing.value = true
  try {
    const r = await recognizeUPosition(selectedCabinet.value)
    result.value = r
    servers.value = await getServers(selectedCabinet.value)
  } catch (e) {
    // 静默: 保留既有立面
  } finally {
    recognizing.value = false
  }
}

function exportReport() {
  if (!result.value) return
  const lines = [
    `# U 位识别报告 ${result.value.code} @ ${result.value.recognizedAt}`,
    `机柜: ${result.value.code} (${result.value.room})  总U: ${result.value.uTotal}`,
    `占用: ${result.value.summary.occupied}  空置: ${result.value.summary.empty}  冲突: ${result.value.summary.conflict}  平均置信度: ${Math.round(result.value.summary.avgConfidence * 100)}%`,
    '',
    '## 识别来源',
    ...result.value.sources.map((s) => `- ${s.name}: ${s.count} 台, 置信度 ${Math.round(s.confidence * 100)}%`),
    '',
    '## 冲突清单',
    ...(result.value.conflicts.length
      ? result.value.conflicts.map((c) => `- [U${c.u}] ${conflictTypeLabel(c.type)}: ${c.detail} (${c.assetNos.join(', ')})`)
      : ['- 无冲突']),
  ]
  const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `u-position-${result.value.code}-${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  try {
    const r = await getCabinetOptions({ size: 200 })
    cabinets.value = r.items
    if (r.items.length) selectedCabinet.value = r.items[0].id
  } catch (e) {
    // 兜底: 生成若干机柜
    cabinets.value = Array.from({ length: 12 }, (_, i) => ({
      id: i + 1,
      code: `A${String.fromCharCode(65 + (i % 3))}-${String(i + 1).padStart(2, '0')}`,
      room: i < 4 ? 'A01 机房' : i < 8 ? 'B02 机房' : 'C03 机房',
      row: 'A',
      uTotal: 42,
    }))
    selectedCabinet.value = 1
  }
  await loadCabinet()
})
</script>

<style scoped>
.u-pos { padding: 16px 20px 32px; color: #e2e8f0; }
.u-pos__head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
.u-pos__title { font-size: 20px; font-weight: 700; margin: 0; }
.u-pos__sub { color: #94a3b8; font-size: 13px; margin: 4px 0 0; }
.u-pos__actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.u-pos__select { background: #0b1220; border: 1px solid #1f2937; color: #e2e8f0; border-radius: 8px; padding: 8px 10px; font-size: 13px; }
.btn { display: inline-flex; align-items: center; gap: 6px; background: #111827; border: 1px solid #1f2937; color: #e2e8f0; border-radius: 8px; padding: 8px 12px; font-size: 13px; cursor: pointer; }
.btn:hover { border-color: #334155; }
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn--primary { background: #0ea5e9; border-color: #0ea5e9; color: #fff; }
.ic { width: 16px; height: 16px; }
.u-pos__hint { padding: 40px; text-align: center; color: #94a3b8; }
.u-pos__hint--err { color: #fca5a5; }
.u-pos__body { display: grid; grid-template-columns: 360px 1fr; gap: 20px; align-items: start; }
@media (max-width: 920px) { .u-pos__body { grid-template-columns: 1fr; } }

.u-pos__rack { background: #0f172a; border: 1px solid #1f2937; border-radius: 12px; padding: 14px; }
.rack__head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; }
.rack__code { font-size: 16px; font-weight: 700; color: #5eead4; }
.rack__meta { font-size: 12px; color: #94a3b8; }
.rack__scroll { overflow-y: auto; max-height: 700px; }
.rack__svg { display: block; }
.u-label { font-size: 10px; font-family: monospace; }
.u-dev { font-size: 10px; font-family: monospace; }
.u-conf { font-size: 10px; font-weight: 600; }
.u-warn { font-size: 10px; font-weight: 700; }
.cell--conflict { animation: blink 1.1s infinite; }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: .55; } }
.rack__legend { display: flex; gap: 14px; margin-top: 10px; font-size: 12px; color: #94a3b8; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 5px; vertical-align: middle; }
.dot--occ { background: #14b8a6; }
.dot--empty { background: #334155; }
.dot--conf { background: #ef4444; }

.u-pos__panel { display: flex; flex-direction: column; gap: 16px; }
.panel__stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat { background: #0f172a; border: 1px solid #1f2937; border-radius: 10px; padding: 12px; text-align: center; }
.stat__num { font-size: 24px; font-weight: 700; }
.stat__num--green { color: #34d399; }
.stat__num--red { color: #f87171; }
.stat__num--blue { color: #60a5fa; }
.stat__lbl { font-size: 12px; color: #94a3b8; margin-top: 2px; }

.panel__src, .panel__conflicts, .panel__detail { background: #0f172a; border: 1px solid #1f2937; border-radius: 10px; padding: 14px; }
.panel__src h4, .panel__conflicts h4, .panel__detail h4 { margin: 0 0 10px; font-size: 14px; }
.src { margin-bottom: 12px; }
.src__top { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.src__name { display: inline-flex; align-items: center; gap: 6px; }
.src__cnt { color: #94a3b8; font-size: 12px; }
.src__bar { height: 6px; background: #1e293b; border-radius: 4px; margin: 6px 0 4px; overflow: hidden; }
.src__bar-fill { height: 100%; border-radius: 4px; }
.fill--rfid { background: #38bdf8; }
.fill--ledger { background: #a78bfa; }
.src__conf { font-size: 11px; color: #94a3b8; }

.badge { display: inline-block; min-width: 20px; text-align: center; padding: 1px 7px; border-radius: 10px; font-size: 12px; }
.badge--red { background: #7f1d1d; color: #fecaca; }
.badge--green { background: #064e3b; color: #a7f3d0; }
.conf-empty { color: #34d399; font-size: 13px; }
.conf-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.conf-item { display: flex; gap: 8px; background: #1c1414; border: 1px solid #7f1d1d; border-radius: 8px; padding: 8px 10px; }
.conf-item--crit { border-color: #ef4444; }
.ic--warn { width: 16px; height: 16px; color: #f87171; flex-shrink: 0; margin-top: 2px; }
.conf-item__u { font-size: 13px; font-weight: 600; color: #fecaca; }
.conf-item__detail { font-size: 12px; color: #e2e8f0; margin-top: 2px; }
.conf-item__assets { font-size: 11px; color: #94a3b8; margin-top: 2px; font-family: monospace; }
.detail-json { background: #020617; border: 1px solid #1f2937; border-radius: 8px; padding: 10px; font-size: 11px; color: #94a3b8; max-height: 220px; overflow: auto; }
</style>
