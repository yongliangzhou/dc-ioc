<template>
  <Panel class="scroll-x">
    <table>
      <caption class="sr-only">
        {{ tl('外部注册设备列表') }}（{{ tl('状态') }}、{{ tl('设备') }} ID、{{ tl('名称') }}、{{
          tl('型号')
        }}、IP、{{ tl('协议') }}、{{ tl('业务域') }}、{{ tl('厂商') }}、{{ tl('最近上报') }}、{{
          tl('测点数')
        }}、{{ tl('操作') }}）
      </caption>
      <thead>
        <tr>
          <th scope="col">{{ tl('状态') }}</th>
          <th scope="col">{{ tl('设备') }} ID</th>
          <th scope="col">{{ tl('名称') }}</th>
          <th scope="col">{{ tl('型号') }}</th>
          <th scope="col">IP</th>
          <th scope="col">{{ tl('协议') }}</th>
          <th scope="col">{{ tl('业务域') }}</th>
          <th scope="col">{{ tl('厂商') }}</th>
          <th scope="col">{{ tl('最近上报') }}</th>
          <th scope="col">{{ tl('测点数') }}</th>
          <th scope="col" style="min-width: 140px">{{ tl('操作') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="d in items"
          :key="d.device_id"
          :class="{ sel: selectedId && selectedId === d.device_id }"
          @click="$emit('select', d)"
        >
          <td>
            <span class="dot" :class="d.online ? 'g' : 'o'"></span>{{ d.online ? '在线' : '离线' }}
          </td>
          <td class="mono">{{ d.device_id }}</td>
          <td>{{ d.name || '—' }}</td>
          <td>{{ d.model }}</td>
          <td class="mono">{{ d.ip }}</td>
          <td>
            <span class="tag b">{{ d.protocol || '—' }}</span>
          </td>
          <td>{{ d.domain || '—' }}</td>
          <td>{{ d.vendor || '—' }}</td>
          <td class="mono">{{ fmtDateTime(d.last_seen) }}</td>
          <td class="mono">{{ d.metric_count }}</td>
          <td>
            <button class="btn-sm" @click.stop="$emit('open-metrics', d)">{{ tl('测点') }}</button>
            <button class="btn-sm" style="margin-left: 4px" @click.stop="$emit('open-edit', d)">
              {{ tl('编辑') }}
            </button>
            <button
              class="btn-sm danger"
              style="margin-left: 4px"
              @click.stop="$emit('confirm-delete', d)"
            >
              {{ tl('删除') }}
            </button>
          </td>
        </tr>
        <tr v-if="!items.length">
          <td colspan="11" class="muted" style="text-align: center; padding: 18px">
            {{ tl('暂无已注册设备') }} {{ tl('—') }} {{ tl('采集器可调用') }} POST
            /api/external/device/register {{ tl('注册') }}
          </td>
        </tr>
      </tbody>
    </table>
  </Panel>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { fmtDateTime } from '@/utils/format'
import Panel from '@/components/common/Panel.vue'
const { t: tl } = useI18n()
import type { ExternalDeviceView } from '@/types'
defineProps<{
  items: ExternalDeviceView[]
  selectedId?: string
}>()

defineEmits<{
  (e: 'select', d: ExternalDeviceView): void
  (e: 'open-metrics', d: ExternalDeviceView): void
  (e: 'open-edit', d: ExternalDeviceView): void
  (e: 'confirm-delete', d: ExternalDeviceView): void
}>()
</script>

<style scoped>
:deep(tr.sel td) {
  background: rgba(34, 227, 255, 0.08);
}
:deep(tbody tr) {
  cursor: pointer;
}
.btn-sm.danger {
  background: rgba(242, 63, 63, 0.15);
  color: var(--red);
  border-color: rgba(242, 63, 63, 0.4);
}
.btn-sm.danger:hover {
  background: rgba(242, 63, 63, 0.3);
}
</style>
