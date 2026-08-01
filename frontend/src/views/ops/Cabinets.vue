<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('资产管理') }} {{ tl('·') }} {{ tl('机柜管理') }}</h1>
      <span class="sub">{{ tl('机柜空间') }} / {{ tl('功耗监控') }} {{ tl('·') }} {{ tl('单柜温湿度与功耗趋势') }}</span>
      <span class="pill">R01~R12 {{ tl('·') }} {{ tl('共') }} {{ total }} {{ tl('台') }}</span>
    </div>

    <!-- 筛选 -->
    <div class="card toolbar">
      <select v-model="room" class="ipt" style="width:130px" @change="reload">
        <option value="">{{ tl('全部机房') }}</option>
        <option v-for="r in rooms" :key="r" :value="r">{{ r }}</option>
      </select>
      <input v-model.trim="kw" class="ipt" :placeholder="tl('搜索机柜编码')" style="width:200px" @keyup.enter="reload" />
      <button class="btn-sm primary" @click="reload">{{ tl('查询') }}</button>
      <span class="muted" style="margin-left:auto;font-size:11px">{{ tl('第') }} {{ page }}/{{ pages }} {{ tl('页') }} {{ tl('·') }} {{ total }} {{ tl('台') }}</span>
    </div>

    <!-- 列表 -->
    <div class="card scroll-x">
      <table>
        <thead>
          <tr>
            <th>{{ tl('机柜编码') }}</th><th>{{ tl('机房') }}</th><th>{{ tl('列') }}</th><th>U {{ tl('位使用') }}</th>
            <th>{{ tl('功耗') }} ({{ tl('当前') }}/{{ tl('额定') }})</th><th>{{ tl('负载率') }}</th><th>{{ tl('状态') }}</th><th>{{ tl('操作') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in items" :key="c.id" @click="openCab(c)" style="cursor:pointer">
            <td class="mono">{{ c.code }}</td>
            <td>{{ c.room }}</td>
            <td>{{ c.row }}</td>
            <td>
              <div class="flex gap6" style="align-items:center">
                <div class="progress" style="width:90px"><i :style="{ width: uPct(c) + '%', background: pctColor(uPct(c), 80, 95) }"></i></div>
                <span class="mono muted" style="font-size:10px">{{ c.u_used }}/{{ c.u_total }}</span>
              </div>
            </td>
            <td class="mono">{{ c.current_power_kw }}/{{ c.rated_power_kw }} kW</td>
            <td class="mono" :style="{ color: pctColor(pwrPct(c), 80, 95) }">{{ pwrPct(c) }}%</td>
            <td><span class="tag" :class="c.status === '正常' ? 'g' : c.status === '告警' ? 'r' : c.status === '高负载' ? 'a' : 'o'">{{ c.status }}</span></td>
            <td><button class="btn-sm" @click.stop="openCab(c)">{{ tl('遥测') }}</button></td>
          </tr>
          <tr v-if="!items.length"><td colspan="8" class="muted" style="text-align:center;padding:18px">{{ tl('无匹配机柜') }}</td></tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div v-if="pages > 1" class="flex center gap8" style="margin:10px 0">
      <button class="btn-sm" :disabled="page <= 1" @click="page--; reload()">{{ tl('上一页') }}</button>
      <span class="muted" style="font-size:11px">{{ page }} / {{ pages }}</span>
      <button class="btn-sm" :disabled="page >= pages" @click="page++; reload()">{{ tl('下一页') }}</button>
    </div>

    <!-- 机柜遥测弹窗 -->
    <teleport to="body">
      <div class="tf-mask" v-if="sel" @click.self="sel = null">
        <div class="tf-modal" style="width:min(760px,96vw)">
          <div class="tf-head">
            <div>
              <h3>{{ tl('机柜遥测') }} {{ tl('·') }} {{ sel.code }}</h3>
              <div class="muted" style="font-size:11px;margin-top:3px">{{ sel.room }} {{ tl('·') }} {{ sel.row }} {{ tl('列') }} {{ tl('·') }} U {{ tl('位') }} {{ sel.u_used }}/{{ sel.u_total }} {{ tl('·') }} {{ tl('额定') }} {{ sel.rated_power_kw }}kW</div>
            </div>
            <button class="tf-x" @click="sel = null">✕</button>
          </div>
          <div class="tf-body">
            <div v-if="cab" style="margin-top:4px">
              <TrendChart
                :metrics="cabTrendMetrics"
                :active="cabActive"
                :series="cabSeries"
                :unit-map="cabUnitMap"
                :loading="cabLoading"
                @select="cabActive = $event"
              />
            </div>
            <div v-else class="muted" style="text-align:center;padding:22px">{{ cabLoading ? "加载中…" : "暂无数据" }}</div>
          </div>
          <div class="tf-foot">
            <span class="muted" style="font-size:11px">{{ tl('数据源') }} /api/cabinets/{{ sel?.id }}/metrics {{ tl('·') }} {{ tl('近') }} 60min</span>
          </div>
        </div>
      </div>
    </teleport>

    <div class="footer-note">{{ tl('资产管理·机柜管理') }} {{ tl('—') }} {{ tl('接入后端') }} /api/cabinets</div>
  </div>
</template>

<script setup lang="ts">import { useI18n } from "vue-i18n";
const { t: tl } = useI18n();
import { computed, onBeforeUnmount, onMounted, ref } from "vue";import { getCabinetMetrics, getCabinets } from "@/api";
import TrendChart, { type TrendMetric } from "@/components/charts/TrendChart.vue";
import type { Cabinet, CabinetMetrics, MetricHistoryPoint, Paginated } from "@/types";

const items = ref<Cabinet[]>([]);
const total = ref(0);
const page = ref(1);
const pages = ref(1);
const room = ref("");
const kw = ref("");
const pageSize = 20;
const rooms = Array.from({ length: 12 }, (_, i) => `R${String(i + 1).padStart(2, "0")}`);

const uPct = (c: Cabinet) => Math.round((c.u_used / c.u_total) * 100);
const pwrPct = (c: Cabinet) => Math.round((c.current_power_kw / c.rated_power_kw) * 100);
function pctColor(pct: number, warn = 80, crit = 95) {
  return pct >= crit ? "var(--red)" : pct >= warn ? "var(--amber)" : "var(--green)";
}

async function reload() {
  try {
    const res: Paginated<Cabinet> = await getCabinets({ page: page.value, size: pageSize, room: room.value || undefined });
    items.value = res.items;
    total.value = res.total;
    pages.value = Math.max(1, Math.ceil(res.total / pageSize));
  } catch { /* 静态 mock 兜底 */ }
}

/* ---- 机柜遥测 ---- */
const sel = ref<Cabinet | null>(null);
const cab = ref<CabinetMetrics | null>(null);
const cabLoading = ref(false);
const cabActive = ref("temperature");
const cabUnitMap: Record<string, string> = { temperature: "℃", humidity: "%", power_kw: "kW" };

const cabTrendMetrics = computed<TrendMetric[]>(() => {
  const m = cab.value;
  if (!m) return [];
  const last = (a: { value: number }[] | null) => (a && a.length ? a[a.length - 1].value : undefined);
  return [
    { name: "temperature", label: tl('温度'), unit: "℃", latest: last(m.temperature) },
    { name: "humidity", label: tl('湿度'), unit: "%", latest: last(m.humidity) },
    { name: "power_kw", label: tl('功耗'), unit: "kW", latest: last(m.power_kw) },
  ];
});
const cabSeries = computed<Record<string, MetricHistoryPoint[]>>(() => {
  const m = cab.value;
  if (!m) return {} as Record<string, MetricHistoryPoint[]>;
  const toMH = (a: { ts: string; value: number }[] | null) => (a || []).map((p) => ({ ts: p.ts, value: p.value, quality: "good" as const }));
  const out: Record<string, MetricHistoryPoint[]> = {
    temperature: toMH(m.temperature),
    humidity: toMH(m.humidity),
    power_kw: toMH(m.power_kw),
  };
  return out;
});

async function openCab(c: Cabinet) {
  sel.value = c;
  cab.value = null;
  cabLoading.value = true;
  cabActive.value = "temperature";
  try {
    cab.value = await getCabinetMetrics(c.id, { minutes: 60, step_sec: 60 });
  } catch { /* mock 兜底 */ }
  finally { cabLoading.value = false; }
}

let timer = 0;
onMounted(() => { reload(); timer = window.setInterval(reload, Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 15000)); });
onBeforeUnmount(() => clearInterval(timer));
</script>

<style scoped>
.toolbar { display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 8px; flex-wrap: wrap; }
.ipt { background: var(--bg2); border: 1px solid var(--line); border-radius: 7px; color: var(--txt); padding: 6px 10px; font-size: 12px; outline: none; }
.ipt:focus { border-color: var(--cyan); }
.btn-sm { background: var(--bg2); border: 1px solid var(--line); color: var(--txt); padding: 4px 10px; border-radius: 6px; cursor: pointer; font-size: 11px; }
.btn-sm:hover { border-color: var(--cyan); }
.btn-sm.primary { background: linear-gradient(90deg, var(--cyan), var(--blue)); color: #04121f; border-color: transparent; font-weight: 700; }
.btn-sm.primary:disabled { opacity: .6; cursor: default; }
.flex { display: flex; align-items: center; }
.gap6 { gap: 6px; }
.center { justify-content: center; }
.progress { height: 6px; background: #13233f; border-radius: 4px; overflow: hidden; }
.progress i { display: block; height: 100%; border-radius: 4px; }
</style>
