<template>
  <Panel class="scroll-x">
    <table>
      <thead>
        <tr>
          <th v-if="selectable" style="width: 38px">
            <input
              type="checkbox"
              class="ck"
              :checked="allSelected"
              :indeterminate.prop="someSelected && !allSelected"
              :disabled="!alarms.length"
              @change="toggleAll"
              title="全选 / 取消全选"
            />
          </th>
          <th style="width: 65px">{{ tl('级别') }}</th>
          <th style="width: 80px">{{ tl('来源系统') }}</th>
          <th scope="col">{{ tl('告警内容') }}</th>
          <th style="width: 130px">{{ tl('触发时间') }}</th>
          <th style="width: 70px">{{ tl('状态') }}</th>
          <th style="width: 70px">{{ tl('责任人') }}</th>
          <th style="width: 90px">{{ tl('关联设备') }}</th>
          <th style="width: 120px">{{ tl('操作') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="x in alarms"
          :key="alarmKeyOf(x)"
          :class="{ 'row-crit': x.level === 'crit', 'row-warn': x.level === 'warn', 'row-sel': isSelected(x) }"
        >
          <td v-if="selectable">
            <input
              type="checkbox"
              class="ck"
              :checked="isSelected(x)"
              @change="toggleRow(alarmKeyOf(x))"
            />
          </td>
          <td>
            <AlarmBadge :level="mapLevel(x.level)" />
          </td>
          <td>
            <span class="source-tag" :class="sourceCls(x.system)">
              <span class="source-dot"></span>
              {{ sourceLabel(x.system) }}
            </span>
          </td>
          <td class="desc-cell">{{ x.message }}</td>
          <td class="mono" style="font-size: 11px">{{ x.time }}</td>
          <td>
            <StatusBadge :status="mapStateStatus(x.status)" :label="x.status" />
          </td>
          <td>{{ x.owner ?? '—' }}</td>
          <td>
            <a v-if="getDeviceRoute(x)" class="device-link" @click.prevent="goDevice(x)">
              {{ getDeviceRoute(x)?.label }}
            </a>
            <span v-else class="no-link">—</span>
          </td>
          <td>
            <div class="flex gap4">
              <button class="act-btn runbook" @click="$emit('runbook', x)">{{ tl('预案') }}</button>
              <button v-if="x.status === 'active'" class="act-btn ack" @click="$emit('ack', x)">
                {{ tl('确认') }}
              </button>
              <button
                v-if="x.status !== 'resolved'"
                class="act-btn ticket"
                @click="$emit('ticket', x)"
              >
                {{ tl('转工单') }}
              </button>
              <button
                v-if="x.status !== 'resolved'"
                class="act-btn resolve"
                @click="$emit('resolve', x)"
              >
                {{ tl('关单') }}
              </button>
              <button class="act-btn fb" @click="$emit('feedback', x)">{{ tl('反馈') }}</button>
              <button v-if="x.status === 'resolved'" class="act-btn done" disabled>
                {{ tl('已处理') }}
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </Panel>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import { computed } from 'vue'
import type { Alarm } from '@/types'
import { alarmKeyOf } from '@/utils/state'

interface AlarmWithDevice extends Alarm {
  deviceId?: string
  device_id?: string
}
import { AlarmBadge } from '@dc-ioc/ui'
import { StatusBadge } from '@dc-ioc/ui'
import Panel from '@/components/common/Panel.vue'

const props = withDefaults(
  defineProps<{
    alarms: Alarm[]
    /** 是否显示复选框（批量操作） */
    selectable?: boolean
    /** 已选中的行标识（alarmKeyOf 的结果） */
    selected?: string[]
  }>(),
  { selectable: false, selected: () => [] },
)

const emit = defineEmits<{
  (e: 'update:selected', keys: string[]): void
  (e: 'ack', x: Alarm): void
  (e: 'resolve', x: Alarm): void
  (e: 'runbook', x: Alarm): void
  (e: 'ticket', x: Alarm): void
  (e: 'feedback', x: Alarm): void
  (e: 'goDevice', payload: { sys: string; deviceId: string }): void
}>()

/* ---- 选择 ---- */
const keys = computed(() => props.alarms.map(alarmKeyOf))
const allSelected = computed(
  () => props.alarms.length > 0 && keys.value.every((k) => props.selected.includes(k)),
)
const someSelected = computed(() => keys.value.some((k) => props.selected.includes(k)))

function isSelected(a: Alarm) {
  return props.selected.includes(alarmKeyOf(a))
}
function toggleRow(key: string) {
  const next = props.selected.includes(key)
    ? props.selected.filter((k) => k !== key)
    : [...props.selected, key]
  emit('update:selected', next)
}
function toggleAll() {
  // 全选时只补当前列表, 取消时只清掉当前列表里的项, 不影响筛选外的选择
  emit('update:selected', allSelected.value ? [] : Array.from(new Set(keys.value)))
}

// ===== Level Mapping =====
function mapLevel(level: string): string {
  switch (level) {
    case 'crit':
      return 'critical'
    case 'warn':
      return 'warning'
    case 'info':
      return 'info'
    default:
      return level
  }
}

// ===== State → StatusBadge status =====
function mapStateStatus(s: string): string {
  switch (s) {
    case 'active':
    case '待确认':
      return 'warning'
    case 'acknowledged':
    case '处理中':
      return 'warning'
    case 'resolved':
    case '已关闭':
      return 'online'
    case '已处理':
      return 'normal'
    default:
      return s || 'offline'
  }
}

// ===== Source System Label & Color =====
function matchSource(system: string): string {
  const s = (system || '').toLowerCase()
  if (s.includes('冷源') || s.includes('chiller') || s.includes('冷冻')) return 'chiller'
  if (s.includes('空调') || s.includes('精密') || s.includes('crac') || s.includes('末端'))
    return 'crac'
  if (s.includes('液冷') || s.includes('liquid') || s.includes('冷板')) return 'liquid'
  if (
    s.includes('配电') ||
    s.includes('电力') ||
    s.includes('power') ||
    s.includes('电气') ||
    s.includes('ups') ||
    s.includes('柴发') ||
    s.includes('变压器')
  )
    return 'power'
  if (
    s.includes('消防') ||
    s.includes('火灾') ||
    s.includes('fire') ||
    s.includes('烟感') ||
    s.includes('气体')
  )
    return 'fire'
  if (
    s.includes('安防') ||
    s.includes('门禁') ||
    s.includes('监控') ||
    s.includes('security') ||
    s.includes('cctv')
  )
    return 'security'
  if (s.includes('网络') || s.includes('交换机') || s.includes('路由') || s.includes('network'))
    return 'network'
  if (s.includes('暖通') || s.includes('hvac') || s.includes('制冷') || s.includes('冷却'))
    return 'hvac'
  return 'other'
}

const SOURCE_DEFS: Record<string, { label: string; cls: string }> = {
  chiller: { label: '冷源系统', cls: 'src-chiller' },
  crac: { label: '空调末端', cls: 'src-crac' },
  liquid: { label: '液冷系统', cls: 'src-liquid' },
  power: { label: '配电系统', cls: 'src-power' },
  fire: { label: '消防系统', cls: 'src-fire' },
  security: { label: '安防系统', cls: 'src-security' },
  network: { label: '网络系统', cls: 'src-network' },
  hvac: { label: '暖通系统', cls: 'src-hvac' },
  other: { label: '其他', cls: 'src-other' },
}

function sourceCls(sys: string): string {
  return SOURCE_DEFS[matchSource(sys)]?.cls ?? 'src-other'
}

function sourceLabel(sys: string): string {
  // If sys is already a readable Chinese label, return it
  const m = matchSource(sys)
  // Return original sys if it looks like a proper label, otherwise mapped
  if (m === 'other' && sys && sys.length <= 12 && /[\u4e00-\u9fff]/.test(sys)) {
    return sys
  }
  return SOURCE_DEFS[m]?.label ?? (sys || '未知')
}

// ===== Device Route =====
const DEVICE_ROUTES: Record<string, { path: string; label: string }> = {
  chiller: { path: '/monitor/hvac/chiller', label: '冷源设备' },
  crac: { path: '/monitor/hvac/crac', label: '空调末端' },
  liquid: { path: '/monitor/hvac/liquid', label: '液冷设备' },
  power: { path: '/monitor/power', label: '配电设备' },
  fire: { path: '/ops/fire', label: '消防设备' },
  security: { path: '/ops/security', label: '安防设备' },
  network: { path: '/monitor/network', label: '网络设备' },
  hvac: { path: '/monitor/hvac/chiller', label: '暖通设备' },
}

function getDeviceRoute(alarm: Alarm): { path: string; label: string } | null {
  const m = matchSource(alarm.system)
  const route = DEVICE_ROUTES[m]
  if (!route) return null
  // Append deviceId if available
  const deviceId = (alarm as AlarmWithDevice).deviceId ?? (alarm as AlarmWithDevice).device_id ?? ''
  return {
    path: route.path + (deviceId ? `?device=${deviceId}` : ''),
    label: route.label,
  }
}

function goDevice(alarm: Alarm) {
  const route = getDeviceRoute(alarm)
  if (!route) return
  // Use window.location or emit — let parent handle navigation
  emit('goDevice', {
    sys: alarm.system,
    deviceId: (alarm as AlarmWithDevice).deviceId ?? (alarm as AlarmWithDevice).device_id ?? '',
  })
}
</script>

<style scoped>
/* Source System Tag */
.source-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10.5px;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: 0.2px;
}
.source-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.src-chiller {
  color: #22e3ff;
  background: rgba(34, 227, 255, 0.1);
  border: 1px solid rgba(34, 227, 255, 0.2);
}
.src-chiller .source-dot {
  background: #22e3ff;
  box-shadow: 0 0 4px #22e3ff;
}
.src-crac {
  color: #2bd47a;
  background: rgba(43, 212, 122, 0.1);
  border: 1px solid rgba(43, 212, 122, 0.2);
}
.src-crac .source-dot {
  background: #2bd47a;
  box-shadow: 0 0 4px #2bd47a;
}
.src-liquid {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
}
.src-liquid .source-dot {
  background: #3b82f6;
  box-shadow: 0 0 4px #3b82f6;
}
.src-power {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.2);
}
.src-power .source-dot {
  background: #f59e0b;
  box-shadow: 0 0 4px #f59e0b;
}
.src-fire {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
}
.src-fire .source-dot {
  background: #ef4444;
  box-shadow: 0 0 4px #ef4444;
}
.src-security {
  color: #a78bfa;
  background: rgba(167, 139, 250, 0.1);
  border: 1px solid rgba(167, 139, 250, 0.2);
}
.src-security .source-dot {
  background: #a78bfa;
  box-shadow: 0 0 4px #a78bfa;
}
.src-network {
  color: #94a3b8;
  background: rgba(148, 163, 184, 0.1);
  border: 1px solid rgba(148, 163, 184, 0.2);
}
.src-network .source-dot {
  background: #94a3b8;
  box-shadow: 0 0 4px #94a3b8;
}
.src-hvac {
  color: #05b896;
  background: rgba(5, 184, 150, 0.1);
  border: 1px solid rgba(5, 184, 150, 0.2);
}
.src-hvac .source-dot {
  background: #05b896;
  box-shadow: 0 0 4px #05b896;
}
.src-other {
  color: #6b7280;
  background: rgba(107, 114, 128, 0.1);
  border: 1px solid rgba(107, 114, 128, 0.15);
}
.src-other .source-dot {
  background: #6b7280;
}

