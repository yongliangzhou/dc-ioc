<template>
  <div class="linkage-view">
    <div class="view-head">
      <h1>{{ tl('制冷链路可视化') }}</h1>
      <span class="sub">{{ tl('制冷一次系统 · 冷却水/冷冻水双循环') }}</span>
      <button class="refresh" @click="load" :disabled="loading">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        {{ tl('刷新') }}
      </button>
    </div>

    <div class="legend">
      <span><i class="dot normal" /> {{ tl('正常') }}</span>
      <span><i class="dot warning" /> {{ tl('预警') }}</span>
      <span><i class="dot fault" /> {{ tl('故障') }}</span>
      <span><i class="dot off" /> {{ tl('离线/停机') }}</span>
      <span class="pipe-key"><i class="line cw" /> {{ tl('冷却水') }}</span>
      <span class="pipe-key"><i class="line chw" /> {{ tl('冷冻水') }}</span>
      <span class="muted">{{ tl('点击设备查看状态 · 跳转对应监控页') }}</span>
    </div>

    <CoolingLinkageDiagram :nodes="nodes" :pipes="pipes" @device-click="onDeviceClick" />

    <transition name="slide">
      <div v-if="selected" class="drawer" @click.self="selected = null">
        <div class="drawer-card">
          <div class="drawer-head">
            <div>
              <h3>{{ selected.title }}</h3>
              <span class="muted">{{ selected.sub }}</span>
            </div>
            <button class="close" @click="selected = null">✕</button>
          </div>
          <div class="drawer-metrics">
            <div v-for="m in selectedMetrics" :key="m.k" class="metric">
              <span class="mk">{{ m.k }}</span>
              <span class="mv">{{ m.v }}</span>
            </div>
          </div>
          <button class="goto" @click="gotoDevice(selected)">{{ tl('跳转设备监控页') }} →</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import CoolingLinkageDiagram, { CoolingDevice, CoolingPipe } from '@/components/hvac/CoolingLinkageDiagram.vue'
import { getChillerPlant } from '@/api/hvac'
import type { ChillerSummary } from '@/api/hvac'

const { t: tl } = useI18n()
const router = useRouter()

const loading = ref(false)
const data = ref<ChillerSummary | null>(null)
const selected = ref<CoolingDevice | null>(null)

const W = 1120
const COLS = ['tower', 'cwpump', 'chiller', 'chwPump', 'hex', 'tank'] as const
const colX: Record<string, number> = {
  tower: 110,
  cwpump: 320,
  chiller: 560,
  chwPump: 790,
  hex: 980,
  tank: 560,
}
const rowYTop = 140
const rowYBot = 420

function statusOf(state: string): CoolingDevice['status'] {
  if (!state) return 'off'
  const s = String(state).toLowerCase()
  if (s.includes('fault') || s.includes('故障')) return 'fault'
  if (s.includes('warn') || s.includes('预警') || s === 'alarm' || s === 'maintenance') return 'warning'
  if (s === 'off' || s === 'offline' || s === 'stop' || s === '停机' || s === '0') return 'off'
  return 'normal'
}

function place(list: Array<Record<string, any>>, col: string, top: boolean) {
  const n = list.length
  if (!n) return []
  const out: CoolingDevice[] = []
  list.forEach((it, i) => {
    const gap = Math.min(80, 200 / n)
    const y = (top ? rowYTop : rowYBot) + (i - (n - 1) / 2) * gap
    out.push({
      id: (col + (it.code ?? i)),
      title: it.name || it.code || (col + (i + 1)),
      sub: it.state,
      status: statusOf(it.state ?? it.status),
      x: colX[col],
      y,
      kind: col,
      meta: { raw: it, col },
    })
  })
  return out
}

const nodes = computed<CoolingDevice[]>(() => {
  const d = data.value
  if (!d) return []
  const list: CoolingDevice[] = []
  list.push(...place(d.towers ?? [], 'tower', true))
  list.push(...place(d.pumpsCw ?? [], 'cwpump', true))
  list.push(...place(d.chillers ?? [], 'chiller', false))
  list.push(...place(d.pumpsChw ?? [], 'chwPump', false))
  list.push(...place(d.hexs ?? [], 'hex', false))
  // 蓄冷罐（聚合节点）
  const st = d.storageTank
  if (st) {
    list.push({
      id: 'tank',
      title: tl('蓄冷罐'),
      sub: '液位 ' + (st.level ?? '-') + '%',
      status: 'normal',
      x: colX.tank,
      y: 280,
      kind: 'tank',
      meta: { raw: st, col: 'tank' },
    })
  }
  return list
})

