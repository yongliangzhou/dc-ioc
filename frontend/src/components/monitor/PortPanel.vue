<template>
  <div class="port-panel">
    <div class="pp-header">
      <span class="pp-title">{{ title }}</span>
      <div class="pp-legend">
        <span class="pp-lg"><i class="pp-dot" style="background: #22c55e"></i> UP</span>
        <span class="pp-lg"><i class="pp-dot" style="background: #f59e0b"></i> 告警</span>
        <span class="pp-lg"><i class="pp-dot" style="background: #374151"></i> DOWN</span>
      </div>
    </div>
    <div class="pp-grid" v-if="ports.length">
      <div
        v-for="(p, i) in ports"
        :key="p.name"
        class="pp-port"
        :class="[portClass(p), { 'pp-selected': selectedIndex === i }]"
        @click="select(i)"
        :title="portTooltip(p)"
      >
        <span class="pp-num">{{ portIndex(p.name) }}</span>
        <span class="pp-speed-indicator" :class="speedCls(p)"></span>
      </div>
      <!-- fill empty slots to 48 -->
      <div
        v-for="i in Math.max(0, 48 - ports.length)"
        :key="'empty-' + i"
        class="pp-port pp-empty"
      ></div>
    </div>
    <div class="pp-grid pp-empty-placeholder" v-else>
      <div v-for="i in 48" :key="'sk-' + i" class="pp-port pp-empty"></div>
    </div>
    <!-- detail card on selection -->
    <div class="pp-detail" v-if="selectedIndex !== null && ports[selectedIndex]">
      <div class="pp-detail-head">
        <span class="pp-detail-name mono">{{ ports[selectedIndex].name }}</span>
        <span class="pp-detail-status" :class="portClass(ports[selectedIndex])">
          {{ ports[selectedIndex].status === 'up' ? 'UP' : 'DOWN' }}
        </span>
        <button class="pp-close" @click="selectedIndex = null">✕</button>
      </div>
      <div class="pp-detail-grid">
        <div class="pp-kv">
          <span class="pp-k">速率</span
          ><span class="pp-v mono">{{ ports[selectedIndex].speed_mbps }}M</span>
        </div>
        <div class="pp-kv">
          <span class="pp-k">入流量</span
          ><span class="pp-v mono">{{ fmtBps(ports[selectedIndex].in_bps) }}</span>
        </div>
        <div class="pp-kv">
          <span class="pp-k">出流量</span
          ><span class="pp-v mono">{{ fmtBps(ports[selectedIndex].out_bps) }}</span>
        </div>
        <div class="pp-kv">
          <span class="pp-k">入利用率</span>
          <span class="pp-v mono" :class="utilCls(ports[selectedIndex].in_util_pct)">
            {{ ports[selectedIndex].in_util_pct }}%
          </span>
        </div>
        <div class="pp-kv">
          <span class="pp-k">出利用率</span>
          <span class="pp-v mono" :class="utilCls(ports[selectedIndex].out_util_pct)">
            {{ ports[selectedIndex].out_util_pct }}%
          </span>
        </div>
        <div class="pp-kv">
          <span class="pp-k">错包</span>
          <span
            class="pp-v mono"
            :class="
              ports[selectedIndex].in_errors + ports[selectedIndex].out_errors ? 'a-text' : 'g-text'
            "
          >
            {{ ports[selectedIndex].in_errors + ports[selectedIndex].out_errors }}
          </span>
        </div>
        <div class="pp-kv" v-if="ports[selectedIndex].rx_power_dbm != null">
          <span class="pp-k">收光</span
          ><span class="pp-v mono">{{ ports[selectedIndex].rx_power_dbm }}dBm</span>
        </div>
        <div class="pp-kv" v-if="ports[selectedIndex].tx_power_dbm != null">
          <span class="pp-k">发光</span
          ><span class="pp-v mono">{{ ports[selectedIndex].tx_power_dbm }}dBm</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import type { SwitchPortView } from '@/api/monitor'
import { fmtBps, utilCls } from '@/utils/format'

const props = withDefaults(
  defineProps<{
    ports: SwitchPortView[]
    title?: string
  }>(),
  {
    title: '设备前面板',
  },
)

const selectedIndex = ref<number | null>(null)

function select(i: number) {
  selectedIndex.value = selectedIndex.value === i ? null : i
}

function portIndex(name: string): string {
  const m = name.match(/(\d+)\/(\d+)\/(\d+)/)
  if (m) return m[3]
  const n = name.match(/(\d+)$/)
  return n ? n[1] : name
}

