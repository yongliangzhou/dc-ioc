<template>
  <div>
    <div class="view-head">
      <h1>{{ viewMode === "campus" ? $t("campus.title") : "IOC 驾驶舱" }}</h1>
      <span class="sub" v-if="viewMode === 'single'">华东-杭州 EC1 数据中心</span>
      <span class="pill">L1 全局态势</span>
      <div class="view-toggle">
        <button :class="{ active: viewMode === 'single' }" @click="switchView('single')">当前园区</button>
        <button :class="{ active: viewMode === 'campus' }" @click="switchView('campus')">{{ $t("campus.switchCampus") }}</button>
      </div>
    </div>

    <!-- ===== 多 DC 聚合视图 ===== -->
    <template v-if="viewMode === 'campus'">
      <p class="subtitle">{{ $t("campus.subtitle") }}</p>

      <!-- 园区概览卡片 -->
      <div class="section-title" style="margin-top:0">{{ $t("campus.campusList") }}</div>
      <div class="grid cols-4">
        <div v-for="c in campuses" :key="c.id" class="card campus-card" :class="'status-' + c.status">
          <div class="camp-head">
            <span class="camp-name">{{ c.name }}</span>
            <span class="camp-status" :class="c.status">
              {{ c.status === "online" ? $t("campus.statusOnline") : c.status === "degraded" ? $t("campus.statusDegraded") : $t("campus.statusOffline") }}
            </span>
          </div>
          <div class="camp-body">
            <div class="camp-kv"><span class="camp-k">{{ $t("campus.deviceCount") }}</span><span class="camp-v">{{ c.online_devices }}/{{ c.total_devices }} <small>({{ c.online_rate }}%)</small></span></div>
            <div class="camp-kv"><span class="camp-k">{{ $t("campus.pueShort") }}</span><span class="camp-v" :style="{ color: c.pue > 1.35 ? '#e53935' : c.pue > 1.25 ? '#fdd835' : '#43a047' }">{{ c.pue }}</span></div>
            <div class="camp-kv"><span class="camp-k">{{ $t("campus.itLoad") }}</span><span class="camp-v">{{ c.it_load_mw }} MW</span></div>
            <div class="camp-kv"><span class="camp-k">{{ $t("campus.totalLoad") }}</span><span class="camp-v">{{ c.total_load_mw }} MW</span></div>
            <div class="camp-kv"><span class="camp-k">{{ $t("campus.alarms") }}</span>
              <span class="camp-v">
                <span :style="{ color: c.alerts_crit > 0 ? '#e53935' : '#aaa' }">{{ c.alerts_crit }} 紧急</span>
                <span style="margin-left:8px" :style="{ color: c.alerts_warn > 0 ? '#ffb020' : '#aaa' }">{{ c.alerts_warn }} 重要</span>
              </span>
            </div>
            <div class="camp-kv"><span class="camp-k">{{ $t("campus.availability") }}</span><span class="camp-v" :style="{ color: c.availability >= 99.99 ? '#43a047' : '#ffb020' }">{{ c.availability }}%</span></div>
          </div>
        </div>
      </div>

      <!-- 跨园区 KPI 对比 -->
      <div class="section-title">{{ $t("campus.kpiComparison") }}</div>
      <div class="grid cols-2" style="margin-bottom:16px">
        <div v-for="cmp in comparisons" :key="cmp.metric" class="card">
          <div class="ct">{{ cmp.label }}
            <span v-if="cmp.unit" style="font-weight:400;color:#888;font-size:0.8rem">({{ cmp.unit }})</span>
          </div>
          <div style="height:200px" :ref="el => renderCmpChart(el as HTMLElement, cmp)"></div>
          <div class="cmp-best">
            <span style="color:#43a047">{{ $t("campus.best") }}: {{ cmp.best }}</span>
            <span style="color:#e53935;margin-left:12px">{{ $t("campus.worst") }}: {{ cmp.worst }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- ===== 全局 KPI (可下钻) ===== -->
    <template v-if="viewMode === 'single'">
    <div class="grid cols-6">
      <div v-for="k in kpis" :key="k.key" class="card kpi" @click="openDrill(k.key)">
        <div class="ct">{{ k.title }}</div>
        <div class="cv" :style="k.color ? { color: k.color } : {}">{{ k.value }}<small>{{ k.unit }}</small></div>
        <div class="cbar"><i :style="{ width: k.bar + '%', background: k.color || 'var(--cyan)' }"></i></div>
        <div class="drill-hint">⇲ 下钻</div>
      </div>
    </div>

    <!-- ===== 四大业务域健康度 ===== -->
    <div class="section-title">四大业务域健康度</div>
    <div class="grid cols-4">
      <div v-for="d in domains" :key="d.name" class="card">
        <div class="ct">{{ d.ico }} {{ d.name }}</div>
        <div class="flex center gap12">
          <BaseChart :option="ringOption(d.pct, d.color)" height="86px" width="86px" />
          <div><div class="cv" style="font-size:18px">{{ d.state }}</div><div class="muted" style="font-size:11px">{{ d.desc }}</div></div>
        </div>
        <div class="kvs" style="margin-top:10px">
          <span class="k">{{ d.k1 }}</span><span class="v">{{ d.v1 }}</span>
          <span class="k">{{ d.k2 }}</span><span class="v" style="font-size:11px">{{ d.v2 }}</span>
        </div>
      </div>
    </div>

    <!-- ===== 园区态势与实时联动告警 ===== -->
    <div class="section-title">园区态势与实时联动告警</div>
    <div class="twin">
      <div class="card"><div class="ct">园区平面 · 楼栋/包间态势</div>
        <div class="map">
          <div v-for="(r, i) in rooms" :key="r.id" class="mhq"
            :style="{ left: (8 + (i % 6) * 15.5) + '%', top: (i < 6 ? 18 : 58) + '%', borderColor: r.hot ? 'var(--amber)' : 'var(--cyan)', boxShadow: r.hot ? '0 0 14px rgba(255,176,32,.4)' : '0 0 14px rgba(34,227,255,.35)' }"
            :title="`${r.id} 机柜 ${r.used}/300`">{{ r.id }}</div>
          <div style="position:absolute;right:10px;bottom:8px;font-size:10px;color:var(--txt3)">A栋 / B栋 · 12 包间 · 3600 机柜</div>
        </div>
        <div class="legend"><span><i style="background:var(--cyan)"></i>正常</span><span><i style="background:var(--amber)"></i>温度关注</span><span><i style="background:var(--red)"></i>告警</span></div>
      </div>

      <!-- 实时联动告警面板: 直接消费响应式 realtimeLinkage.active -->
      <div class="card">
        <div class="ct">实时联动告警 <span class="rt-dot" :class="{ live: realtimeLinkage.running }"></span>
          <span class="tag r">{{ liveCrit }} 紧急</span> <span class="tag a">{{ liveWarn }} 重要</span>
          <span class="rt-count">{{ realtimeLinkage.active.length }} 活动</span>
        </div>
        <div class="live-note muted">越限联动引擎实时生成 · 遥测持续越限自动推送</div>
        <div v-if="realtimeLinkage.active.length" style="max-height:248px;overflow-y:auto">
          <div v-for="a in realtimeLinkage.active" :key="a.id" class="alarm rt">
            <span class="lv" :class="a.lv">{{ lvText(a.lv) }}</span>
            <div class="txt">{{ a.desc }}
              <div class="meta">{{ a.sys }} · {{ a.deviceId }} · {{ a.value }}{{ a.unit }} / 阈值 {{ a.threshold }}{{ a.unit }} · {{ a.ts }} · {{ a.state }}</div>
            </div>
            <div class="acts">
              <button class="mini" :disabled="a.state !== '待确认'" @click="realtimeLinkage.ack(a.id)">确认</button>
              <button class="mini danger" @click="realtimeLinkage.resolve(a.id)">关单</button>
            </div>
          </div>
        </div>
        <div v-else class="muted center" style="padding:26px 0">暂无实时联动告警 · 联动引擎运行中（遥测越限将自动生成）</div>
      </div>
    </div>

    <!-- ===== 关键趋势 ===== -->
    <div class="section-title">关键趋势</div>
    <div class="grid cols-3">
      <div class="card"><div class="ct">冷冻水供水温度 (℃) · 48 点</div><BaseChart :option="tempOpt" height="120px" />
        <div class="flex between muted" style="font-size:10px;margin-top:4px"><span>设定 15.0℃</span><span>当前 15.2℃</span></div></div>
      <div class="card"><div class="ct">冷源系统负载率 PLR (%)</div><BaseChart :option="plrOpt" height="120px" />
        <div class="flex between muted" style="font-size:10px;margin-top:4px"><span>加机线 85%</span><span>当前 68%</span></div></div>
      <div class="card"><div class="ct">PUE 30 日趋势</div><BaseChart :option="pueOpt" height="120px" />
        <div class="flex between muted" style="font-size:10px;margin-top:4px"><span>目标 ≤1.30</span><span>今日 {{ ov?.pue?.toFixed(3) ?? "-" }}</span></div></div>
    </div>

    <div class="footer-note">数据域覆盖: 暖通(冷源/末端) · 电力(10KV/0.4KV/柴发/燃油/电池) · 安防消防(视频/门禁/防入侵/消防) · 智能运营(孪生/容量/告警/电量预测) · 运维作业 — Vue3 + ECharts</div>

    <!-- ===== KPI 下钻面板 ===== -->
    <teleport to="body">
      <div v-if="drillOpen" class="dd-mask" @click.self="drillOpen = false">
        <div class="dd-modal">
          <div class="dd-head">
            <div><h3>{{ drill.title }}</h3><div class="dd-bench">{{ drill.benchmark }}</div></div>
            <button class="dm-x" @click="drillOpen = false">✕</button>
          </div>
          <div class="dd-body">
            <div class="dd-headline" :style="drill.color ? { color: drill.color } : {}">{{ drill.headline }}<small>{{ drill.unit }}</small></div>
            <div v-if="drill.bars.length" class="dd-stack">
              <div class="dd-stack-bar">
                <span v-for="(b, i) in drill.bars" :key="i" class="seg" :style="{ width: b.pct + '%', background: b.color }" :title="`${b.label} ${b.value}${b.unit} (${b.pct}%)`"></span>
              </div>
            </div>
            <div class="dd-bars">
              <div v-for="(b, i) in drill.bars" :key="i" class="dd-row">
                <span class="dd-k"><i class="dot" :style="{ background: b.color }"></i>{{ b.label }}</span>
                <span class="dd-v">{{ b.value }}<small>{{ b.unit }}</small></span>
                <span class="dd-p">{{ b.pct }}%</span>
              </div>
            </div>
            <div v-if="drill.notes.length" class="dd-notes">
              <div v-for="(n, i) in drill.notes" :key="i" class="dd-note">· {{ n }}</div>
            </div>
            <div v-if="drill.liveBySys.length" class="dd-live">
              <div class="dd-live-title">实时联动告警按系统分布 (当前 {{ realtimeLinkage.active.length }} 条)</div>
              <div v-for="(s, i) in drill.liveBySys" :key="i" class="dd-row">
                <span class="dd-k"><i class="dot" style="background:var(--amber)"></i>{{ s.sys }}</span>
                <span class="dd-v">{{ s.count }}<small>条</small></span>
                <span class="dd-p">{{ totalActive ? Math.round(s.count / totalActive * 100) : 0 }}%</span>
              </div>
            </div>
          </div>
          <div class="dd-foot">
            <button class="dm-btn" @click="drillOpen = false">关闭</button>
          </div>
        </div>
      </div>
    </teleport>
    </template><!-- /viewMode single -->
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { useRoute, useRouter } from "vue-router";
import BaseChart from "@/components/charts/BaseChart.vue";
import { ringOption, lineOption } from "@/components/charts/options";
import { getCampuses, getCampusComparison, getDashboardOverview } from "@/api";
import type { CampusComparisonItem, DCCampus, DashboardOverview } from "@/types";
import * as echarts from "echarts";
import { realtimeLinkage } from "@/engine/realtimeLinkage";

const { t } = useI18n();
const route = useRoute();
const router = useRouter();

const ov = ref<DashboardOverview | null>(null);
const rnd = (a: number, b: number, f = 1) => +(a + Math.random() * (b - a)).toFixed(f);

/* --------- 视图模式 --------- */
const viewMode = ref<"single" | "campus">("single");
function syncViewFromQuery() {
  // 由导航/URL 进入时读取 ?view=campus 参数, 否则默认单园区
  viewMode.value = route.query.view === "campus" ? "campus" : "single";
}
function switchView(mode: "single" | "campus") {
  viewMode.value = mode;
  // 同步到 URL, 便于导航/刷新保持当前视图
  router.replace({
    query: { ...route.query, view: mode === "campus" ? "campus" : undefined },
  });
}
watch(() => route.query.view, syncViewFromQuery);

/* --------- 多 DC 数据 --------- */
const campuses = ref<DCCampus[]>([]);
const comparisons = ref<CampusComparisonItem[]>([]);

async function loadCampuses() {
  try {
    const [cRes, cmpRes] = await Promise.all([getCampuses(), getCampusComparison()]);
    campuses.value = cRes.campuses;
    comparisons.value = cmpRes.comparisons;
  } catch { /* ignore */ }
}

const cmpCharts: Map<string, echarts.ECharts> = new Map();
function renderCmpChart(el: HTMLElement, cmp: CampusComparisonItem) {
  if (!el || el.tagName === "DIV") {
    setTimeout(() => renderCmpChart(el, cmp), 50);
    return;
  }
  let chart = cmpCharts.get(cmp.metric);
  if (!chart) {
    chart = echarts.init(el);
    cmpCharts.set(cmp.metric, chart);
  }
  const names = cmp.data.map((d) => d.campus);
  const vals = cmp.data.map((d) => d.value);
  const isBetterLow = cmp.metric === "pue" || cmp.metric === "alarms";
  const bestVal = isBetterLow ? Math.min(...vals) : Math.max(...vals);
  chart.setOption({
    tooltip: { trigger: "axis" },
    grid: { top: 10, left: 40, right: 20, bottom: 25 },
    xAxis: { type: "category", axisLabel: { color: "#ddd" }, data: names },
    yAxis: { type: "value", name: cmp.unit, nameTextStyle: { color: "#888" }, axisLabel: { color: "#aaa" } },
    series: [{
      type: "bar",
      data: vals.map((v) => ({
        value: v,
        itemStyle: { color: v === bestVal ? "#43a047" : "#42a5f5" },
        borderRadius: [4, 4, 0, 0],
      })),
      label: { show: true, position: "top", color: "#aaa", fontSize: 11, formatter: (p: any) => p.value.toFixed(isBetterLow ? 2 : 1) },
    }],
  });
}

/* 四大业务域 */
const domains = [
  { ico: "❄", name: "暖通监控系统", pct: 96, color: "#22e3ff", state: "健康", desc: "冷源 2+1 运行 · 末端 78/96", k1: "供水温度", v1: "15.2 ℃", k2: "运行模式", v2: "部分自然冷" },
  { ico: "⚡", name: "电力监控系统", pct: 99, color: "#2bd47a", state: "健康", desc: "双路市电正常 · 柴发 7 备用", k1: "10KV 进线", v1: "2/2 合闸", k2: "UPS/HVDC", v2: "全部正常" },
  { ico: "🛡", name: "物理安防与消防", pct: 97, color: "#ffb020", state: "关注", desc: "1 条门磁异常处理中", k1: "视频在线", v1: "482/486", k2: "消防主机", v2: "正常" },
  { ico: "🧠", name: "智能运营平台", pct: 99, color: "#9b6bff", state: "在线", desc: "Raptor/方舟 · 点位 12.85 万", k1: "告警收敛率", v1: "95.1%", k2: "AI 节能", v2: "-3.1%" },
];

/* 包间态势 */
const rooms = Array.from({ length: 12 }, (_, i) => ({
  id: `R${String(i + 1).padStart(2, "0")}`, used: rnd(240, 296, 0), hot: i === 3 || i === 8,
}));

const lvText = (lv: string) => (lv === "crit" ? "紧急" : lv === "warn" ? "重要" : "提示");

/* ===== 实时联动告警面板驱动数据 ===== */
const liveCrit = computed(() => realtimeLinkage.active.filter((a) => a.lv === "crit").length);
const liveWarn = computed(() => realtimeLinkage.active.filter((a) => a.lv === "warn").length);
const totalActive = computed(() => realtimeLinkage.active.length);
const liveBySys = computed(() => {
  const m: Record<string, number> = {};
  for (const a of realtimeLinkage.active) m[a.sys] = (m[a.sys] ?? 0) + 1;
  return Object.entries(m).map(([sys, count]) => ({ sys, count }));
});

/* ===== KPI 卡片 (可点击下钻) ===== */
const kpis = computed(() => {
  const o = ov.value;
  const pue = o?.pue != null ? o.pue.toFixed(3) : "-";
  const it = o?.it_load_mw ?? null;
  const total = o?.total_load_mw ?? null;
  const cool = o?.cool_load_mw ?? null;
  const online = o?.online_rate ?? null;
  const wue = o?.wue ?? null;
  const pct = (v: number | null, max: number) => (v == null ? 0 : Math.min(100, Math.round((v / max) * 100)));
  return [
    { key: "pue", title: "PUE (实时)", value: pue, unit: "", color: "var(--cyan)", bar: pct(o?.pue ?? null, 1.5) },
    { key: "it", title: "IT 负载", value: it != null ? it : "-", unit: it != null ? "MW" : "", color: "var(--green)", bar: pct(it, 36) },
    { key: "total", title: "总负载", value: total != null ? total : "-", unit: total != null ? "MW" : "", color: "", bar: pct(total, 40) },
    { key: "cool", title: "制冷负载", value: cool != null ? cool : "-", unit: cool != null ? "MW" : "", color: "var(--amber)", bar: pct(cool, 12) },
    { key: "online", title: "设备在线率", value: online != null ? online : "-", unit: online != null ? "%" : "", color: "var(--green)", bar: online ?? 0 },
    { key: "wue", title: "WUE", value: wue != null ? wue : "-", unit: wue != null ? "L/kWh" : "", color: "", bar: pct(wue, 3) },
  ];
});

/* ===== KPI 下钻数据 ===== */
interface DrillBar { label: string; value: number | string; unit: string; pct: number; color: string }
interface DrillData {
  title: string; headline: string; unit: string; color: string; benchmark: string;
  bars: DrillBar[]; notes: string[]; liveBySys: { sys: string; count: number }[];
}
function powerBreakdown(): DrillBar[] {
  const o = ov.value;
  const it = o?.it_load_mw ?? 0;
  const cool = o?.cool_load_mw ?? 0;
  const total = o?.total_load_mw ?? (it + cool || 1);
  const other = Math.max(0, total - it - cool);
  const p = (v: number) => (total > 0 ? +(v / total * 100).toFixed(1) : 0);
  return [
    { label: "IT 设备", value: +it.toFixed(1), unit: "MW", pct: p(it), color: "var(--cyan)" },
    { label: "制冷系统", value: +cool.toFixed(1), unit: "MW", pct: p(cool), color: "var(--green)" },
    { label: "供配电及其他", value: +other.toFixed(1), unit: "MW", pct: p(other), color: "var(--amber)" },
  ];
}
function buildDrill(key: string): DrillData {
  const o = ov.value;
  const empty: DrillData = { title: "下钻", headline: "—", unit: "", color: "", benchmark: "", bars: [], notes: ["数据加载中…"], liveBySys: [] };
  if (!o) return empty;
  switch (key) {
    case "pue":
      return {
        title: "PUE 能效下钻", headline: o.pue.toFixed(3), unit: "", color: "var(--cyan)",
        benchmark: "目标 ≤ 1.30（设计值 1.247）",
        bars: powerBreakdown(),
        notes: [
          `WUE：${o.wue ?? "-"} L/kWh`,
          `自由冷却时长：${o.free_cool_hours ?? "-"} h`,
          `系统可用性：${o.availability != null ? o.availability + "%" : "-"}`,
          `今日告警：${o.today_alarms ?? "-"} 条（紧急 ${o.alarms?.crit ?? 0} / 重要 ${o.alarms?.warn ?? 0}）`,
        ], liveBySys: [],
      };
    case "it":
      return {
        title: "IT 负载下钻", headline: (o.it_load_mw ?? 0).toFixed(1), unit: "MW", color: "var(--green)",
        benchmark: "设计容量 36 MW",
        bars: powerBreakdown(),
        notes: [
          `PUE = ${(o.total_load_mw && o.it_load_mw) ? (o.total_load_mw / o.it_load_mw).toFixed(3) : "-"}`,
          `IT 占比：${o.total_load_mw ? Math.round((o.it_load_mw ?? 0) / o.total_load_mw * 100) : "-"}%`,
        ], liveBySys: [],
      };
    case "total":
      return {
        title: "总负载下钻", headline: (o.total_load_mw ?? 0).toFixed(1), unit: "MW", color: "",
        benchmark: "供电容量 40 MW",
        bars: powerBreakdown(),
        notes: [`IT 负载：${o.it_load_mw ?? "-"} MW · 制冷负载：${o.cool_load_mw ?? "-"} MW`], liveBySys: [],
      };
    case "cool":
      return {
        title: "制冷负载下钻", headline: (o.cool_load_mw ?? 0).toFixed(1), unit: "MW", color: "var(--amber)",
        benchmark: "制冷容量 40 MW",
        bars: powerBreakdown(),
        notes: [`制冷负载率：${o.total_load_mw ? Math.round((o.cool_load_mw ?? 0) / o.total_load_mw * 100) : "-"}%`], liveBySys: [],
      };
    case "online":
      return {
        title: "设备在线率下钻", headline: (o.online_rate ?? 0).toString(), unit: "%", color: "var(--green)",
        benchmark: "目标 ≥ 99.9%",
        bars: [
          { label: "在线设备", value: o.online_devices ?? 0, unit: "台", pct: o.online_rate ?? 0, color: "var(--green)" },
          { label: "离线设备", value: Math.max(0, (o.total_devices ?? 0) - (o.online_devices ?? 0)), unit: "台", pct: 100 - (o.online_rate ?? 0), color: "var(--red)" },
        ],
        notes: [`设备总数：${o.total_devices ?? "-"} 台 · 在线 ${o.online_devices ?? "-"} 台`],
        liveBySys: liveBySys.value,
      };
    case "wue":
    default:
      return {
        title: "WUE 下钻", headline: (o.wue ?? 0).toString(), unit: "L/kWh", color: "",
        benchmark: "目标 ≤ 1.6 L/kWh",
        bars: [{ label: "WUE", value: o.wue ?? 0, unit: "L/kWh", pct: o.wue ? Math.min(100, +(o.wue / 3 * 100).toFixed(1)) : 0, color: "var(--cyan)" }],
        notes: [`PUE：${o.pue?.toFixed(3) ?? "-"} · 自由冷却时长：${o.free_cool_hours ?? "-"} h`], liveBySys: [],
      };
  }
}

const drillOpen = ref(false);
const drillKey = ref("pue");
const drill = computed(() => buildDrill(drillKey.value));
function openDrill(k: string) { drillKey.value = k; drillOpen.value = true; }

/* 趋势图 (computed: 数据固定, 但依赖 themeMode 在主题切换时重新取色) */
const pts48 = Array.from({ length: 48 }, (_, i) => `${i}`);
const tempData = pts48.map(() => rnd(14.6, 15.8));
const plrData = pts48.map(() => rnd(55, 80, 0));
const days30 = Array.from({ length: 30 }, (_, i) => `${i + 1}`);
const pueData = days30.map(() => rnd(1.22, 1.31, 3));
const tempOpt = computed(() => lineOption(pts48, [{ name: "供水温度", data: tempData, area: true }]));
const plrOpt = computed(() => lineOption(pts48, [{ name: "PLR", data: plrData, color: "#9b6bff", area: true }]));
const pueOpt = computed(() => lineOption(days30, [{ name: "PUE", data: pueData, color: "#2bd47a", area: true }]));

let timer = 0;
async function load() { try { ov.value = await getDashboardOverview(); } catch (e) { } }
onMounted(() => {
  syncViewFromQuery();
  load();
  loadCampuses(); // 预加载多DC数据
  // 确保越限联动引擎运行（DefaultLayout 已启动则幂等）
  realtimeLinkage.start(Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000));
  timer = window.setInterval(load, Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000));
});
onBeforeUnmount(() => {
  clearInterval(timer);
  // 引擎由 DefaultLayout 统一生命周期管理, 此处不停止
});
</script>

