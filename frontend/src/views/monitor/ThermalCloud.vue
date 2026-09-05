<template>
  <div class="thermal-view">
    <div class="view-head">
      <h1>{{ tl('温度云图') }}</h1>
      <div class="layers">
        <button :class="{ on: layer === 'room' }" @click="layer = 'room'">
          {{ tl('机房层') }}
        </button>
        <button :class="{ on: layer === 'aisle' }" @click="openAisle">
          {{ tl('通道层') }}
        </button>
        <button :class="{ on: layer === 'rack' }" @click="openRack">
          {{ tl('机柜层') }}
        </button>
      </div>
      <button class="refresh" @click="page.reload" :disabled="busy">
        <RefreshCw :size="14" :class="{ 'is-spin': busy }" />
        {{ busy ? tl('刷新中') : tl('刷新') }}
      </button>
      <button class="ge-edit" @click="editOpen = true">
        {{ tl('编辑') }}{{ hasGraphicEdits ? ' ●' : '' }}
      </button>
    </div>

    <!-- 内容区: 加载 / 失败可重试 / 空态 -->
    <AsyncSection
      :page="page"
      skeleton-variant="skeleton"
      :skeleton-rows="6"
      min-height="260px"
      empty-title="暂无机房温度数据"
      empty-desc="后端未返回任何包间，请确认暖通采集已接入"
    >
      <template #empty-actions>
        <button class="link-btn" @click="page.reload">{{ tl('重新加载') }}</button>
      </template>

      <!-- 区间可调 -->
      <div class="ctrl">
        <label
          >{{ tl('低温区间') }} <b>{{ coldThreshold }}℃</b></label
        >
        <input type="range" min="14" max="28" step="0.5" v-model.number="coldThreshold" />
        <label
          >{{ tl('高温区间') }} <b>{{ hotThreshold }}℃</b></label
        >
        <input type="range" min="26" max="42" step="0.5" v-model.number="hotThreshold" />
        <span class="scale">
          <i class="s cold" /> {{ tl('偏低') }} <i class="s ok" /> {{ tl('正常') }}
          <i class="s hot" /> {{ tl('偏高/热点') }}
        </span>
        <DataBadge
          v-if="layer !== 'room'"
          tone="sample"
          tip="通道层 / 机柜层的温度为前端基于包间冷热通道温度合成的示例分布（后端暂无逐机柜测点），仅用于观察温场形态，不可作为热点判定依据"
        />
      </div>

      <!-- 层1 机房层 -->
      <section v-if="layer === 'room'">
        <h2>{{ tl('机房温度分布') }}（{{ tl('点选机房下钻') }}）</h2>
        <div class="board">
          <TemperatureHeatmap
            :cells="roomCellsView"
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
            <span class="val"
              >{{ (currentRoom.hotAisle - currentRoom.coldAisle).toFixed(1) }}℃</span
            >
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
    </AsyncSection>

    <!-- 统一图形编辑入口: 机房格改名/删除/新增 + 冷热阈值参数配置 (覆盖层) -->
    <GraphicEditDrawer
      v-model="editOpen"
      :editor="graphicEditor"
      :title="tl('温度云图')"
      :defaults="graphicDefaults"
      :param-defaults="paramDefaults"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import TemperatureHeatmap, { HeatCell } from '@/components/hvac/TemperatureHeatmap.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import DataBadge from '@/components/common/DataBadge.vue'
import GraphicEditDrawer from '@/components/common/GraphicEditDrawer.vue'
import { useAsyncPage } from '@/composables/useAsyncPage'
import { useGraphicEditor, type NodeAdapter } from '@/composables/useGraphicEditor'
import { getHvacOverview } from '@/api/hvac'
import type { RoomView } from '@/api/hvac'
import type { GraphicNode } from '@/types/graphic'

const { t: tl } = useI18n()

/** 数据源：暖通总览里的包间列表。失败时走 AsyncSection 的错误态，不再只 console.error */
const page = useAsyncPage<RoomView[]>(
  async () => {
    const ov = await getHvacOverview()
    return ov.crac.rooms ?? []
  },
  {
    isEmpty: (list) => !list.length,
    onSuccess: (list) => {
      if (!currentRoomId.value && list[0]) currentRoomId.value = list[0].id
    },
  },
)
const { busy } = page
const rooms = computed(() => page.data.value ?? [])
const layer = ref<'room' | 'aisle' | 'rack'>('room')
const currentRoomId = ref<string>('')

