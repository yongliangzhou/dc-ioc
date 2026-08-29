<template>
  <div>
    <MockDataBanner v-if="usingMock" level="full" />
    <div class="view-head">
      <h1>{{ tl('智能运营') }} {{ tl('·') }} {{ tl('告警历史与持久化') }}</h1>
      <span class="sub"
        >{{ tl('时间窗查询') }} {{ tl('·') }} {{ tl('确认') }} / {{ tl('闭环') }} {{ tl('·') }}
        {{ tl('收敛与处置统计') }}</span
      >
    </div>

    <!-- 统计 -->
    <div class="grid cols-5" v-if="data">
      <KpiCard :title="'24h ' + tl('总告警')" :value="data.stats.total24h" unit="条" />
      <KpiCard
        :title="'24h ' + tl('活跃')"
        :value="data.stats.active24h"
        unit="条"
        status="danger"
      />
      <KpiCard :title="'24h ' + tl('已闭环')" :value="data.stats.resolved24h" unit="条" />
      <KpiCard title="MTTA" :value="data.stats.mttaMin" unit="min" />
      <KpiCard title="MTTR" :value="data.stats.mttrMin" unit="min" />
    </div>

    <!-- 筛选 -->
    <Panel class="toolbar">
      <select v-model="fSys" class="ipt" style="width: 160px" @change="onFilter">
        <option value="">{{ tl('全部系统') }}</option>
        <option v-for="s in systemOptions" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="fLv" class="ipt" style="width: 110px" @change="onFilter">
        <option value="">{{ tl('全部级别') }}</option>
        <option value="crit">crit</option>
        <option value="warn">warn</option>
        <option value="info">info</option>
      </select>
      <select v-model="fState" class="ipt" style="width: 120px" @change="onFilter">
        <option value="">{{ tl('全部状态') }}</option>
        <option value="active">{{ tl('活跃') }}</option>
        <option value="acknowledged">{{ tl('已确认') }}</option>
        <option value="resolved">{{ tl('已闭环') }}</option>
        <option value="suppressed">{{ tl('已抑制') }}</option>
      </select>
      <input
        v-model.trim="kw"
        class="ipt"
        :placeholder="tl('搜索规则 / 描述')"
        style="width: 220px"
        @keyup.enter="onFilter"
      />
      <button class="btn-sm primary" @click="onFilter">{{ tl('查询') }}</button>
      <span class="muted" style="margin-left: auto; font-size: 11px"
        >{{ tl('共') }} {{ data?.total ?? 0 }} {{ tl('条') }} {{ tl('·') }} {{ tl('当前页') }}
        {{ data?.items.length ?? 0 }} {{ tl('条') }}</span
      >
    </Panel>

    <!-- 列表 -->
    <Panel class="scroll-x">
      <table>
        <thead>
          <tr>
            <th scope="col">{{ tl('触发时间') }}</th>
            <th scope="col">{{ tl('级别') }}</th>
            <th scope="col">{{ tl('系统') }}</th>
            <th scope="col">{{ tl('规则') }} / {{ tl('描述') }}</th>
            <th scope="col">{{ tl('实测') }} / {{ tl('阈值') }}</th>
            <th scope="col">{{ tl('状态') }}</th>
            <th style="min-width: 150px">{{ tl('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="e in data?.items"
            :key="e.id"
            :class="{ 'row-crit': e.level === 'crit' && e.status !== 'resolved' }"
          >
            <td class="mono">{{ fmtDateTime(e.triggeredAt) }}</td>
            <td>
              <span class="tag" :class="e.level === 'crit' ? 'r' : e.level === 'warn' ? 'a' : 'g'">{{
                e.level
              }}</span>
            </td>
            <td>{{ e.system }}</td>
            <td>
              <div style="font-weight: 600">{{ e.ruleName }}</div>
              <div class="muted" style="font-size: 11px">{{ e.message }}</div>
            </td>
            <td class="mono">
              {{ e.value }}{{ e.unit || '' }} / {{ e.threshold }}{{ e.unit || '' }}
            </td>
            <td>
              <span class="tag" :class="stateTag(e.status)">{{ stateText(e.status) }}</span>
            </td>
            <td>
              <button class="btn-sm" v-if="e.status === 'active'" @click="ack(e)">
                {{ tl('确认') }}
              </button>
              <button
                class="btn-sm primary"
                v-if="e.status === 'active' || e.status === 'acknowledged'"
                style="margin-left: 4px"
                @click="resolve(e)"
              >
                {{ tl('闭环') }}
              </button>
              <span class="muted" v-if="e.status === 'resolved'" style="font-size: 11px"
                >{{ e.resolvedBy }}{{ e.autoResolved ? '·自动' : '' }}</span
              >
              <span class="muted" v-if="e.status === 'suppressed'" style="font-size: 11px">{{
                tl('已抑制')
              }}</span>
            </td>
          </tr>
          <tr v-if="!data?.items.length">
            <td colspan="7" class="muted" style="text-align: center; padding: 18px">
              {{ tl('无匹配告警') }}
            </td>
          </tr>
        </tbody>
      </table>
      <Pagination
        v-if="data"
        :total="data.total"
        :page="page"
        :size="size"
        @change="onPage"
        @size-change="onSize"
      />
    </Panel>

    <!-- 告警触达通道 (由多通道告警模块整合) -->
    <div class="channels">
      <div class="view-sub">
        <h2>{{ tl('告警触达通道') }}</h2>
        <span class="sub">{{ tl('统一管理多通道触达策略与发送记录') }}</span>
      </div>

      <div class="ch-grid">
        <div
          v-for="c in channels"
          :key="c.id"
          class="ch-card"
          :class="{ disabled: !c.enabled }"
        >
          <div class="ch-top">
            <span class="ch-icon">{{ c.icon }}</span>
            <span class="ch-name">{{ c.name }}</span>
            <span class="ch-status" :class="c.enabled ? 'on' : 'off'">{{
              c.enabled ? tl('启用') : tl('停用')
            }}</span>
          </div>
          <div class="ch-meta">
            <div><span class="muted">{{ tl('触发级别') }}</span> {{ c.levels.join(' / ') }}</div>
            <div><span class="muted">{{ tl('触达对象') }}</span> {{ c.target }}</div>
          </div>
          <div class="ch-bar">
            <span class="muted sm">{{ tl('近 24h 触达') }}</span>
            <span class="ch-count">{{ c.sent }}</span>
          </div>
        </div>
      </div>

      <Panel class="toolbar" style="margin-top: 16px">
        <strong style="font-size: 13px">{{ tl('触达规则') }}</strong>
        <table style="margin-top: 10px">
          <thead>
            <tr>
              <th>{{ tl('规则名称') }}</th>
              <th>{{ tl('通道') }}</th>
              <th>{{ tl('适用级别') }}</th>
              <th>{{ tl('静默') }}</th>
              <th>{{ tl('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in channelRules" :key="r.id">
              <td>{{ r.name }}</td>
              <td>{{ r.channels.join(' / ') }}</td>
              <td>{{ r.levels.join(' / ') }}</td>
              <td>{{ r.silence }}</td>
              <td>
                <span class="tag" :class="r.enabled ? 'g' : 'n'">{{
                  r.enabled ? tl('生效') : tl('停用')
                }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </Panel>

      <Panel class="scroll-x" style="margin-top: 16px">
        <strong style="font-size: 13px">{{ tl('触达记录') }}</strong>
        <table style="margin-top: 10px">
          <thead>
            <tr>
              <th>{{ tl('时间') }}</th>
              <th>{{ tl('通道') }}</th>
              <th>{{ tl('级别') }}</th>
              <th>{{ tl('接收人') }}</th>
              <th>{{ tl('内容摘要') }}</th>
              <th>{{ tl('状态') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="l in channelLogs" :key="l.id">
              <td class="mono">{{ fmtDateTime(l.at) }}</td>
              <td>{{ l.channel }}</td>
              <td><span class="tag" :class="l.level === 'crit' ? 'r' : l.level === 'warn' ? 'a' : 'g'">{{ l.level }}</span></td>
              <td>{{ l.receiver }}</td>
              <td class="muted">{{ l.summary }}</td>
              <td>
                <span class="tag" :class="l.ok ? 'g' : 'r'">{{ l.ok ? tl('成功') : tl('失败') }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </Panel>
    </div>

    <div class="footer-note">
      {{ tl('智能运营·告警历史') }} {{ tl('—') }} {{ tl('接入后端') }} /api/alarm-history ({{
        tl('确认')
      }}
      / {{ tl('闭环') }} {{ tl('写操作在后端不可达时本地生效') }})
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { fmtDateTime } from '@/utils/format'
const { t: tl } = useI18n()
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { acknowledgeAlarm, getAlarmHistory, resolveAlarm } from '@/api'
import type { AlarmEvent, AlarmHistoryResponse } from '@/types'
import Pagination from '@/components/Pagination.vue'
import { KpiCard } from '@dc-ioc/ui'
import Panel from '@/components/common/Panel.vue'
import MockDataBanner from '@/components/common/MockDataBanner.vue'

/** 后端不可达时曾静默回退为 mock 数据——现在显式标注，避免误判真实告警历史 */
const usingMock = ref(false)
const data = ref<AlarmHistoryResponse | null>(null)
const fSys = ref('')
const fLv = ref('')
const fState = ref('')
const page = ref(1)
const size = ref(50)
const kw = ref('')
const operator = '值班员'

/* 触达通道数据 (由多通道告警模块整合) */
const channels = [
  { id: 'ch1', icon: '📟', name: tl('短信 SMS'), enabled: true, levels: ['crit', 'warn'], target: tl('运维值班组'), sent: 184 },
  { id: 'ch2', icon: '💬', name: tl('企业微信'), enabled: true, levels: ['crit', 'warn', 'info'], target: tl('数据中心运维群'), sent: 326 },
  { id: 'ch3', icon: '🔔', name: tl('钉钉'), enabled: true, levels: ['crit'], target: tl('应急管理群'), sent: 47 },
  { id: 'ch4', icon: '📧', name: tl('邮件'), enabled: true, levels: ['crit', 'warn'], target: tl('设施经理'), sent: 92 },
  { id: 'ch5', icon: '📞', name: tl('语音外呼'), enabled: false, levels: ['crit'], target: tl('7×24 值守'), sent: 0 },
]
const channelRules = [
  { id: 'r1', name: tl('一级事件电话升级'), channels: [tl('语音外呼'), tl('短信 SMS')], levels: ['crit'], silence: tl('22:00–07:00 免打扰'), enabled: true },
  { id: 'r2', name: tl('二级事件群通知'), channels: [tl('企业微信'), tl('钉钉')], levels: ['warn'], silence: tl('无'), enabled: true },
  { id: 'r3', name: tl('三级事件邮件'), channels: [tl('邮件')], levels: ['info'], silence: tl('工作日 09:00–18:00'), enabled: false },
]
const channelLogs = [
  { id: 'l1', at: new Date(Date.now() - 3600e3).toISOString(), channel: tl('企业微信'), level: 'crit', receiver: tl('数据中心运维群'), summary: tl('A 区冷机 2 回风温度越限'), ok: true },
  { id: 'l2', at: new Date(Date.now() - 7200e3).toISOString(), channel: tl('短信 SMS'), level: 'warn', receiver: tl('运维值班组'), summary: tl('B 区 UPS 负载率 86%'), ok: true },
  { id: 'l3', at: new Date(Date.now() - 10800e3).toISOString(), channel: tl('钉钉'), level: 'crit', receiver: tl('应急管理群'), summary: tl('市电中断演练触发'), ok: false },
]

const systemOptions = computed(() =>
  data.value ? [...new Set(data.value.items.map((e) => e.system))] : [],
)
const stateTag = (s: string) =>
  s === 'active' ? 'r' : s === 'acknowledged' ? 'a' : s === 'resolved' ? 'g' : 'o'
const stateText = (s: string) =>
  (
    ({
      active: '活跃',
      acknowledged: '已确认',
      resolved: '已闭环',
      suppressed: '已抑制',
    }) as Record<string, string>
  )[s] ?? s

function patchLocal(id: string, patch: Partial<AlarmEvent>) {
  const e = data.value?.items.find((x) => x.id === id)
  if (e) Object.assign(e, patch)
}
async function ack(e: AlarmEvent) {
  patchLocal(e.id, {
    status: 'acknowledged',
    acknowledgedAt: new Date().toISOString(),
    acknowledgedBy: operator,
  })
  try {
    await acknowledgeAlarm(e.id, operator)
  } catch {
    /* 后端未就绪 */
  }
}
async function resolve(e: AlarmEvent) {
  patchLocal(e.id, {
    status: 'resolved',
    resolvedAt: new Date().toISOString(),
    resolvedBy: operator,
    note: '已处置并闭环',
    autoResolved: false,
  })
  try {
    await resolveAlarm(e.id, operator, '已处置并闭环')
  } catch {
    /* 后端未就绪 */
  }
}

async function reload() {
  usingMock.value = false
  try {
    data.value = await getAlarmHistory({
      system: fSys.value || undefined,
      level: fLv.value || undefined,
      status: fState.value || undefined,
      page: page.value,
      limit: size.value,
    })
  } catch {
    usingMock.value = true
  }
}

function onPage(p: number) {
  page.value = p
  reload()
}
function onSize(s: number) {
  size.value = s
  page.value = 1
  reload()
}
function onFilter() {
  page.value = 1
  reload()
}

let timer = 0
onMounted(() => {
  reload()
  timer = window.setInterval(reload, Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 5000))
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
.row-crit {
  background: rgba(242, 63, 63, 0.05);
}
.channels {
  margin-top: 20px;
}
.view-sub {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 12px;
}
.view-sub h2 {
  font-size: 16px;
  color: var(--txt);
  margin: 0;
}
.view-sub .sub {
  color: var(--muted, #7e93b8);
  font-size: 12px;
}
.ch-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.ch-card {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
  background: var(--bg2);
}
.ch-card.disabled {
  opacity: 0.5;
}
.ch-top {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
}
.ch-icon {
  font-size: 16px;
}
.ch-name {
  color: var(--txt);
  font-weight: 600;
  font-size: 13px;
  flex: 1;
}
.ch-status {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
}
.ch-status.on {
  color: #34d399;
  background: rgba(52, 211, 153, 0.14);
}
.ch-status.off {
  color: #7e93b8;
  background: rgba(126, 147, 184, 0.14);
}
.ch-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--txt);
  margin-bottom: 10px;
}
.ch-meta .muted {
  margin-right: 4px;
}
.ch-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}
.ch-count {
  color: var(--cyan);
  font-weight: 700;
  font-size: 15px;
}
</style>
