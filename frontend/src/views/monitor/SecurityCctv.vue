<template>
  <div class="page">
    <div class="page-head">
      <div>
        <h2 class="page-title">视频监控</h2>
        <p class="page-sub">Video Surveillance · 实时预览 / 分区覆盖 / AI 布控 / 事件联动</p>
      </div>
      <div class="head-actions">
        <button class="btn" :class="{ active: layout === 1 }" @click="setLayout(1)">单屏</button>
        <button class="btn" :class="{ active: layout === 4 }" @click="setLayout(4)">4 分屏</button>
        <button class="btn" :class="{ active: layout === 9 }" @click="setLayout(9)">9 分屏</button>
        <button class="btn" :class="{ active: layout === 16 }" @click="setLayout(16)">
          16 分屏
        </button>
        <span class="divider"></span>
        <button class="btn" :class="{ active: patrolOn }" @click="togglePatrol">
          <Play v-if="!patrolOn" :size="14" />
          <Pause v-if="patrolOn" :size="14" />
          {{ patrolOn ? '停止轮巡' : '大屏轮巡' }}
        </button>
        <span v-if="patrolOn" class="patrol-tip">轮巡中 · {{ patrolSec }}s/路</span>
      </div>
    </div>

    <!-- 总览 KPI -->
    <div class="kpi-row">
      <KpiCard
        title="摄像机总数"
        :value="summary.total"
        unit="路"
        :sub="'在线 ' + summary.online"
      />
      <KpiCard
        title="在线率"
        :value="onlineRate"
        unit="%"
        :trend="summary.offline === 0 ? 1 : -1"
        :sub="summary.offline + ' 路离线'"
      />
      <KpiCard
        title="NVR 存储"
        :value="summary.nvr.storeDays"
        unit="天"
        :sub="'要求≥' + summary.nvr.required + '天'"
      />
      <KpiCard
        title="今日事件"
        :value="summary.events.length"
        unit="条"
        :sub="aiEvents + ' 条 AI 联动'"
      />
      <KpiCard title="AI 算法" :value="summary.ai.length" unit="类" :sub="'布控中'" />
    </div>

    <div class="grid-main">
      <!-- 左：实时预览分屏 -->
      <Panel class="preview-card">
        <div class="card-head">
          <span class="card-title">实时预览</span>
          <span class="card-sub">{{ layout }} 分屏 · {{ visibleCams.length }} 路在线窗口</span>
        </div>
        <div class="preview-grid" :class="'g' + layout">
          <div
            v-for="(cam, i) in gridCams"
            :key="i"
            class="pv-cell"
            :class="{ off: cam.status === 'offline', alarm: cam.alarm }"
            @click="focusCam(cam)"
          >
            <template v-if="cam">
              <div class="pv-feedsim">
                <span class="sim-scan"></span>
                <span class="sim-grid"></span>
                <Cctv v-if="cam.status !== 'offline'" :size="28" class="sim-ico" />
                <VideoOff v-else :size="28" class="sim-ico off" />
              </div>
              <div class="pv-bar">
                <span class="pv-name">{{ cam.name }}</span>
                <span class="pv-meta">
                  <span class="dot" :class="cam.status"></span
                  >{{ cam.status === 'offline' ? '离线' : '在线' }}
                  <span class="pv-bit">· {{ cam.bitrate }}</span>
                </span>
              </div>
              <span v-if="cam.alarm" class="pv-alarm">AI 告警</span>
              <span class="pv-idx">{{ i + 1 }}</span>
            </template>
            <span v-else class="pv-empty">—</span>
          </div>
        </div>
        <div v-if="patrolOn" class="patrol-bar">
          <span class="rec-dot"></span> 大屏轮巡进行中：每 {{ patrolSec }}s 切换一组 · 已轮巡
          {{ patrolRound }} 轮
        </div>
      </Panel>

      <!-- 右：摄像头列表 -->
      <Panel class="camlist-card">
        <div class="card-head">
          <span class="card-title">摄像头列表</span>
          <div class="list-filter">
            <select v-model="filterZone" class="sel">
              <option value="">全部分区</option>
              <option v-for="z in summary.zones" :key="z.id" :value="z.id">{{ z.id }}</option>
            </select>
            <select v-model="filterStatus" class="sel">
              <option value="">全部状态</option>
              <option value="online">在线</option>
              <option value="offline">离线</option>
            </select>
          </div>
        </div>
        <div class="camlist">
          <div
            v-for="cam in filteredCams"
            :key="cam.id"
            class="cam-row"
            :class="{
              sel: selectedCam && selectedCam.id === cam.id,
              off: cam.status === 'offline',
            }"
            @click="focusCam(cam)"
          >
            <span class="c-dot" :class="cam.status"></span>
            <span class="c-name">{{ cam.name }}</span>
            <span class="c-zone">{{ cam.zone }}</span>
            <span class="c-ip">{{ cam.ip }}</span>
            <span class="c-bit">{{ cam.bitrate }}</span>
            <span class="c-st" :class="cam.status">{{
              cam.status === 'offline' ? '离线' : '在线'
            }}</span>
          </div>
          <EmptyState v-if="!filteredCams.length" text="无匹配摄像头" />
        </div>
      </Panel>
    </div>

    <div class="grid-sub">
      <!-- 分区覆盖 -->
      <Panel>
        <div class="card-head">
          <span class="card-title">分区覆盖</span
          ><span class="card-sub">分区 / 摄像机数 / 离线</span>
        </div>
        <div class="zone-bars">
          <div v-for="z in summary.zones" :key="z.id" class="zone-row">
            <span class="z-name">{{ z.id }}</span>
            <div class="z-track">
              <div class="z-fill" :style="{ width: pct(z.cams, maxZone) + '%' }"></div>
              <div
                v-if="z.offline"
                class="z-off"
                :style="{ width: pct(z.offline, maxZone) + '%' }"
              ></div>
            </div>
            <span class="z-num"
              >{{ z.cams }}<em v-if="z.offline" class="z-off-n"> · {{ z.offline }} 离线</em></span
            >
          </div>
        </div>
      </Panel>

      <!-- AI 布控 -->
      <Panel>
        <div class="card-head">
          <span class="card-title">AI 智能布控</span><span class="card-sub">算法 / 联动</span>
        </div>
        <ul class="ai-list">
          <li v-for="a in summary.ai" :key="a"><Cpu :size="14" />{{ a }}</li>
        </ul>
        <div class="nvr-box">
          <span class="nvr-t">NVR 集群</span>
          <span>设备 {{ summary.nvr.ok }}/{{ summary.nvr.total }} 正常</span>
          <span>存储 {{ summary.nvr.storeDays }} 天 / 要求 ≥ {{ summary.nvr.required }} 天</span>
        </div>
      </Panel>

      <!-- 事件联动 -->
      <Panel>
        <div class="card-head">
          <span class="card-title">视频事件联动</span
          ><span class="card-sub">{{ summary.events.length }} 条</span>
        </div>
        <div class="evt-list">
          <div v-for="(e, i) in summary.events" :key="i" class="evt-row">
            <AlarmBadge :level="e.lv" />
            <span class="e-ts">{{ e.ts }}</span>
            <span class="e-zone">{{ e.zone }}</span>
            <span class="e-desc">{{ e.desc }}</span>
          </div>
          <EmptyState v-if="!summary.events.length" text="暂无事件" />
        </div>
      </Panel>
    </div>

    <!-- 知识库 -->
    <Panel class="know">
      <div class="card-head"><span class="card-title">监控设计阈值 · 架构 · 故障锁定</span></div>
      <SecurityKnowledge
        :knowledge="summary.knowledge"
        logic-title="录像 / 轮巡逻辑"
        reset-header="人工复位"
      />
    </Panel>

    <p v-if="usingMock" class="mock-flag">⚠ 当前为本地模拟数据（后端未返回或未运行）</p>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Camera, Activity, Database, Bell, Cpu, Cctv, VideoOff, Play, Pause } from 'lucide-vue-next'