const currentRoom = computed(() => rooms.value.find((r) => r.id === currentRoomId.value) ?? null)

function selectRoom(id?: string) {
  if (id) currentRoomId.value = id
}

function openAisle() {
  selectRoom(rooms.value[0]?.id)
  layer.value = 'aisle'
}

function openRack() {
  selectRoom(rooms.value[0]?.id)
  layer.value = 'rack'
}

// 层1 机房 cell
const roomCells = computed<HeatCell[]>(() =>
  rooms.value.map((r) => ({ id: r.id, label: r.name, temp: r.avgTemp })),
)
const topRooms = computed(() => [...rooms.value].sort((a, b) => b.avgTemp - a.avgTemp).slice(0, 5))
const topRoomIds = computed(() => topRooms.value.map((r) => r.id))

// 算法生成机柜网格（基于房间温度，靠近热通道一侧更高）
function genRackCells(room: RoomView, rowsR: number, colsR: number): HeatCell[] {
  const cells: HeatCell[] = []
  for (let r = 0; r < rowsR; r++) {
    // 行越靠下（热通道侧），温度越高
    const heatBias = (r / Math.max(1, rowsR - 1)) * (room.hotAisle - room.coldAisle)
    for (let c = 0; c < colsR; c++) {
      const noise = (Math.sin(r * 1.7 + c * 2.3) + Math.cos(c * 1.1)) * 0.9
      const temp = room.coldAisle + heatBias + noise + (Math.random() - 0.5) * 0.6
      cells.push({
        id: `${room.id}-R${r}-C${c}`,
        label: `${room.name} U${r + 1}`,
        temp,
        row: r,
        col: c,
        meta: { room: room.id, r, c },
      })
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

const topRacks = computed(() => [...rackCells.value].sort((a, b) => b.temp - a.temp).slice(0, 5))
const topRackIds = computed(() => topRacks.value.map((c) => c.id))

function onRackClick(_c: HeatCell) {
  // 机柜详情待后端提供逐机柜测点后接入；当前云图以高亮为主，不做无效 console
}

/* ───────── 统一图形编辑入口 (温度云图) ─────────
 * 支持两类编辑: ① 机房层网格格子的改名/删除/新增 (覆盖层, 接口数据仍实时刷新)
 *              ② 冷/热阈值参数配置 (保存在场景 params, 抽屉里可改) */
const graphicEditor = useGraphicEditor('thermal-cloud-grid', { title: '温度云图' })
const editOpen = ref(false)
const hasGraphicEdits = computed(() => graphicEditor.hasOverrides.value)

/** HeatCell ↔ GraphicNode 双向映射 (未改字段保留接口实时值) */
const cellAdapter: NodeAdapter<HeatCell> = {
  toNode: (c) => ({ id: c.id, label: c.label, type: '机房', status: c.temp.toFixed(1) + '℃' }),
  fromNode: (g, base) => {
    if (base) return { ...base, label: g.label || base.label }
    // 用户新增格子: 温度取 params.temp (缺省 24), 否则热力图无法着色
    return {
      id: g.id,
      label: g.label || g.id,
      temp: Number(g.params?.temp ?? 24) || 24,
      row: 0,
      col: 0,
      meta: {},
    }
  },
}
const roomCellsView = computed(() => graphicEditor.apply(roomCells.value, cellAdapter))
const graphicDefaults = (): GraphicNode[] => roomCells.value.map(cellAdapter.toNode)

/** 冷/热阈值持久化: 初始取覆盖层参数, 抽屉保存后回写 */
const coldThreshold = ref(Number(graphicEditor.getParam('coldThreshold', '22')) || 22)
const hotThreshold = ref(Number(graphicEditor.getParam('hotThreshold', '30')) || 30)
const paramDefaults = (): Record<string, string> => ({
  coldThreshold: '22',
  hotThreshold: '30',
})
watch(
  () => graphicEditor.scene.value.params,
  (p) => {
    const c = Number(p?.coldThreshold)
    const h = Number(p?.hotThreshold)
    if (c >= 14 && c <= 28) coldThreshold.value = c
    if (h >= 26 && h <= 42) hotThreshold.value = h
  },
  { deep: true },
)
</script>

<style scoped>
.thermal-view {
  padding: 16px 20px 32px;
}
.view-head {
  display: flex;
  align-items: center;
  gap: 14px;
}
.view-head h1 {
  font-size: 20px;
  margin: 0;
  color: #e2e8f0;
}
.layers {
  display: flex;
  gap: 6px;
}
.layers button {
  background: #1e293b;
  color: #cbd5e1;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
}
.layers button.on {
  background: #0ea5e9;
  color: #fff;
  border-color: #0ea5e9;
}
.refresh {
  margin-left: auto;
  background: #1e293b;
  color: #cbd5e1;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
/* 统一图形编辑入口按钮 */
.ge-edit {
  background: #1e293b;
  color: #22d3ee;
  border: 1px solid #22d3ee;
  border-radius: 8px;
  padding: 6px 12px;
  cursor: pointer;
  font-size: 13px;
}
.ge-edit:hover {
  background: rgba(34, 211, 238, 0.14);
}
.ctrl {
  display: flex;
  align-items: center;
  gap: 16px;
  margin: 16px 0;
  flex-wrap: wrap;
  font-size: 13px;
  color: #94a3b8;
}
.ctrl label b {
  color: #e2e8f0;
}
.ctrl input[type='range'] {
  width: 160px;
}
.scale {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.scale .s {
  width: 14px;
  height: 14px;
  border-radius: 3px;
  display: inline-block;
}
.s.cold {
  background: #38bdf8;
}
.s.ok {
  background: #22c55e;
}
.s.hot {
  background: #ef4444;
}
section h2 {
  color: #cbd5e1;
  font-size: 16px;
  margin: 18px 0 10px;
}
.board {
  display: grid;
  grid-template-columns: 1fr 220px;
  gap: 16px;
  align-items: start;
}
.side {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 14px;
}
.side-title {
  color: #f59e0b;
  font-size: 13px;
  margin-bottom: 10px;
}
.top-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 8px;
  cursor: pointer;
}
.top-item:hover {
  background: #1e293b;
}
.rank {
  background: #7f1d1d;
  color: #fecaca;
  border-radius: 4px;
  padding: 1px 6px;
  font-size: 11px;
}
.name {
  color: #cbd5e1;
  font-size: 13px;
  flex: 1;
}
.temp {
  color: #ef4444;
  font-weight: 600;
}
.aisle-bars {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}
.aisle-card {
  background: #0f172a;
  border: 1px solid #1e293b;
  border-radius: 12px;
  padding: 14px 18px;
  min-width: 120px;
}
.aisle-card.cold {
  border-color: #38bdf8;
}
.aisle-card.hot {
  border-color: #ef4444;
}
.aisle-card .lbl {
  display: block;
  color: #64748b;
  font-size: 12px;
}
.aisle-card .val {
  display: block;
  color: #e2e8f0;
  font-size: 24px;
  font-weight: 700;
}
.hint {
  color: #64748b;
  font-size: 12px;
  margin: 0 0 10px;
}

/* ===== 本轮新增 ===== */
.is-spin {
  animation: tc-rotate 0.8s linear infinite;
}
@keyframes tc-rotate {
  to {
    transform: rotate(360deg);
  }
}
.link-btn {
  background: none;
  border: none;
  padding: 0;
  font-size: 12px;
  color: #22e3ff;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

/* ===== 响应式 ===== */
@media (max-width: 1100px) {
  /* 热力图 + TOP5 侧栏改为上下堆叠，避免热力图被压成窄条 */
  .board {
    grid-template-columns: 1fr;
  }
  .side {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 4px;
  }
  .side-title {
    grid-column: 1 / -1;
  }
}
@media (max-width: 860px) {
  .view-head {
    flex-wrap: wrap;
    gap: 10px;
  }
  .refresh {
    margin-left: 0;
  }
  .ctrl {
    gap: 10px;
  }
  .ctrl input[type='range'] {
    width: 100%;
    min-width: 120px;
  }
  .ctrl label {
    flex: 1 1 100%;
  }
  .aisle-bars {
    flex-wrap: wrap;
  }
  .aisle-card {
    flex: 1 1 140px;
    min-width: 0;
  }
}
@media (max-width: 560px) {
  .thermal-view {
    padding: 12px 12px 24px;
  }
  .layers {
    width: 100%;
  }
  .layers button {
    flex: 1;
  }
  .side {
    grid-template-columns: 1fr;
  }
}
</style>