/* Device Link */
.device-link {
  color: var(--cyan);
  cursor: pointer;
  font-size: 11px;
  text-decoration: underline;
  text-underline-offset: 3px;
  transition: color 0.15s;
}
.device-link:hover {
  color: #22e3ff;
}
.no-link {
  color: var(--txt3);
  font-size: 11px;
}

/* Row highlighting */
.row-crit {
  background: linear-gradient(90deg, rgba(255, 77, 94, 0.06), transparent);
}
.row-warn {
  background: linear-gradient(90deg, rgba(255, 176, 32, 0.04), transparent);
}
.row-sel {
  background: rgba(34, 227, 255, 0.08);
  box-shadow: inset 2px 0 0 var(--cyan);
}
.desc-cell {
  max-width: 260px;
}

/* 复选框 */
.ck {
  width: 14px;
  height: 14px;
  cursor: pointer;
  accent-color: var(--cyan);
  vertical-align: middle;
}
.ck:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

/* Action buttons — keep existing styles */
.act-btn {
  padding: 2px 8px;
  border-radius: 4px;
  border: 1px solid var(--line);
  font-size: 10px;
  cursor: pointer;
  background: var(--bg2);
  color: var(--txt2);
  transition: all 0.15s;
}
.act-btn.ack {
  border-color: var(--cyan);
  color: var(--cyan);
}
.act-btn.ack:hover {
  background: rgba(34, 227, 255, 0.1);
}
.act-btn.ticket {
  border-color: #a78bfa;
  color: #a78bfa;
}
.act-btn.ticket:hover {
  background: rgba(167, 139, 250, 0.12);
}
.act-btn.runbook {
  border-color: #2bd47a;
  color: #2bd47a;
}
.act-btn.runbook:hover {
  background: rgba(43, 212, 122, 0.1);
}
.act-btn.fb {
  border-color: var(--amber, #ffb020);
  color: var(--amber, #ffb020);
}
.act-btn.fb:hover {
  background: rgba(255, 176, 32, 0.12);
}
.act-btn.resolve {
  border-color: var(--green);
  color: var(--green);
}
.act-btn.resolve:hover {
  background: rgba(43, 212, 122, 0.1);
}
.act-btn.done {
  border-color: rgba(255, 255, 255, 0.1);
  color: var(--txt3);
  cursor: default;
}
</style>