// 管道：按列中心连线，代表该段水管走向
function pipeBetween(fromCol: string, toCol: string, kind: CoolingPipe['kind'], yFrom?: number, yTo?: number): CoolingPipe {
  const x1 = colX[fromCol]
  const x2 = colX[toCol]
  const y1 = yFrom ?? (fromCol === 'tower' || fromCol === 'cwpump' ? rowYTop : rowYBot)
  const y2 = yTo ?? (toCol === 'chiller' || toCol === 'cwpump' ? rowYBot : rowYBot)
  // 折线：先水平到中间，再竖直到目标行
  const midX = (x1 + x2) / 2
  const d = `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`
  return { d, kind, dur: kind === 'cw' ? '3s' : '3.4s' }
}

const pipes = computed<CoolingPipe[]>(() => {
  const d = data.value
  if (!d) return []
  const ps: CoolingPipe[] = []
  // 冷却水循环（蓝）：冷却塔 → 冷却泵 → 冷机
  ps.push(pipeBetween('tower', 'cwpump', 'cw', rowYTop, rowYTop))
  ps.push(pipeBetween('cwpump', 'chiller', 'cw', rowYTop, rowYBot))
  // 冷冻水循环（青）：冷机 → 冷冻泵 → 末端 → 蓄冷罐 → 回冷机
  ps.push(pipeBetween('chiller', 'chwPump', 'chw', rowYBot, rowYBot))
  ps.push(pipeBetween('chwPump', 'hex', 'chw', rowYBot, rowYBot))
  ps.push(pipeBetween('hex', 'tank', 'chw', rowYBot, 280))
  ps.push(pipeBetween('tank', 'chiller', 'chw', 280, rowYBot))
  return ps
})

const selectedMetrics = computed(() => {
  const raw = selected.value?.meta?.raw as Record<string, any>
  if (!raw) return []
  const map: Record<string, string> = {
    state: '状态', code: '编码', name: '名称', hz: '频率', kw: '功率',
    flow: '流量', fanHz: '风机频率', outTemp: '出水温', level: '液位',
    eff: '效率', loadPercent: '负载', cop: 'COP', temperatureIn: '进水温',
    temperatureOut: '出水温', coolingCapacity: '冷量',
  }
  return Object.keys(map)
    .filter((k) => raw[k] !== undefined && raw[k] !== null)
    .map((k) => ({ k: map[k], v: String(raw[k]) }))
})

function onDeviceClick(n: CoolingDevice) {
  selected.value = n
}

function gotoDevice(n: CoolingDevice) {
  const col = n.meta?.col as string
  if (col === 'chiller' || col === 'tower' || col === 'cwpump' || col === 'chwPump') {
    router.push('/monitor/hvac/chiller')
  } else if (col === 'hex' || col === 'tank') {
    router.push('/monitor/hvac/crac')
  } else {
    router.push('/monitor/hvac')
  }
  selected.value = null
}

async function load() {
  loading.value = true
  try {
    data.value = await getChillerPlant()
  } catch (e) {
    console.error('制冷链路加载失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.linkage-view { padding: 16px 20px 32px; }
.view-head { display: flex; align-items: center; gap: 14px; }
.view-head h1 { font-size: 20px; margin: 0; color: #e2e8f0; }
.sub { color: #64748b; font-size: 13px; }
.refresh {
  background: #1e293b; color: #cbd5e1; border: 1px solid #334155;
  border-radius: 8px; padding: 6px 12px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px; margin-left: auto;
}
.legend { display: flex; gap: 14px; align-items: center; margin: 14px 0; font-size: 12px; color: #94a3b8; flex-wrap: wrap; }
.legend .dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 5px; vertical-align: middle; }
.dot.normal { background: #22c55e; } .dot.warning { background: #f59e0b; } .dot.fault { background: #ef4444; } .dot.off { background: #64748b; }
.pipe-key .line { display: inline-block; width: 18px; height: 4px; border-radius: 2px; margin-right: 5px; vertical-align: middle; }
.line.cw { background: #38bdf8; } .line.chw { background: #2dd4bf; }
.muted { color: #64748b; }
.drawer { position: fixed; inset: 0; background: rgba(2,6,23,0.6); display: flex; justify-content: flex-end; z-index: 50; }
.drawer-card { width: 380px; max-width: 90vw; height: 100%; background: #0f172a; border-left: 1px solid #1e293b; padding: 22px; overflow-y: auto; }
.drawer-head { display: flex; justify-content: space-between; align-items: flex-start; }
.drawer-head h3 { margin: 0 0 4px; color: #e2e8f0; }
.drawer-metrics { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin: 18px 0; }
.metric { background: #1e293b; border-radius: 8px; padding: 10px 12px; }
.mk { display: block; color: #64748b; font-size: 12px; }
.mv { display: block; color: #e2e8f0; font-size: 16px; font-weight: 600; }
.goto { width: 100%; background: #0ea5e9; color: #fff; border: none; border-radius: 8px; padding: 10px; cursor: pointer; font-size: 14px; }
.goto:hover { background: #0284c7; }
.slide-enter-active, .slide-leave-active { transition: opacity 0.2s; }
.slide-enter-from, .slide-leave-to { opacity: 0; }
</style>
