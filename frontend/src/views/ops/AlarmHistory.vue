<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('智能运营') }} {{ tl('·') }} {{ tl('告警历史与持久化') }}</h1>
      <span class="sub">{{ tl('时间窗查询') }} {{ tl('·') }} {{ tl('确认') }} / {{ tl('闭环') }} {{ tl('·') }} {{ tl('收敛与处置统计') }}</span>
    </div>

    <!-- 统计 -->
    <div class="grid cols-5" v-if="data">
      <div class="card"><div class="ct">24h {{ tl('总告警') }}</div><div class="cv">{{ data.stats.total24h }}<small>{{ tl('条') }}</small></div></div>
      <div class="card"><div class="ct">24h {{ tl('活跃') }}</div><div class="cv" style="color:var(--red)">{{ data.stats.active24h }}<small>{{ tl('条') }}</small></div></div>
      <div class="card"><div class="ct">24h {{ tl('已闭环') }}</div><div class="cv" style="color:var(--green)">{{ data.stats.resolved24h }}<small>{{ tl('条') }}</small></div></div>
      <div class="card"><div class="ct">MTTA</div><div class="cv">{{ data.stats.mttaMin }}<small>min</small></div></div>
      <div class="card"><div class="ct">MTTR</div><div class="cv">{{ data.stats.mttrMin }}<small>min</small></div></div>
    </div>

    <!-- 筛选 -->
    <div class="card toolbar">
      <select v-model="fSys" class="ipt" style="width:160px" @change="onFilter">
        <option value="">{{ tl('全部系统') }}</option>
        <option v-for="s in sysOptions" :key="s" :value="s">{{ s }}</option>
      </select>
      <select v-model="fLv" class="ipt" style="width:110px" @change="onFilter">
        <option value="">{{ tl('全部级别') }}</option>
        <option value="crit">crit</option><option value="warn">warn</option><option value="info">info</option>
      </select>
      <select v-model="fState" class="ipt" style="width:120px" @change="onFilter">
        <option value="">{{ tl('全部状态') }}</option>
        <option value="active">{{ tl('活跃') }}</option>
        <option value="acknowledged">{{ tl('已确认') }}</option>
        <option value="resolved">{{ tl('已闭环') }}</option>
        <option value="suppressed">{{ tl('已抑制') }}</option>
      </select>
      <input v-model.trim="kw" class="ipt" :placeholder="tl('搜索规则 / 描述')" style="width:220px" @keyup.enter="onFilter" />
      <button class="btn-sm primary" @click="onFilter">{{ tl('查询') }}</button>
      <span class="muted" style="margin-left:auto;font-size:11px">{{ tl('共') }} {{ data?.total ?? 0 }} {{ tl('条') }} {{ tl('·') }} {{ tl('当前页') }} {{ data?.items.length ?? 0 }} {{ tl('条') }}</span>
    </div>

    <!-- 列表 -->
    <div class="card scroll-x">
      <table>
        <thead>
          <tr>
            <th>{{ tl('触发时间') }}</th><th>{{ tl('级别') }}</th><th>{{ tl('系统') }}</th><th>{{ tl('规则') }} / {{ tl('描述') }}</th>
            <th>{{ tl('实测') }} / {{ tl('阈值') }}</th><th>{{ tl('状态') }}</th><th style="min-width:150px">{{ tl('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="e in data?.items" :key="e.id" :class="{ 'row-crit': e.lv === 'crit' && e.state !== 'resolved' }">
            <td class="mono">{{ fmt(e.triggeredAt) }}</td>
            <td><span class="tag" :class="e.lv === 'crit' ? 'r' : e.lv === 'warn' ? 'a' : 'g'">{{ e.lv }}</span></td>
            <td>{{ e.sys }}</td>
            <td>
              <div style="font-weight:600">{{ e.ruleName }}</div>
              <div class="muted" style="font-size:11px">{{ e.desc }}</div>
            </td>
            <td class="mono">{{ e.value }}{{ e.unit || "" }} / {{ e.threshold }}{{ e.unit || "" }}</td>
            <td><span class="tag" :class="stateTag(e.state)">{{ stateText(e.state) }}</span></td>
            <td>
              <button class="btn-sm" v-if="e.state === 'active'" @click="ack(e)">{{ tl('确认') }}</button>
              <button class="btn-sm primary" v-if="e.state === 'active' || e.state === 'acknowledged'" style="margin-left:4px" @click="resolve(e)">{{ tl('闭环') }}</button>
              <span class="muted" v-if="e.state === 'resolved'" style="font-size:11px">{{ e.resolvedBy }}{{ e.autoResolved ? "·自动" : "" }}</span>
              <span class="muted" v-if="e.state === 'suppressed'" style="font-size:11px">{{ tl('已抑制') }}</span>
            </td>
          </tr>
          <tr v-if="!data?.items.length"><td colspan="7" class="muted" style="text-align:center;padding:18px">{{ tl('无匹配告警') }}</td></tr>
        </tbody>
      </table>
      <Pagination v-if="data" :total="data.total" :page="page" :size="size" @change="onPage" @size-change="onSize" />
    </div>

    <div class="footer-note">{{ tl('智能运营·告警历史') }} {{ tl('—') }} {{ tl('接入后端') }} /api/alarm-history ({{ tl('确认') }} / {{ tl('闭环') }} {{ tl('写操作在后端不可达时本地生效') }})</div>
  </div>
</template>

<script setup lang="ts">import { useI18n } from "vue-i18n";
const { t: tl } = useI18n();
import { computed, onBeforeUnmount, onMounted, ref } from "vue";import { acknowledgeAlarm, getAlarmHistory, resolveAlarm } from "@/api";
import type { AlarmEvent, AlarmHistoryResponse } from "@/types";
import Pagination from "@/components/Pagination.vue";

const data = ref<AlarmHistoryResponse | null>(null);
const fSys = ref("");
const fLv = ref("");
const fState = ref("");
const page = ref(1);
const size = ref(50);
const kw = ref("");
const operator = "值班员";

const sysOptions = computed(() => (data.value ? [...new Set(data.value.items.map((e) => e.sys))] : []));
const stateTag = (s: string) =>
  s === "active" ? "r" : s === "acknowledged" ? "a" : s === "resolved" ? "g" : "o";
const stateText = (s: string) =>
  ({ active: "活跃", acknowledged: "已确认", resolved: "已闭环", suppressed: "已抑制" } as Record<string, string>)[s] ?? s;

function fmt(s?: string) {
  if (!s) return "—";
  return new Date(s).toLocaleString("zh-CN", { hour12: false });
}

function patchLocal(id: string, patch: Partial<AlarmEvent>) {
  const e = data.value?.items.find((x) => x.id === id);
  if (e) Object.assign(e, patch);
}
async function ack(e: AlarmEvent) {
  patchLocal(e.id, { state: "acknowledged", acknowledgedAt: new Date().toISOString(), acknowledgedBy: operator });
  try { await acknowledgeAlarm(e.id, operator); } catch { /* 后端未就绪 */ }
}
async function resolve(e: AlarmEvent) {
  patchLocal(e.id, {
    state: "resolved", resolvedAt: new Date().toISOString(), resolvedBy: operator,
    note: "已处置并闭环", autoResolved: false,
  });
  try { await resolveAlarm(e.id, operator, "已处置并闭环"); } catch { /* 后端未就绪 */ }
}

async function reload() {
  try {
    data.value = await getAlarmHistory({
      sys: fSys.value || undefined,
      lv: fLv.value || undefined,
      state: fState.value || undefined,
      page: page.value, limit: size.value,
    });
  } catch { /* 静态 mock 兜底 */ }
}

function onPage(p: number) { page.value = p; reload(); }
function onSize(s: number) { size.value = s; page.value = 1; reload(); }
function onFilter() { page.value = 1; reload(); }

let timer = 0;
onMounted(() => { reload(); timer = window.setInterval(reload, Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 5000)); });
onBeforeUnmount(() => clearInterval(timer));
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 8px; flex-wrap: wrap; }
.ipt { background: var(--bg2); border: 1px solid var(--line); border-radius: 7px; color: var(--txt); padding: 6px 10px; font-size: 12px; outline: none; }
.ipt:focus { border-color: var(--cyan); }
.btn-sm { background: var(--bg2); border: 1px solid var(--line); color: var(--txt); padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 11px; }
.btn-sm:hover { border-color: var(--cyan); }
.btn-sm.primary { background: linear-gradient(90deg, var(--cyan), var(--blue)); color: #04121f; border-color: transparent; font-weight: 700; }
.row-crit { background: rgba(242, 63, 63, .05); }
</style>