import KpiCard from '@/components/monitor/KpiCard.vue'
import Panel from '@/components/common/Panel.vue'
import SecurityKnowledge from '@/components/SecurityKnowledge.vue'
import AlarmBadge from '@/components/monitor/AlarmBadge.vue'
import EmptyState from '@/components/monitor/EmptyState.vue'
import { getSecurityCctvDetailed } from '@/api/security'
import type { CctvSummary, CctvZoneView } from '@/api/security'

interface CamView {
  id: string
  name: string
  zone: string
  ip: string
  status: 'online' | 'offline'
  bitrate: string
  nvr: string
  alarm: boolean
}

const summary = ref<CctvSummary>({
  total: 0,
  online: 0,
  offline: 0,
  nvr: { total: 0, ok: 0, storeDays: 0, required: 0 },
  zones: [],
  ai: [],
  events: [],
  knowledge: { thresholds: [] },
})
const usingMock = ref(false)
const loading = ref(false)

// 派生的摄像头明细（后端 CctvSummary 仅聚合到 zone，无明细列表）
const cams = ref<CamView[]>([])

function deriveCams(zones: CctvZoneView[]): CamView[] {
  const list: CamView[] = []
  const nvrPool = ['NVR-01', 'NVR-02', 'NVR-03', 'NVR-04', 'NVR-05', 'NVR-06']
  zones.forEach((z, zi) => {
    const prefix = zonePrefix(z.id)
    for (let i = 1; i <= z.cams; i++) {
      const offline = i <= z.offline
      list.push({
        id: `${prefix}-${String(i).padStart(2, '0')}`,
        name: `CAM-${prefix}-${String(i).padStart(2, '0')}`,
        zone: z.id,
        ip: `10.${20 + zi}.${Math.floor(i / 30)}.${10 + (i % 240)}`,
        status: offline ? 'offline' : 'online',
        bitrate: offline ? '—' : `${[2, 3, 4, 6, 8][i % 5]} Mbps`,
        nvr: nvrPool[zi % nvrPool.length],
        alarm: false,
      })
    }
  })
  // 标记 AI 告警摄像头（用事件中的摄像机名关联）
  summary.value.events.forEach((e) => {
    const m = e.desc.match(/CAM-[\w-]+/)
    if (m) {
      const found = list.find((c) => c.name === m[0] && c.status === 'online')
      if (found) found.alarm = true
    }
  })
  return list
}

