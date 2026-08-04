<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.duty') }}</h1>
      <span class="sub">{{ tl('人员值班与交接班管理') }}</span>
    </div>
    <div class="grid cols-3" v-if="stats">
      <MetricCard
        metric-name="duty-total"
        :label="tl('总班次')"
        :value="stats.totalShifts"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="duty-today"
        :label="tl('今日班次')"
        :value="stats.todayShifts"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="duty-week"
        :label="tl('本周班次')"
        :value="shifts.length"
        quality="good"
        :online="true"
      />
    </div>
    <Panel style="margin-top: 16px">
      <div class="flex between" style="margin-bottom: 12px">
        <h5 class="section-title" style="margin: 0">{{ tl('值班表') }}</h5>
        <div class="flex gap">
          <input type="date" v-model="fromStr" class="d-inp" />
          <span class="muted">~</span>
          <input type="date" v-model="toStr" class="d-inp" />
        </div>
      </div>
      <div class="tbl" v-if="shifts.length">
        <div class="tbl-head">
          <span class="col w-duty-date">{{ tl('日期') }}</span
          ><span class="col w-duty-type">{{ tl('班次') }}</span
          ><span class="col w-duty-on">{{ tl('当值') }}</span
          ><span class="col w-duty-bk">{{ tl('备班') }}</span
          ><span class="col w-duty-note">{{ tl('交接事项') }}</span>
        </div>
        <div v-for="s in shifts" :key="s.id" class="tbl-row">
          <span class="col w-duty-date">{{ s.shiftDate }}</span>
          <span class="col w-duty-type"
            ><span class="pill-tag" :class="s.shiftType === 'day' ? 'b' : ''">{{
              s.shiftType === 'day' ? '白班' : '夜班'
            }}</span></span
          >
          <span class="col w-duty-on fw">{{ s.onDuty }}</span>
          <span class="col w-duty-bk muted">{{ s.backupDuty || '-' }}</span>
          <span class="col w-duty-note muted">{{ s.handoverNotes || '-' }}</span>
        </div>
      </div>
      <div class="empty" v-else>{{ tl('暂无排班') }}</div>
    </Panel>
    <Panel v-if="!shifts.length && !e"
      ><div class="flex center" style="padding: 40px">
        <span class="muted">{{ tl('common.loading') }}</span>
      </div></Panel
    >
    <Panel v-if="e"
      ><div class="flex center" style="padding: 40px">
        <span class="muted" style="color: var(--red)">{{ e }}</span>
      </div></Panel
    >
  </div>
</template>
<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import { getDutyShifts, getDutyStats, type ShiftView, type DutyStats } from '@/api/duty'
const shifts = ref<ShiftView[]>([])
const stats = ref<DutyStats | null>(null)
const e = ref('')
const fromStr = ref('')
const toStr = ref('')
function today() {
  const d = new Date()
  return d.toISOString().slice(0, 10)
}
async function load() {
  fromStr.value = today()
  toStr.value = new Date(Date.now() + 6 * 86400000).toISOString().slice(0, 10)
}
async function refresh() {
  try {
    const [s, st] = await Promise.all([
      getDutyShifts(fromStr.value || undefined, toStr.value || undefined),
      getDutyStats(),
    ])
    shifts.value = s
    stats.value = st
  } catch (ex: unknown) {
    e.value = (ex as ErrorLike)?.message || String(ex)
  }
}
watch([fromStr, toStr], refresh)
onMounted(async () => {
  load()
  await refresh()
})
</script>
<style scoped>
.tbl {
  max-height: 420px;
  overflow-y: auto;
}
.tbl-head,
.tbl-row {
  display: flex;
  align-items: center;
  padding: 9px 6px;
  font-size: 12.5px;
}
.tbl-head {
  font-weight: 600;
  color: var(--muted);
  border-bottom: 2px solid var(--border);
  font-size: 12px;
}
.tbl-row {
  border-bottom: 1px solid var(--border-light, rgba(255, 255, 255, 0.04));
}
.col {
  flex-shrink: 0;
}
.w-duty-date {
  width: 120px;
}
.w-duty-type {
  width: 80px;
}
.w-duty-on {
  width: 100px;
}
.w-duty-bk {
  width: 100px;
}
.w-duty-note {
  flex: 1;
}
.fw {
  font-weight: 500;
}
.pill-tag {
  font-size: 10.5px;
  padding: 1px 8px;
  border-radius: 9px;
  background: var(--bg2);
}
.pill-tag.b {
  background: rgba(64, 150, 255, 0.12);
  color: var(--blue);
}
.empty {
  text-align: center;
  padding: 32px;
  color: var(--muted);
  font-size: 13px;
}
.flex {
  display: flex;
  align-items: center;
}
.between {
  justify-content: space-between;
}
.gap {
  gap: 8px;
}
.center {
  justify-content: center;
}
.d-inp {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg);
  color: var(--text);
  font-size: 12px;
}
</style>
