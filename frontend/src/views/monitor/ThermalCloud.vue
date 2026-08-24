<template>
  <div class="thermal-view">
    <div class="view-head">
      <h1>{{ tl('温度云图') }}</h1>
      <div class="layers">
        <button :class="{ on: layer === 'room' }" @click="layer = 'room'">{{ tl('机房层') }}</button>
        <button :class="{ on: layer === 'aisle' }" @click="selectRoom(rooms[0]?.id); layer = 'aisle'">{{ tl('通道层') }}</button>
        <button :class="{ on: layer === 'rack' }" @click="selectRoom(rooms[0]?.id); layer = 'rack'">{{ tl('机柜层') }}</button>
      </div>
      <button class="refresh" @click="load" :disabled="loading">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 4v6h-6M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
        {{ tl('刷新') }}
      </button>
    </div>

    <!-- 区间可调 -->
    <div class="ctrl">
      <label>{{ tl('低温区间') }} <b>{{ coldThreshold }}℃</b></label>
      <input type="range" min="14" max="28" step="0.5" v-model.number="coldThreshold" />
      <label>{{ tl('高温区间') }} <b>{{ hotThreshold }}℃</b></label>
      <input type="range" min="26" max="42" step="0.5" v-model.number="hotThreshold" />
      <span class="scale">
        <i class="s cold" /> {{ tl('偏低') }}
        <i class="s ok" /> {{ tl('正常') }}
        <i class="s hot" /> {{ tl('偏高/热点') }}
      </span>
    </div>

    <!-- 层1 机房层 -->
    <section v-if="layer === 'room'">
      <h2>{{ tl('机房温度分布') }}（{{ tl('点选机房下钻') }}）</h2>
      <div class="board">
        <TemperatureHeatmap
          :cells="roomCells"
          :cols="4"
          :cold-threshold="coldThreshold"
          :hot-threshold="hotThreshold"
          :top-ids="topRoomIds"
          @cell-click="(c) => selectRoom(c.id)"
        />
        <div class="side">
          <div class="side-title">{{ tl('TOP5 热点机房') }}</div>
          <div v-for="(r, i) in topRooms" :key="r.id" class="top-item" @click="selectRoom(r.id)">
            <span class="rank">#{{ i + 1 }}</span>
            <span class="name">{{ r.name }}</span>
            <span class="temp">{{ r.avgTemp.toFixed(1) }}℃</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 层2 通道层 -->
    <section v-if="layer === 'aisle' && currentRoom">
      <h2>{{ tl('通道温度') }} · {{ currentRoom.name }}</h2>
      <div class="aisle-bars">
        <div class="aisle-card cold">
          <span class="lbl">{{ tl('冷通道') }}</span>
          <span class="val">{{ currentRoom.coldAisle.toFixed(1) }}℃</span>
        </div>
        <div class="aisle-card hot">
          <span class="lbl">{{ tl('热通道') }}</span>
          <span class="val">{{ currentRoom.hotAisle.toFixed(1) }}℃</span>
        </div>
        <div class="aisle-card">
          <span class="lbl">{{ tl('通道温差') }}</span>
          <span class="val">{{ (currentRoom.hotAisle - currentRoom.coldAisle).toFixed(1) }}℃</span>
        </div>
      </div>
      <p class="hint">{{ tl('上排为冷通道、下排为热通道的截面温度分布') }}</p>
      <TemperatureHeatmap
        :cells="aisleCells"
        :cols="12"
        :cold-threshold="coldThreshold"
        :hot-threshold="hotThreshold"
        :top-ids="topRackIds"
        @cell-click="onRackClick"
      />
    </section>

    <!-- 层3 机柜层 -->
    <section v-if="layer === 'rack' && currentRoom">
      <h2>{{ tl('机柜进风温度') }} · {{ currentRoom.name }}（{{ tl('TOP5 热点已标注') }}）</h2>
      <div class="board">
        <TemperatureHeatmap
          :cells="rackCells"
          :cols="24"
          :cold-threshold="coldThreshold"
          :hot-threshold="hotThreshold"
          :top-ids="topRackIds"
          @cell-click="onRackClick"
        />
        <div class="side">
          <div class="side-title">{{ tl('TOP5 热点机柜') }}</div>
          <div v-for="(c, i) in topRacks" :key="c.id" class="top-item" @click="onRackClick(c)">
            <span class="rank">#{{ i + 1 }}</span>
            <span class="name">{{ c.label }}</span>
            <span class="temp">{{ c.temp.toFixed(1) }}℃</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import TemperatureHeatmap, { HeatCell } from '@/components/hvac/TemperatureHeatmap.vue'
import { getHvacOverview } from '@/api/hvac'
import type { RoomView } from '@/api/hvac'

const { t: tl } = useI18n()

const loading = ref(false)
const rooms = ref<RoomView[]>([])
const layer = ref<'room' | 'aisle' | 'rack'>('room')
const currentRoomId = ref<string>('')
const coldThreshold = ref(22)
const hotThreshold = ref(30)