function zonePrefix(zone: string): string {
  const map: Record<string, string> = {
    园区周界: 'P',
    '大堂/门厅': 'L',
    '走廊/通道': 'C',
    机房包间: 'R',
    动力机房: 'D',
    '柴发/油罐区': 'F',
  }
  if (map[zone]) return map[zone]
  return zone
    .replace(/[^\w一-龥]/g, '')
    .slice(0, 2)
    .toUpperCase()
}

const onlineRate = computed(() =>
  summary.value.total ? +((summary.value.online / summary.value.total) * 100).toFixed(1) : 0,
)
const aiEvents = computed(
  () => summary.value.events.filter((e) => /AI|联动|复核/.test(e.desc)).length,
)
const maxZone = computed(() => Math.max(1, ...summary.value.zones.map((z) => z.cams)))
function pct(v: number, max: number) {
  return Math.min(100, (v / max) * 100)
}

// 摄像头列表过滤
const filterZone = ref('')
const filterStatus = ref('')
const selectedCam = ref<CamView | null>(null)
const filteredCams = computed(() =>
  cams.value.filter(
    (c) =>
      (!filterZone.value || c.zone === filterZone.value) &&
      (!filterStatus.value || c.status === filterStatus.value),
  ),
)

// 分屏预览
const layout = ref(4)
const startIdx = ref(0)
const gridCams = computed<CamView[]>(() => {
  const n = layout.value
  const online = cams.value.filter((c) => c.status === 'online')
  if (online.length === 0) return []
  const arr: CamView[] = []
  for (let i = 0; i < n; i++) arr.push(online[(startIdx.value + i) % online.length])
  return arr
})
const visibleCams = computed(() => gridCams.value)
function setLayout(n: number) {
  layout.value = n
  startIdx.value = 0
}
function focusCam(cam: CamView | null) {
  if (!cam) return
  selectedCam.value = cam
  const idx = cams.value.filter((c) => c.status === 'online').findIndex((c) => c.id === cam.id)
  if (idx >= 0) startIdx.value = Math.floor(idx / layout.value) * layout.value
}