function portClass(p: SwitchPortView): string {
  if (p.status === 'down') return 'pp-down'
  if (p.optical_alarm && p.optical_alarm !== '正常') return 'pp-alarm'
  if (p.in_errors + p.out_errors > 0) return 'pp-alarm'
  return 'pp-up'
}

function speedCls(p: SwitchPortView): string {
  if (p.speed_mbps >= 25000) return 'spd-25g'
  if (p.speed_mbps >= 10000) return 'spd-10g'
  return ''
}

function portTooltip(p: SwitchPortView): string {
  const lines = [`${p.name} (${p.status})`, `速率: ${p.speed_mbps}M`]
  if (p.status === 'up') {
    lines.push(`入: ${fmtBps(p.in_bps)} / 出: ${fmtBps(p.out_bps)}`)
  }
  return lines.join('\n')
}
</script>

<style scoped>
.port-panel {
  border: 1px solid var(--border, #2a2e3a);
  border-radius: 10px;
  padding: 14px;
  background: var(--bg2, #161822);
}
.pp-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.pp-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--txt);
}
.pp-legend {
  display: flex;
  gap: 12px;
  font-size: 10px;
  color: var(--txt3);
}
.pp-lg {
  display: flex;
  align-items: center;
  gap: 4px;
}
.pp-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  display: inline-block;
}
.pp-grid {
  display: grid;
  grid-template-columns: repeat(24, 1fr);
  gap: 3px;
}
.pp-empty-placeholder {
  opacity: 0.3;
}
.pp-port {
  aspect-ratio: 1;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #1e2030;
  border: 1px solid #2a2d3a;
  transition: all 0.15s;
  position: relative;
}
.pp-port:hover {
  transform: scale(1.15);
  z-index: 2;
}
.pp-port.pp-up {
  background: rgba(34, 197, 94, 0.15);
  border-color: rgba(34, 197, 94, 0.4);
}
.pp-port.pp-down {
  opacity: 0.5;
}
.pp-port.pp-alarm {
  background: rgba(245, 158, 11, 0.18);
  border-color: rgba(245, 158, 11, 0.5);
  animation: pp-pulse 1.5s ease-in-out infinite;
}
@keyframes pp-pulse {
  0%,
  100% {
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.3);
  }
  50% {
    box-shadow: 0 0 6px 2px rgba(245, 158, 11, 0.15);
  }
}
.pp-port.pp-selected {
  box-shadow: 0 0 0 2px var(--cyan, #22e3ff);
  z-index: 3;
}
.pp-port.pp-empty {
  cursor: default;
  opacity: 0.15;
  border-style: dashed;
}
.pp-num {
  font-size: 8px;
  font-family: 'SF Mono', Consolas, monospace;
  color: inherit;
  line-height: 1;
}
.pp-speed-indicator {
  width: 3px;
  height: 3px;
  border-radius: 50%;
  margin-top: 1px;
}
.pp-speed-indicator.spd-25g {
  background: #22e3ff;
}
.pp-speed-indicator.spd-10g {
  background: #a78bfa;
}
.pp-detail {
  margin-top: 10px;
  padding: 10px 12px;
  background: var(--bg1, #0f1017);
  border-radius: 8px;
  border: 1px solid var(--border);
}
.pp-detail-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}
.pp-detail-name {
  font-weight: 600;
  font-size: 13px;
}
.pp-detail-status {
  font-size: 10px;
  padding: 1px 7px;
  border-radius: 10px;
  font-weight: 600;
}
.pp-detail-status.pp-up {
  color: #22c55e;
  background: rgba(34, 197, 94, 0.12);
}
.pp-detail-status.pp-down {
  color: #6b7280;
  background: rgba(107, 114, 128, 0.12);
}
.pp-detail-status.pp-alarm {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.12);
}
.pp-close {
  margin-left: auto;
  background: none;
  border: none;
  color: var(--txt3);
  cursor: pointer;
  font-size: 14px;
  padding: 2px 6px;
}
.pp-detail-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px 12px;
}
.pp-kv {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.pp-k {
  font-size: 10px;
  color: var(--txt2);
}
.pp-v {
  font-size: 12px;
  color: var(--txt);
  font-weight: 600;
}
.mono {
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', Consolas, monospace;
}
.g-text {
  color: var(--green, #22c55e);
}
.a-text {
  color: var(--amber, #f59e0b);
}
</style>