const currentRoom = computed(() => rooms.value.find((r) => r.id === currentRoomId.value) ?? null)

function selectRoom(id?: string) {
  if (id) currentRoomId.value = id
}

// 层1 机房 cell
const roomCells = computed<HeatCell[]>(() =>
  rooms.value.map((r) => ({ id: r.id, label: r.name, temp: r.avgTemp }))
)
const topRooms = computed(() =>
  [...rooms.value].sort((a, b) => b.avgTemp - a.avgTemp).slice(0, 5)
)
const topRoomIds = computed(() => topRooms.value.map((r) => r.id))

// 算法生成机柜网格（基于房间温度，靠近热通道一侧更高）
function genRackCells(room: RoomView, rowsR: number, colsR: number): HeatCell[] {
  const base = (room.coldAisle + room.hotAisle) / 2
  const cells: HeatCell[] = []
  for (let r = 0; r < rowsR; r++) {
    // 行越靠下（热通道侧），温度越高
    const heatBias = (r / Math.max(1, rowsR - 1)) * (room.hotAisle - room.coldAisle)
    for (let c = 0; c < colsR; c++) {
      const noise = (Math.sin(r * 1.7 + c * 2.3) + Math.cos(c * 1.1)) * 0.9
      const temp = room.coldAisle + heatBias + noise + (Math.random() - 0.5) * 0.6
      cells.push({ id: `${room.id}-R${r}-C${c}`, label: `${room.name} U${r + 1}`, temp, row: r, col: c, meta: { room: room.id, r, c } })
    }
  }
  return cells
}

// 层2 通道层：上 6 行冷通道、下 6 行热通道
const aisleCells = computed<HeatCell[]>(() => {
  const room = currentRoom.value
  if (!room) return []
  return genRackCells(room, 12, 12)
})
// 层3 机柜层
const rackCells = computed<HeatCell[]>(() => {
  const room = currentRoom.value
  if (!room) return []
  return genRackCells(room, 12, 24)
})

const topRacks = computed(() =>
  [...rackCells.value].sort((a, b) => b.temp - a.temp).slice(0, 5)
)
const topRackIds = computed(() => topRacks.value.map((c) => c.id))

function onRackClick(c: HeatCell) {
  // 机柜详情可在此扩展；当前以高亮为主
  console.log('rack selected', c)
}

async function load() {
  loading.value = true
  try {
    const ov = await getHvacOverview()
    rooms.value = ov.crac.rooms ?? []
    if (!currentRoomId.value && rooms.value[0]) currentRoomId.value = rooms.value[0].id
  } catch (e) {
    console.error('温度云图加载失败', e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.thermal-view { padding: 16px 20px 32px; }
.view-head { display: flex; align-items: center; gap: 14px; }
.view-head h1 { font-size: 20px; margin: 0; color: #e2e8f0; }
.layers { display: flex; gap: 6px; }
.layers button {
  background: #1e293b; color: #cbd5e1; border: 1px solid #334155;
  border-radius: 8px; padding: 6px 12px; cursor: pointer; font-size: 13px;
}
.layers button.on { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }
.refresh {
  margin-left: auto; background: #1e293b; color: #cbd5e1; border: 1px solid #334155;
  border-radius: 8px; padding: 6px 12px; cursor: pointer;
  display: inline-flex; align-items: center; gap: 6px;
}
.ctrl { display: flex; align-items: center; gap: 16px; margin: 16px 0; flex-wrap: wrap; font-size: 13px; color: #94a3b8; }
.ctrl label b { color: #e2e8f0; }
.ctrl input[type='range'] { width: 160px; }
.scale { display: inline-flex; align-items: center; gap: 6px; }
.scale .s { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.s.cold { background: #38bdf8; } .s.ok { background: #22c55e; } .s.hot { background: #ef4444; }
section h2 { color: #cbd5e1; font-size: 16px; margin: 18px 0 10px; }
.board { display: grid; grid-template-columns: 1fr 220px; gap: 16px; align-items: start; }
.side { background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px; }
.side-title { color: #f59e0b; font-size: 13px; margin-bottom: 10px; }
.top-item { display: flex; align-items: center; gap: 8px; padding: 8px; border-radius: 8px; cursor: pointer; }
.top-item:hover { background: #1e293b; }
.rank { background: #7f1d1d; color: #fecaca; border-radius: 4px; padding: 1px 6px; font-size: 11px; }
.name { color: #cbd5e1; font-size: 13px; flex: 1; }
.temp { color: #ef4444; font-weight: 600; }
.aisle-bars { display: flex; gap: 12px; margin-bottom: 12px; }
.aisle-card { background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 14px 18px; min-width: 120px; }
.aisle-card.cold { border-color: #38bdf8; } .aisle-card.hot { border-color: #ef4444; }
.aisle-card .lbl { display: block; color: #64748b; font-size: 12px; }
.aisle-card .val { display: block; color: #e2e8f0; font-size: 24px; font-weight: 700; }
.hint { color: #64748b; font-size: 12px; margin: 0 0 10px; }
</style>