// 大屏轮巡
const patrolOn = ref(false)
const patrolSec = ref(5)
const patrolRound = ref(0)
let patrolTimer: ReturnType<typeof setInterval> | null = null
function togglePatrol() {
  patrolOn.value = !patrolOn.value
  if (patrolOn.value) {
    patrolRound.value = 0
    patrolTimer = setInterval(() => {
      const online = cams.value.filter((c) => c.status === 'online')
      if (!online.length) return
      startIdx.value = (startIdx.value + layout.value) % online.length
      patrolRound.value++
    }, patrolSec.value * 1000)
  } else if (patrolTimer) {
    clearInterval(patrolTimer)
    patrolTimer = null
  }
}
watch(layout, () => {
  startIdx.value = 0
})

async function load() {
  loading.value = true
  try {
    const data = await getSecurityCctvDetailed()
    if (data && data.total) {
      summary.value = data
      usingMock.value = false
    } else {
      throw new Error('empty')
    }
  } catch {
    summary.value = mockSummary()
    usingMock.value = true
  } finally {
    cams.value = deriveCams(summary.value.zones)
    loading.value = false
  }
}

function mockSummary(): CctvSummary {
  return {
    total: 486,
    online: 482,
    offline: 4,
    nvr: { total: 12, ok: 12, storeDays: 92, required: 90 },
    zones: [
      { id: '园区周界', cams: 64, offline: 0 },
      { id: '大堂/门厅', cams: 22, offline: 0 },
      { id: '走廊/通道', cams: 118, offline: 1 },
      { id: '机房包间', cams: 192, offline: 2 },
      { id: '动力机房', cams: 58, offline: 1 },
      { id: '柴发/油罐区', cams: 32, offline: 0 },
    ],
    ai: ['周界入侵检测', '人员徘徊识别', '未戴安全帽识别', '离岗检测'],
    events: [
      { ts: '13:52', zone: '园区周界-东', desc: 'AI 周界检测: 小动物触发, 已自动过滤', lv: 'info' },
      { ts: '11:20', zone: '走廊 C2', desc: '摄像机 CAM-C2-07 视频丢失', lv: 'warn' },
      { ts: '09:47', zone: '机房 R03', desc: '人员徘徊识别: 已联动复核, 为巡检人员', lv: 'info' },
    ],
    knowledge: {
      thresholds: [
        { k: '存储时长', v: '≥90 天', note: '金融/等保三级要求' },
        { k: '在线率', v: '≥99.5%', note: '离线需 4h 内处置' },
        { k: '主码流', v: '4~8 Mbps', note: '1080P/4K' },
        { k: '抽帧存储', v: '1~4 fps', note: '非重点区节能' },
        { k: '录像完整性', v: '≥99.9%', note: '缺失需告警' },
      ],
      arch: {
        components: ['IPC 网络摄像机', 'NVR/云存储', '视频综合平台', 'AI 算力服务器', '解码上墙'],
        design: '分层星型：IPC→接入交换机→核心→NVR/平台，重点区双网卡聚合。',
        redundancy: 'NVR N+1 热备，核心交换机双机，存储 RAID6 + 异地备份。',
      },
      logic: [
        {
          title: '实时预览',
          steps: [
            { step: 1, text: '选择摄像机 → 平台取流(GB28181/RTSP)', ok: true },
            { step: 2, text: '解码上墙 / WebRTC 低延迟预览', ok: true },
          ],
        },
        {
          title: '大屏轮巡',
          steps: [
            { step: 1, text: '编辑轮巡组(≤16 路)', ok: true },
            { step: 2, text: '设定驻留时间(默认 5s)自动切换', ok: true },
          ],
        },
        {
          title: 'AI 联动',
          steps: [
            { step: 1, text: '算法识别 → 打标 + 截图', ok: true },
            { step: 2, text: '联动预置位 / 弹窗 / 推送 IOC', ok: true },
          ],
        },
      ],
      faults: [
        {
          no: 1,
          fault: '视频丢失',
          lock: '标记离线 + 告警',
          action: '查供电/网络/光纤',
          manualReset: false,
        },
        {
          no: 2,
          fault: '画面卡顿',
          lock: '降码流/切换线路',
          action: '查带宽/交换机',
          manualReset: false,
        },
        {
          no: 3,
          fault: '时间不同步',
          lock: '强制 NTP 校时',
          action: '校时服务器',
          manualReset: false,
        },
        {
          no: 4,
          fault: '存储写满',
          lock: '覆盖最旧 + 告警',
          action: '扩容/清理',
          manualReset: true,
        },
        {
          no: 5,
          fault: 'AI 误报频发',
          lock: '调阈值/模型',
          action: '复核样本',
          manualReset: false,
        },
      ],
    },
  }
}