<style scoped>
.kpi { cursor: pointer; position: relative; transition: transform .12s, box-shadow .12s, border-color .12s; }
.kpi:hover { transform: translateY(-2px); border-color: var(--cyan, #22e3ff); box-shadow: 0 0 0 1px rgba(34,227,255,.35), 0 8px 22px rgba(0,0,0,.35); }
.drill-hint { position: absolute; right: 10px; bottom: 8px; font-size: 10px; color: var(--txt3, #5a6380); opacity: 0; transition: opacity .12s; }
.kpi:hover .drill-hint { opacity: 1; }

.rt-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: var(--txt3, #5a6380); margin-left: 2px; vertical-align: middle; }
.rt-dot.live { background: var(--amber, #ffb020); box-shadow: 0 0 8px var(--amber, #ffb020); animation: rtPulse 1.4s infinite; }
@keyframes rtPulse { 0%,100% { opacity: 1; } 50% { opacity: .35; } }
.rt-count { margin-left: auto; font-size: 11px; color: var(--txt3, #5a6380); }
.live-note { font-size: 10.5px; margin: -4px 0 8px; }

.alarm.rt { align-items: flex-start; }
.alarm .acts { display: flex; flex-direction: column; gap: 4px; margin-left: 6px; }
.mini { font-size: 11px; padding: 3px 9px; border-radius: 6px; cursor: pointer; background: transparent; border: 1px solid var(--line, rgba(255,255,255,.18)); color: var(--txt2, #8892b0); }
.mini:hover:not(:disabled) { border-color: var(--cyan, #22e3ff); color: var(--cyan, #22e3ff); }
.mini.danger:hover:not(:disabled) { border-color: var(--red, #ff5a6a); color: var(--red, #ff5a6a); }
.mini:disabled { opacity: .4; cursor: not-allowed; }

/* ===== KPI 下钻面板 ===== */
.dd-mask { position: fixed; inset: 0; z-index: 1100; background: rgba(4,8,20,.66); display: flex; align-items: center; justify-content: center; backdrop-filter: blur(3px); }
.dd-modal { width: 480px; max-width: 94vw; max-height: 88vh; overflow: auto; background: var(--panel, #131a30); border: 1px solid var(--line, rgba(255,255,255,.1)); border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,.5); }
.dd-head { display: flex; align-items: flex-start; justify-content: space-between; padding: 16px 18px; border-bottom: 1px solid var(--line, rgba(255,255,255,.1)); }
.dd-head h3 { margin: 0; font-size: 15px; color: var(--cyan, #22e3ff); }
.dd-bench { font-size: 11px; color: var(--txt3, #5a6380); margin-top: 3px; }
.dm-x { background: none; border: none; color: var(--txt2, #8892b0); font-size: 15px; cursor: pointer; }
.dd-body { padding: 16px 18px; }
.dd-headline { font-size: 34px; font-weight: 600; line-height: 1.1; }
.dd-headline small { font-size: 15px; margin-left: 4px; color: var(--txt2, #8892b0); }
.dd-stack { margin: 14px 0 10px; }
.dd-stack-bar { display: flex; height: 14px; border-radius: 7px; overflow: hidden; background: rgba(255,255,255,.05); }
.dd-stack-bar .seg { height: 100%; }
.dd-bars { display: flex; flex-direction: column; gap: 2px; }
.dd-row { display: flex; align-items: center; gap: 10px; font-size: 12.5px; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,.04); }
.dd-k { color: var(--txt2, #8892b0); flex: 1; display: flex; align-items: center; gap: 6px; }
.dd-k .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dd-v { color: var(--txt, #e6f1ff); font-weight: 600; }
.dd-v small { font-weight: 400; color: var(--txt3, #5a6380); margin-left: 2px; }
.dd-p { color: var(--txt3, #5a6380); width: 56px; text-align: right; }
.dd-notes { margin-top: 12px; font-size: 12px; color: var(--txt2, #8892b0); }
.dd-note { padding: 2px 0; }
.dd-live { margin-top: 14px; padding-top: 12px; border-top: 1px solid var(--line, rgba(255,255,255,.1)); }
.dd-live-title { font-size: 12px; color: var(--amber, #ffb020); margin-bottom: 6px; }
.dd-foot { display: flex; justify-content: flex-end; padding: 12px 18px; border-top: 1px solid var(--line, rgba(255,255,255,.1)); }
.dm-btn { padding: 7px 16px; border-radius: 7px; font-size: 13px; cursor: pointer; background: transparent; border: 1px solid var(--line, rgba(255,255,255,.15)); color: var(--txt2, #8892b0); }
/* 多 DC 视图 */
.view-toggle { margin-left: auto; display: flex; gap: 4px; background: rgba(255,255,255,.05); border-radius: 8px; padding: 2px; }
.view-toggle button { background: transparent; border: none; color: #8892b0; cursor: pointer; padding: 5px 14px; border-radius: 6px; font-size: 12px; transition: all .2s; }
.view-toggle button.active { background: rgba(66,165,245,.15); color: #42a5f5; font-weight: 600; }
.campus-card { display: flex; flex-direction: column; gap: 10px; }
.campus-card.status-degraded { border-color: rgba(253,216,53,.3); }
.camp-head { display: flex; justify-content: space-between; align-items: center; }
.camp-name { font-weight: 600; color: #fff; font-size: .95rem; }
.camp-status { font-size: .72rem; border-radius: 4px; padding: 2px 8px; }
.camp-status.online { color: #43a047; background: rgba(67,160,71,.12); }
.camp-status.degraded { color: #fdd835; background: rgba(253,216,53,.12); }
.camp-status.offline { color: #e53935; background: rgba(229,57,53,.12); }
.camp-body { display: flex; flex-direction: column; gap: 6px; }
.camp-kv { display: flex; justify-content: space-between; align-items: center; }
.camp-k { color: #888; font-size: .78rem; }
.camp-v { color: #ddd; font-weight: 500; font-size: .82rem; }
.camp-v small { color: #888; font-size: .72rem; }
.cmp-best { display: flex; font-size: .72rem; margin-top: 4px; }
.subtitle { color: #8892b0; font-size: .85rem; margin: 0 0 12px; }
</style>
