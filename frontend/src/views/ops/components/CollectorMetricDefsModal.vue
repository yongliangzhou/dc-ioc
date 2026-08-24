<template>
  <teleport to="body">
    <div class="modal-mask" v-if="device" @click.self="$emit('close')">
      <div class="modal" role="dialog" aria-modal="true">
        <div class="modal-head">
          <div>
            <div class="modal-title">{{ tl('测点管理') }} {{ tl('·') }} {{ device.device_id }}</div>
            <div class="muted" style="font-size: 11px; margin-top: 3px">
              {{ tl('维护该设备挂载的测点定义') }} ({{ tl('新增 / 编辑 / 删除') }})
            </div>
          </div>
          <button class="btn-sm primary" v-bind="authState('write')" @click="openCreate">
            ＋ {{ tl('新增测点') }}
          </button>
        </div>

        <div class="modal-body scroll-x">
          <table v-if="defs.length">
            <thead>
              <tr>
                <th>{{ tl('测点名') }}</th>
                <th>{{ tl('中文名') }}</th>
                <th>{{ tl('单位') }}</th>
                <th>{{ tl('类型') }}</th>
                <th>{{ tl('状态') }}</th>
                <th>{{ tl('说明') }}</th>
                <th>{{ tl('操作') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in defs" :key="d.id">
                <td class="mono">{{ d.metricName }}</td>
                <td>{{ d.label || '—' }}</td>
                <td>{{ d.unit || '—' }}</td>
                <td>{{ d.dataType }}</td>
                <td>
                  <span class="tag" :class="d.enabled ? 'g' : 'r'">{{
                    d.enabled ? tl('启用') : tl('停用')
                  }}</span>
                </td>
                <td class="muted">{{ d.description || '—' }}</td>
                <td class="p-ops">
                  <button class="link" v-bind="authState('write')" @click="openEdit(d)">{{ tl('编辑') }}</button>
                  <button class="link danger" v-bind="authState('write')" @click="remove(d)">{{ tl('删除') }}</button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="muted" style="text-align: center; padding: 22px">
            {{ loading ? tl('加载中…') : tl('该设备暂无测点定义') }}
          </div>
        </div>

        <div class="modal-foot">
          <span class="muted" style="font-size: 11px">{{ tl('测点定义独立于实时上报数据流') }}</span>
          <button class="btn-sm" @click="$emit('close')">{{ tl('关闭') }}</button>
        </div>

        <!-- 编辑抽屉 -->
        <div class="drawer-mask" v-if="formOpen" @click.self="formOpen = false">
          <div class="drawer">
            <div class="drawer-head">
              <span>{{ editingId ? tl('编辑测点') : tl('新增测点') }}</span>
              <button class="x" @click="formOpen = false">✕</button>
            </div>
            <div class="form">
              <label>{{ tl('测点名') }} (metric_name)
                <input v-model.trim="form.metricName" class="ipt" :disabled="!!editingId" :placeholder="'supply_temp'" />
              </label>
              <div class="row">
                <label>{{ tl('中文名') }}<input v-model.trim="form.label" class="ipt" :placeholder="tl('送风温度')" /></label>
                <label>{{ tl('单位') }}<input v-model.trim="form.unit" class="ipt" :placeholder="'℃'" /></label>
              </div>
              <div class="row">
                <label>{{ tl('数据类型') }}
                  <select v-model="form.dataType" class="ipt">
                    <option value="float">float</option>
                    <option value="int">int</option>
                    <option value="bool">bool</option>
                    <option value="string">string</option>
                  </select>
                </label>
                <label>{{ tl('状态') }}
                  <select v-model="form.enabled" class="ipt">
                    <option :value="true">{{ tl('启用') }}</option>
                    <option :value="false">{{ tl('停用') }}</option>
                  </select>
                </label>
              </div>
              <label>{{ tl('说明') }}<textarea v-model.trim="form.description" class="ipt" rows="2"></textarea></label>
              <div v-if="err" class="err">{{ err }}</div>
              <div class="drawer-foot">
                <button class="btn-sm" @click="formOpen = false">{{ tl('取消') }}</button>
                <button class="btn-sm primary" :disabled="saving" @click="save">{{ saving ? tl('保存中…') : tl('保存') }}</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import type { ExternalDeviceView } from '@/types'
import {
  getMetricDefs,
  createMetricDef,
  updateMetricDef,
  deleteMetricDef,
  type MetricDef,
} from '@/api'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { usePermission, type PermAction } from '@/hooks/usePermission'
const toast = useToast()
const { can, denyTip } = usePermission()
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

const props = defineProps<{
  device: ExternalDeviceView | null
  loading?: boolean
}>()
const emit = defineEmits<{ (e: 'close'): void }>()

const defs = ref<MetricDef[]>([])
const loading = ref(false)
const formOpen = ref(false)
const saving = ref(false)
const err = ref('')
const editingId = ref<number | null>(null)
const form = ref<Partial<MetricDef>>({
  metricName: '', label: '', unit: '', dataType: 'float', enabled: true, description: '',
})

async function loadDefs() {
  if (!props.device) return
  loading.value = true
  try {
    defs.value = await getMetricDefs(props.device.device_id)
  } catch {
    defs.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { metricName: '', label: '', unit: '', dataType: 'float', enabled: true, description: '' }
  err.value = ''
  formOpen.value = true
}
function openEdit(d: MetricDef) {
  editingId.value = d.id
  form.value = { ...d }
  err.value = ''
  formOpen.value = true
}
async function save() {
  if (!props.device) return
  if (!form.value.metricName) {
    err.value = tl('测点名为必填')
    return
  }
  saving.value = true
  err.value = ''
  try {
    const payload = {
      metricName: form.value.metricName,
      label: form.value.label,
      unit: form.value.unit,
      dataType: form.value.dataType,
      enabled: form.value.enabled,
      description: form.value.description,
    }
    if (editingId.value != null) await updateMetricDef(props.device.device_id, editingId.value, payload)
    else await createMetricDef(props.device.device_id, payload)
    formOpen.value = false
    await loadDefs()
    toast.success(tl('已保存'))
  } catch (e: unknown) {
    err.value = (e as ErrorLike)?.message || tl('保存失败')
  } finally {
    saving.value = false
  }
}
async function remove(d: MetricDef) {
  if (!props.device) return
  const ok = await useConfirm({
    title: tl('删除测点'),
    message: `${tl('确认删除测点')} ${d.metricName}?`,
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => {
      await deleteMetricDef(props.device!.device_id, d.id)
    },
  })
  if (ok) {
    await loadDefs()
    toast.success(tl('已删除'))
  }
}

watch(() => props.device, loadDefs)
onMounted(loadDefs)
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
}
.modal {
  width: min(880px, 96vw);
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
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
th, td {
  padding: 9px 10px;
  text-align: left;
  border-bottom: 1px solid var(--line);
}
th {
  background: var(--bg2);
  color: var(--txt2);
  font-weight: 600;
}
.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.muted {
  color: var(--muted);
}
.tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 9px;
}
.tag.g {
  background: rgba(43, 212, 122, 0.12);
  color: var(--green);
}
.tag.r {
  background: rgba(255, 77, 94, 0.12);
  color: var(--red);
}
.p-ops {
  display: flex;
  gap: 8px;
}
.link {
  background: none;
  border: none;
  color: var(--cyan);
  cursor: pointer;
  font-size: 12px;
  padding: 0;
}
.link.danger {
  color: var(--red);
}
.btn-sm {
  padding: 5px 12px;
  border-radius: 7px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt2);
  cursor: pointer;
  font-size: 12px;
}
.btn-sm.primary {
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  color: #04121f;
  border-color: transparent;
  font-weight: 700;
}
.btn-sm:disabled {
  opacity: 0.6;
  cursor: default;
}
.drawer-mask {
  position: fixed;
  inset: 0;
  background: rgba(6, 11, 20, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6vh 16px;
  z-index: 1100;
}
.drawer {
  width: 440px;
  max-width: 94vw;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 14px;
}
.x {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.form label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--txt2);
}
.row {
  display: flex;
  gap: 10px;
}
.row label {
  flex: 1;
}
.ipt {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 7px;
  padding: 7px 9px;
  color: var(--txt);
  font-size: 13px;
  font-family: inherit;
}
.err {
  color: var(--red);
  font-size: 12px;
}
.drawer-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 6px;
}
</style>
