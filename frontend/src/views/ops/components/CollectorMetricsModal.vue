<template>
  <teleport to="body">
    <div class="modal-mask" v-if="device" @click.self="$emit('close')">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div>
            <div class="modal-title">{{ tl('查看测点') }} {{ tl('·') }} {{ device.device_id }}</div>
            <div class="muted" style="font-size: 11px; margin-top: 3px">
              {{ tl('最近') }} {{ metrics.length }} {{ tl('条上报') }} {{ tl('·') }}
              {{ tl('数据源') }} /api/external/devices/{{ device.device_id }}/metrics
            </div>
          </div>
          <button class="btn-sm" @click="$emit('close')">{{ tl('关闭') }} ✕</button>
        </div>
        <div class="modal-body scroll-x">
          <table v-if="metrics.length">
            <thead>
              <tr>
                <th>{{ tl('测点') }} ({{ tl('语义') }})</th>
                <th>{{ tl('数值') }}</th>
                <th>{{ tl('单位') }}</th>
                <th>{{ tl('质量') }}</th>
                <th>{{ tl('采样时间') }}</th>
                <th>{{ tl('接收时间') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(m, i) in metrics" :key="i">
                <td>
                  <div style="font-weight: 600">{{ mLab(m.metric_name) }}</div>
                  <div class="mono muted" style="font-size: 11px">{{ m.metric_name }}</div>
                </td>
                <td class="mono" style="font-weight: 700">{{ m.value }}</td>
                <td>{{ m.unit || '—' }}</td>
                <td>
                  <span class="tag" :class="qTag(m.quality)">{{ m.quality }}</span>
                </td>
                <td class="mono">{{ fmtDateTime(m.ts) }}</td>
                <td class="mono">{{ fmtDateTime(m.received_at) }}</td>
              </tr>
            </tbody>
          </table>
          <div v-else class="muted" style="text-align: center; padding: 22px">
            {{ loading ? '加载中…' : '该设备暂无测点上报记录' }}
          </div>
        </div>
        <div class="modal-foot">
          <span class="muted" style="font-size: 11px"
            >{{ tl('由采集器每') }} 5s {{ tl('经契约端点推送') }} {{ tl('·') }}
            {{ tl('质量码') }} good / uncertain / bad</span
          >
          <button class="btn-sm" @click="$emit('refresh')">{{ tl('刷新') }}</button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { fmtDateTime } from '@/utils/format'
const { t: tl } = useI18n()
import type { ExternalDeviceView, MetricRecordView } from '@/types'
defineProps<{
  device: ExternalDeviceView | null
  metrics: MetricRecordView[]
  loading: boolean
}>()

defineEmits<{ (e: 'close'): void; (e: 'refresh'): void }>()

function mLab(name: string): string {
  const map: Record<string, string> = {
    supply_temp: '送风温度',
    return_temp: '回风温度',
    inlet_temp: '进风温度',
    outlet_temp: '出风温度',
    humidity: '湿度',
    power_kw: '功耗',
    cpu_usage: 'CPU 使用率',
    temp: '温度',
  }
  return map[name] ?? name
}
const qTag = (q: string) => (q === 'good' ? 'g' : q === 'uncertain' ? 'a' : 'r')
</script>

<style scoped>
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(6, 11, 20, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6vh 16px;
  z-index: 1000;
  animation: modalFade 0.15s ease;
}
.modal {
  width: min(900px, 96vw);
  max-height: 86vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, var(--panel), var(--bg2));
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}
.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
}
.modal-title {
  font-size: 15px;
  font-weight: 700;
}
.modal-body {
  padding: 6px 16px 14px;
  overflow: auto;
}
.modal-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 16px;
  border-top: 1px solid var(--line);
}
@keyframes modalFade {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}
</style>
