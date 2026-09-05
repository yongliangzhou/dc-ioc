<template>
  <div>
    <div class="view-head">
      <h1>{{ t('notifyCenter.title') }}</h1>
      <span class="sub">{{ t('notifyCenter.sub') }}</span>
    </div>

    <!-- ===== 通道管理 ===== -->
    <Panel :title="t('notifyCenter.channels')">
      <template #extra>
        <button class="btn-sm primary" @click="openNew">{{ t('notifyCenter.newChannel') }}</button>
      </template>

      <AsyncSection
        :loading="chLoading"
        :error="chError"
        :empty="chEmpty"
        :min-height="'200px'"
        @retry="reloadChannels"
      >
        <div class="scroll-x">
          <table>
            <thead>
              <tr>
                <th style="width: 110px">{{ t('notifyCenter.type') }}</th>
                <th style="width: 160px">{{ t('notifyCenter.name') }}</th>
                <th style="width: 90px">{{ t('notifyCenter.minLevel') }}</th>
                <th style="width: 150px">{{ t('notifyCenter.quietWindow') }}</th>
                <th style="width: 150px">{{ t('notifyCenter.url') }}</th>
                <th style="width: 70px">{{ t('notifyCenter.enabled') }}</th>
                <th style="width: 170px">{{ t('notifyCenter.action') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in channels ?? []" :key="row.id">
                <td>
                  <span class="ctag" :class="'ct-' + row.type">{{ row.type }}</span>
                </td>
                <td>{{ row.name }}</td>
                <td>
                  <select
                    class="ipt"
                    style="width: 86px"
                    :value="row.minLevel"
                    @change="changeLevel(row, $event)"
                  >
                    <option value="crit">{{ t('notifyCenter.lvCrit') }}</option>
                    <option value="warn">{{ t('notifyCenter.lvWarn') }}</option>
                    <option value="info">{{ t('notifyCenter.lvInfo') }}</option>
                  </select>
                </td>
                <td class="mono" style="font-size: 11px">
                  {{ row.quietStart && row.quietEnd ? `${row.quietStart} ~ ${row.quietEnd}` : '—' }}
                </td>
                <td class="mono url" style="font-size: 11px" :title="row.url ?? ''">
                  {{ row.url || '—' }}
                </td>
                <td>
                  <label class="switch">
                    <input
                      type="checkbox"
                      :checked="row.enabled"
                      @change="toggleEnabled(row, $event)"
                    />
                    <span class="slider"></span>
                  </label>
                </td>
                <td>
                  <div class="row-actions">
                    <button class="btn-sm" @click="testChannel(row)">
                      {{ t('notifyCenter.test') }}
                    </button>
                    <button class="btn-sm" @click="openEdit(row)">
                      {{ t('notifyCenter.edit') }}
                    </button>
                    <button class="btn-sm danger" @click="removeChannel(row)">
                      {{ t('notifyCenter.del') }}
                    </button>
                  </div>
                </td>
              </tr>
              <tr v-if="!(channels ?? []).length">
                <td colspan="7" class="muted" style="text-align: center; padding: 20px">
                  {{ t('notifyCenter.noChannels') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </AsyncSection>
    </Panel>

    <!-- ===== 发送记录 ===== -->
    <Panel :title="t('notifyCenter.records')" style="margin-top: 12px">
      <div class="flex gap8 wrap" style="align-items: center; margin-bottom: 10px">
        <select v-model="filters.level" class="ipt" style="width: 130px">
          <option value="">{{ t('notifyCenter.allLevels') }}</option>
          <option value="crit">{{ t('notifyCenter.lvCrit') }}</option>
          <option value="warn">{{ t('notifyCenter.lvWarn') }}</option>
          <option value="info">{{ t('notifyCenter.lvInfo') }}</option>
        </select>
        <select v-model="filters.channelId" class="ipt" style="width: 160px">
          <option value="">{{ t('notifyCenter.allChannels') }}</option>
          <option v-for="c in channels ?? []" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
        <select v-model="filters.status" class="ipt" style="width: 130px">
          <option value="">{{ t('notifyCenter.allStatus') }}</option>
          <option value="sent">{{ t('notifyCenter.sent') }}</option>
          <option value="failed">{{ t('notifyCenter.failed') }}</option>
          <option value="muted">{{ t('notifyCenter.muted') }}</option>
          <option value="dedup">{{ t('notifyCenter.dedup') }}</option>
        </select>
        <button class="btn-sm primary" @click="applyFilters">{{ t('notifyCenter.filter') }}</button>
        <span class="muted" style="margin-left: auto; font-size: 11px"
          >{{ t('notifyCenter.total') }} {{ recTotal }}</span
        >
      </div>

      <AsyncSection
        :loading="recLoading"
        :error="recError"
        :empty="recEmpty"
        :min-height="'280px'"
        @retry="reloadRecords"
      >
        <div class="scroll-x">
          <table>
            <thead>
              <tr>
                <th style="width: 160px">{{ t('notifyCenter.time') }}</th>
                <th style="width: 80px">{{ t('notifyCenter.level') }}</th>
                <th style="width: 240px">{{ t('notifyCenter.recordTitle') }}</th>
                <th style="width: 140px">{{ t('notifyCenter.channel') }}</th>
                <th style="width: 90px">{{ t('notifyCenter.status') }}</th>
                <th style="width: 90px">{{ t('notifyCenter.retryCount') }}</th>
                <th>{{ t('notifyCenter.error') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in records" :key="row.id">
                <td class="mono" style="font-size: 11px">{{ fmtTime(row.createdAt) }}</td>
                <td>
                  <span class="ltag" :class="'lt-' + row.level">{{ levelText(row.level) }}</span>
                </td>
                <td>{{ row.title }}</td>
                <td>{{ row.channelName }}</td>
                <td>
                  <span class="ltag" :class="'st-' + row.status">{{ statusText(row.status) }}</span>
                </td>
                <td class="mono" style="font-size: 11px">{{ row.retryCount }}</td>
                <td class="err-cell muted" style="font-size: 11px" :title="row.error ?? ''">
                  {{ row.error || '—' }}
                </td>
              </tr>
              <tr v-if="!records.length">
                <td colspan="7" class="muted" style="text-align: center; padding: 20px">
                  {{ t('notifyCenter.emptyRecords') }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </AsyncSection>

      <Pagination
        :total="recTotal"
        :page="recPage"
        :size="recSize"
        @change="onPageChange"
        @size-change="onSizeChange"
      />
    </Panel>

    <!-- ===== 通道新增/编辑弹窗 ===== -->
    <transition name="fade">
      <div v-if="formOpen" class="modal-mask" @click.self="formOpen = false">
        <div class="modal-card">
          <div class="modal-head">
            <span class="modal-title">{{
              editing ? t('notifyCenter.editChannel') : t('notifyCenter.newChannel')
            }}</span>
            <button class="btn-sm" @click="formOpen = false">✕</button>
          </div>
          <div class="form-grid">
            <label class="fl">{{ t('notifyCenter.type') }}</label>
            <select v-model="form.type" class="ipt" :disabled="!!editing">
              <option value="dingtalk">dingtalk</option>
              <option value="email">email</option>
              <option value="wechat">wechat</option>
              <option value="sms">sms</option>
              <option value="custom">custom</option>
            </select>
            <label class="fl">{{ t('notifyCenter.name') }}</label>
            <input v-model.trim="form.name" class="ipt" :placeholder="t('notifyCenter.namePh')" />
            <label class="fl">{{ t('notifyCenter.url') }}</label>
            <input
              v-model.trim="form.url"
              class="ipt"
              placeholder="https://oapi.dingtalk.com/robot/send?access_token=..."
            />
            <label class="fl">{{ t('notifyCenter.minLevel') }}</label>
            <select v-model="form.minLevel" class="ipt">
              <option value="crit">{{ t('notifyCenter.lvCrit') }}</option>
              <option value="warn">{{ t('notifyCenter.lvWarn') }}</option>
              <option value="info">{{ t('notifyCenter.lvInfo') }}</option>
            </select>
            <label class="fl">{{ t('notifyCenter.quietWindow') }}</label>
            <div class="flex gap8" style="align-items: center">
              <input v-model="form.quietStart" class="ipt" type="time" />
              <span class="muted">~</span>
              <input v-model="form.quietEnd" class="ipt" type="time" />
            </div>
            <label class="fl">{{ t('notifyCenter.enabled') }}</label>
            <label class="switch">
              <input v-model="form.enabled" type="checkbox" />
              <span class="slider"></span>
            </label>
          </div>
          <div class="modal-foot">
            <button class="btn-sm" @click="formOpen = false">{{ t('notifyCenter.cancel') }}</button>
            <button class="btn-sm primary" :disabled="saving" @click="saveChannel">
              {{ t('notifyCenter.save') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Panel from '@/components/common/Panel.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import Pagination from '@/components/Pagination.vue'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { toErrorMessage, useAsyncPage } from '@/composables/useAsyncPage'
import {
  createNotificationChannel,
  deleteNotificationChannel,
  getNotificationChannels,
  getNotificationRecords,
  testNotificationChannel,
  updateNotificationChannel,
} from '@/api'
import type { NotificationChannel, NotificationChannelType, NotificationRecord } from '@/types'

const { t } = useI18n()
const toast = useToast()

/* ---------------- 通道管理 ---------------- */
const {
  data: channels,
  loading: chLoading,
  error: chError,
  empty: chEmpty,
  reload: reloadChannels,
} = useAsyncPage<NotificationChannel[]>(() => getNotificationChannels(), {
  isEmpty: (d) => !d.length,
})

const formOpen = ref(false)
const editing = ref<NotificationChannel | null>(null)
const saving = ref(false)
const form = reactive<{
  type: NotificationChannelType
  name: string
  url: string
  minLevel: 'crit' | 'warn' | 'info'
  quietStart: string
  quietEnd: string
  enabled: boolean
}>({
  type: 'dingtalk',
  name: '',
  url: '',
  minLevel: 'warn',
  quietStart: '',
  quietEnd: '',
  enabled: true,
})

function openNew() {
  editing.value = null
  form.type = 'dingtalk'
  form.name = ''
  form.url = ''
  form.minLevel = 'warn'
  form.quietStart = ''
  form.quietEnd = ''
  form.enabled = true
  formOpen.value = true
}

function openEdit(row: NotificationChannel) {
  editing.value = row
  form.type = row.type
  form.name = row.name
  form.url = row.url ?? ''
  form.minLevel = row.minLevel
  form.quietStart = row.quietStart ?? ''
  form.quietEnd = row.quietEnd ?? ''
  form.enabled = row.enabled
  formOpen.value = true
}

function payload() {
  return {
    type: form.type,
    name: form.name,
    url: form.url || null,
    minLevel: form.minLevel,
    quietStart: form.quietStart || null,
    quietEnd: form.quietEnd || null,
    enabled: form.enabled,
  }
}

async function saveChannel() {
  if (!form.name) {
    toast.warning(t('notifyCenter.nameRequired'))
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      await updateNotificationChannel(editing.value.id, payload())
      toast.success(t('notifyCenter.updateSuccess'))
    } else {
      await createNotificationChannel(payload())
      toast.success(t('notifyCenter.addSuccess'))
    }
    formOpen.value = false
    reloadChannels()
  } catch (e) {
    toast.error(toErrorMessage(e, t('notifyCenter.saveFailed')))
  } finally {
    saving.value = false
  }
}

async function toggleEnabled(row: NotificationChannel, ev: Event) {
  const next = (ev.target as HTMLInputElement).checked
  try {
    await updateNotificationChannel(row.id, { enabled: next })
    row.enabled = next
  } catch (e) {
    ;(ev.target as HTMLInputElement).checked = row.enabled
    toast.error(toErrorMessage(e, t('notifyCenter.saveFailed')))
  }
}

async function changeLevel(row: NotificationChannel, ev: Event) {
  const next = (ev.target as HTMLSelectElement).value as 'crit' | 'warn' | 'info'
  try {
    await updateNotificationChannel(row.id, { minLevel: next })
    row.minLevel = next
  } catch (e) {
    ;(ev.target as HTMLSelectElement).value = row.minLevel
    toast.error(toErrorMessage(e, t('notifyCenter.saveFailed')))
  }
}

async function removeChannel(row: NotificationChannel) {
  const ok = await useConfirm({ message: t('notifyCenter.confirmDelete'), danger: true })
  if (!ok) return
  try {
    await deleteNotificationChannel(row.id)
    toast.success(t('notifyCenter.deleteSuccess'))
    reloadChannels()
  } catch (e) {
    toast.error(toErrorMessage(e, t('notifyCenter.deleteFailed')))
  }
}

async function testChannel(row: NotificationChannel) {
  try {
    const res = await testNotificationChannel({
      channelId: row.id,
      title: t('notifyCenter.testSent'),
      message: t('notifyCenter.testMessage'),
    })
    if (res?.status === 'sent') toast.success(t('notifyCenter.testSent'))
    else toast.error(`${t('notifyCenter.testFailed')}: ${res?.error || res?.status || '—'}`)
  } catch (e) {
    toast.error(toErrorMessage(e, t('notifyCenter.testFailed')))
  }
}

/* ---------------- 发送记录 ---------------- */
const records = ref<NotificationRecord[]>([])
const recTotal = ref(0)
const recPage = ref(1)
const recSize = ref(20)
const filters = reactive<{ level: string; channelId: string; status: string }>({
  level: '',
  channelId: '',
  status: '',
})

const {
  loading: recLoading,
  error: recError,
  empty: recEmpty,
  reload: reloadRecords,
} = useAsyncPage(
  async () => {
    const res = await getNotificationRecords({
      page: recPage.value,
      pageSize: recSize.value,
      level: (filters.level || undefined) as 'crit' | 'warn' | 'info' | undefined,
      channelId: filters.channelId ? Number(filters.channelId) : undefined,
      status: (filters.status || undefined) as 'sent' | 'failed' | 'muted' | 'dedup' | undefined,
    })
    records.value = res?.items ?? []
    recTotal.value = res?.total ?? 0
    return res
  },
  { isEmpty: () => records.value.length === 0, keepDataOnError: false },
)

/** 筛选/查询: 变更过滤条件后回到第 1 页再查询 */
function applyFilters() {
  recPage.value = 1
  reloadRecords()
}

function onPageChange(p: number) {
  recPage.value = p
  reloadRecords()
}

function onSizeChange(s: number) {
  recSize.value = s
  recPage.value = 1
  reloadRecords()
}

/* ---------------- 展示辅助 ---------------- */
const levelText = (l: string) =>
  l === 'crit'
    ? t('notifyCenter.lvCrit')
    : l === 'warn'
      ? t('notifyCenter.lvWarn')
      : t('notifyCenter.lvInfo')
const statusText = (s: string) =>
  ({
    sent: t('notifyCenter.sent'),
    failed: t('notifyCenter.failed'),
    muted: t('notifyCenter.muted'),
    dedup: t('notifyCenter.dedup'),
  })[s] ?? s

function fmtTime(s?: string) {
  if (!s) return '—'
  const d = new Date(s)
  if (isNaN(d.getTime())) return s
  return d.toLocaleString('zh-CN', { hour12: false })
}
</script>

<style scoped>
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
.btn-sm.primary {
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  color: #04121f;
  border-color: transparent;
  font-weight: 700;
}
.btn-sm.danger {
  color: var(--red, #ff6b6b);
}
.scroll-x {
  overflow-x: auto;
}
.mono {
  font-family: var(--mono, monospace);
}
.muted {
  color: var(--txt3);
}
.url {
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.err-cell {
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: help;
}

/* 通道类型徽标: dingtalk 蓝 / email 紫 / wechat 绿 / sms 橙 / custom 灰 */
.ctag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  border: 1px solid;
  line-height: 1.5;
}
.ct-dingtalk {
  color: #4da8ff;
  border-color: #4da8ff55;
  background: #4da8ff14;
}
.ct-email {
  color: #b48cff;
  border-color: #b48cff55;
  background: #b48cff14;
}
.ct-wechat {
  color: #3ecf8e;
  border-color: #3ecf8e55;
  background: #3ecf8e14;
}
.ct-sms {
  color: #ffa94d;
  border-color: #ffa94d55;
  background: #ffa94d14;
}
.ct-custom {
  color: #8a97a8;
  border-color: #8a97a855;
  background: #8a97a814;
}

/* 级别/状态徽标 */
.ltag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 20px;
  font-size: 11px;
  border: 1px solid;
  line-height: 1.5;
}
.lt-crit {
  color: #ff6b6b;
  border-color: #ff6b6b55;
  background: #ff6b6b14;
}
.lt-warn {
  color: #ffa94d;
  border-color: #ffa94d55;
  background: #ffa94d14;
}
.lt-info {
  color: var(--cyan);
  border-color: color-mix(in srgb, var(--cyan) 35%, transparent);
  background: color-mix(in srgb, var(--cyan) 8%, transparent);
}
.st-sent {
  color: #3ecf8e;
  border-color: #3ecf8e55;
  background: #3ecf8e14;
}
.st-failed {
  color: #ff6b6b;
  border-color: #ff6b6b55;
  background: #ff6b6b14;
}
.st-muted {
  color: #8a97a8;
  border-color: #8a97a855;
  background: #8a97a814;
}
.st-dedup {
  color: #4da8ff;
  border-color: #4da8ff55;
  background: #4da8ff14;
}

/* 启停开关 */
.switch {
  position: relative;
  display: inline-block;
  width: 34px;
  height: 18px;
  cursor: pointer;
}
.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.slider {
  position: absolute;
  inset: 0;
  border-radius: 18px;
  background: var(--bg2);
  border: 1px solid var(--line);
  transition:
    background 0.15s,
    border-color 0.15s;
}
.slider::before {
  content: '';
  position: absolute;
  width: 12px;
  height: 12px;
  left: 2px;
  top: 2px;
  border-radius: 50%;
  background: var(--txt3);
  transition:
    transform 0.15s,
    background 0.15s;
}
.switch input:checked + .slider {
  background: color-mix(in srgb, var(--cyan) 30%, transparent);
  border-color: var(--cyan);
}
.switch input:checked + .slider::before {
  transform: translateX(16px);
  background: var(--cyan);
}

.row-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* 弹窗 */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 90;
}
.modal-card {
  width: min(520px, 92vw);
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px;
}
.modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.modal-title {
  font-size: 15px;
  font-weight: 700;
}
.form-grid {
  display: grid;
  grid-template-columns: 92px 1fr;
  gap: 10px 12px;
  align-items: center;
}
.fl {
  font-size: 12px;
  color: var(--txt3);
}
.modal-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.18s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