const REFRESH_MS = 30000
let timer: ReturnType<typeof setInterval> | null = null
onMounted(() => {
  load()
  timer = setInterval(load, REFRESH_MS)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
  if (patrolTimer) clearInterval(patrolTimer)
})

void Camera
void Activity
void Database
void Bell
</script>

<style scoped>
.page {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.page-title {
  font-size: 20px;
  margin: 0;
}
.page-sub {
  margin: 2px 0 0;
  color: var(--text-2);
  font-size: 12px;
}
.head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: 1px solid var(--border);
  background: var(--bg-1);
  color: var(--text-1);
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn.active {
  background: var(--brand);
  color: #fff;
  border-color: var(--brand);
}
.divider {
  width: 1px;
  height: 20px;
  background: var(--border);
  margin: 0 4px;
}
.patrol-tip {
  font-size: 12px;
  color: var(--brand);
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.grid-main {
  display: grid;
  grid-template-columns: 2.2fr 1fr;
  gap: 14px;
}
.grid-sub {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
/* 预览分屏 */
.preview-card {
  min-height: 420px;
}
.preview-grid {
  display: grid;
  gap: 6px;
}
.preview-grid.g1 {
  grid-template-columns: 1fr;
}
.preview-grid.g4 {
  grid-template-columns: 1fr 1fr;
}
.preview-grid.g9 {
  grid-template-columns: repeat(3, 1fr);
}
.preview-grid.g16 {
  grid-template-columns: repeat(4, 1fr);
}
.pv-cell {
  position: relative;
  aspect-ratio: 16/9;
  background: #0a0e14;
  border: 1px solid #1c2530;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: flex-end;
}
.pv-cell.off {
  background: #15110f;
  border-color: #3a2418;
}
.pv-cell.alarm {
  border-color: #b4451f;
  box-shadow: 0 0 0 1px #b4451f inset;
}
.pv-feedsim {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sim-ico {
  color: #2f6f4f;
  opacity: 0.8;
}
.sim-ico.off {
  color: #6b3a2a;
}
.sim-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(#15202c 1px, transparent 1px),
    linear-gradient(90deg, #15202c 1px, transparent 1px);
  background-size: 28px 28px;
  opacity: 0.5;
}
.sim-scan {
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #2f6f4f, transparent);
  animation: scan 3.2s linear infinite;
}
@keyframes scan {
  0% {
    top: 0;
  }
  100% {
    top: 100%;
  }
}
.pv-bar {
  position: relative;
  z-index: 2;
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 6px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.7));
  font-size: 11px;
  color: #cfe;
}
.pv-name {
  font-weight: 600;
}
.pv-meta {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: #9fb;
}
.pv-bit {
  color: #7a8;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  display: inline-block;
}
.dot.online {
  background: #2fae6b;
}
.dot.offline {
  background: #d06a3a;
}
.pv-alarm {
  position: absolute;
  top: 6px;
  left: 6px;
  z-index: 3;
  background: #b4451f;
  color: #fff;
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
}
.pv-idx {
  position: absolute;
  top: 6px;
  right: 6px;
  z-index: 3;
  color: #456;
  font-size: 10px;
}
.pv-empty {
  margin: auto;
  color: #345;
}
.patrol-bar {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-2);
}
.rec-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #d23;
  animation: blink 1s steps(2) infinite;
}
@keyframes blink {
  50% {
    opacity: 0.2;
  }
}

/* 摄像头列表 */
.camlist-card {
  display: flex;
  flex-direction: column;
}
.list-filter {
  display: flex;
  gap: 6px;
}
.sel {
  background: var(--bg-2);
  border: 1px solid var(--border);
  color: var(--text-1);
  border-radius: 5px;
  padding: 3px 6px;
  font-size: 12px;
}
.camlist {
  overflow-y: auto;
  max-height: 420px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.cam-row {
  display: grid;
  grid-template-columns: 14px 1fr 70px 96px 56px 40px;
  align-items: center;
  gap: 4px;
  padding: 5px 6px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 12px;
}
.cam-row:hover {
  background: var(--bg-2);
}
.cam-row.sel {
  background: var(--brand-weak);
  outline: 1px solid var(--brand);
}
.cam-row.off {
  opacity: 0.6;
}
.c-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.c-dot.online {
  background: #2fae6b;
}
.c-dot.offline {
  background: #d06a3a;
}
.c-name {
  font-weight: 600;
}
.c-zone,
.c-ip,
.c-bit {
  color: var(--text-2);
}
.c-st {
  font-size: 11px;
}
.c-st.online {
  color: #2fae6b;
}
.c-st.offline {
  color: #d06a3a;
}

/* 分区覆盖 */
.zone-bars {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.zone-row {
  display: grid;
  grid-template-columns: 90px 1fr 80px;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}
.z-name {
  color: var(--text-2);
}
.z-track {
  position: relative;
  height: 14px;
  background: var(--bg-2);
  border-radius: 7px;
  overflow: hidden;
}
.z-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: linear-gradient(90deg, #2f6f9f, #3f8fbf);
  border-radius: 7px;
}
.z-off {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: #d06a3a;
  opacity: 0.9;
}
.z-num {
  text-align: right;
}
.z-off-n {
  color: #d06a3a;
  font-style: normal;
}

/* AI */
.ai-list {
  list-style: none;
  padding: 0;
  margin: 0 0 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 13px;
}
.ai-list li {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-1);
}
.nvr-box {
  display: flex;
  flex-direction: column;
  gap: 3px;
  font-size: 12px;
  color: var(--text-2);
  border-top: 1px dashed var(--border);
  padding-top: 8px;
}
.nvr-t {
  color: var(--text-1);
  font-weight: 600;
}

/* 事件 */
.evt-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 220px;
  overflow-y: auto;
}
.evt-row {
  display: grid;
  grid-template-columns: auto 52px 80px 1fr;
  gap: 6px;
  align-items: center;
  font-size: 12px;
}
.e-ts {
  color: var(--text-2);
}
.e-zone {
  color: var(--brand);
}
.e-desc {
  color: var(--text-1);
}

.mock-flag {
  font-size: 12px;
  color: #d06a3a;
  margin: 0;
}
@media (max-width: 1100px) {
  .kpi-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .grid-main,
  .grid-sub {
    grid-template-columns: 1fr;
  }
}
</style>
