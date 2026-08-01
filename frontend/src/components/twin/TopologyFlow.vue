<template>
  <div class="topo-flow">
    <div class="tf-legend">
      <span class="tf-lg"><i class="dot flow-power" />{{ tl('供电能流') }}</span>
      <span class="tf-lg"><i class="dot flow-cool" />{{ tl('制冷冷量流') }}</span>
      <span class="tf-lg" v-if="affectedIds?.length"><i class="dot fault" />{{ tl('故障传播') }} · {{ affectedIds!.length }} 台波及</span>
      <span class="tf-lg dim">{{ realtime ? tl('真实测点驱动') : tl('模拟负载') }} · {{ graph.source === 'db' ? tl('真实台账') : tl('模拟台账') }}</span>
      <span class="tf-lg hint">{{ tl('点击节点聚焦 · 缩略图导航') }}</span>
    </div>

    <div class="tf-stage">
      <!-- 主画布 (可滚动, 固定像素尺寸, 缩略图与聚焦据此导航) -->
      <div class="tf-canvas" ref="canvasRef" @scroll="onScroll">
        <svg
          :viewBox="`0 0 ${layout.width} ${layout.height}`"
          :style="{ width: layout.width + 'px', height: layout.height + 'px' }"
          class="tf-svg"
          @click="clearFocus"
        >
          <!-- 边 (底层) -->
          <g class="tf-edges">
            <template v-for="e in layout.edges" :key="e.id">
              <path
                :id="e.id"
                :d="e.d"
                :class="['edge', e.type, { fault: e.affected, dim: dimEdge(e), hot: hotEdge(e) }]"
                fill="none"
              />
              <circle v-if="!dimEdge(e)" r="3.2" :class="['flow-dot', e.type, { fault: e.affected, dim: dimEdge(e) }]">
                <animateMotion :dur="e.dur" repeatCount="indefinite">
                  <mpath :href="'#' + e.id" />
                </animateMotion>
              </circle>
              <circle v-if="!dimEdge(e)" r="3.2" :class="['flow-dot', e.type, { fault: e.affected }]">
                <animateMotion :dur="e.dur" begin="-1.2s" repeatCount="indefinite">
                  <mpath :href="'#' + e.id" />
                </animateMotion>
              </circle>
            </template>
          </g>

          <!-- 节点 (上层) -->
          <g class="tf-nodes">
            <g
              v-for="n in layout.nodes"
              :key="n.id"
              class="tf-node"
              :class="[n.lane, { affected: n.affected, down: n.downstream, dim: dimNode(n), focus: focusedId === n.id }]"
              :transform="`translate(${n.x},${n.y})`"
              @click.stop="focusNode(n.id)"
              @mouseenter="hoveredId = n.id"
              @mouseleave="hoveredId = null"
            >
              <title>{{ n.label }} · {{ n.kind }} · {{ tl('负载') }} {{ n.load }}% · {{ tl('健康') }} {{ n.health }}{{ n.redundancy ? ' · ' + n.redundancy : '' }}{{ n.tempText ? ' · ' + n.tempText : '' }}</title>
              <rect :width="NODE_W" :height="NODE_H" rx="9" class="tf-rect" />
              <rect :width="NODE_W" :height="3" rx="1.5" class="tf-loadbar" :x="0" :y="0" :style="{ width: NODE_W * Math.min(1, n.load / 100) + 'px' }" />
              <text :x="NODE_W / 2" y="14" class="tf-kind">{{ n.kind }}</text>
              <text :x="NODE_W / 2" y="27" class="tf-load">{{ n.loadText }}</text>
              <text v-if="n.tempText" :x="NODE_W / 2" y="39" class="tf-temp">{{ n.tempText }}</text>
              <circle v-if="n.affected" :cx="NODE_W - 7" :cy="7" r="3.5" class="tf-badge" />
            </g>
          </g>
        </svg>
      </div>

      <!-- 链路缩略图 / 聚焦导航 -->
      <div class="tf-minimap">
        <div class="mm-title">
          <span>{{ tl('缩略图') }}</span>
          <span class="mm-tip">{{ tl('点击定位') }}</span>
        </div>
        <svg
          class="mm-svg"
          :viewBox="`0 0 ${layout.width} ${layout.height}`"
          preserveAspectRatio="xMidYMid meet"
          @click="onMinimapClick"
        >
          <path
            v-for="e in layout.edges"
            :key="e.id"
            :d="e.d"
            :class="['mm-edge', { 'mm-fault': e.affected }]"
            fill="none"
          />
          <rect
            v-if="viewportRect"
            :x="viewportRect.x"
            :y="viewportRect.y"
            :width="viewportRect.w"
            :height="viewportRect.h"
            class="mm-view"
          />
          <circle
            v-for="n in layout.nodes"
            :key="n.id"
            :cx="n.x + NODE_W / 2"
            :cy="n.y + NODE_H / 2"
            r="2.8"
            :class="['mm-node', n.lane, { affected: n.affected, focus: focusedId === n.id }]"
            @click.stop="focusNode(n.id)"
          >
            <title>{{ n.label }}</title>
          </circle>
        </svg>
      </div>

      <!-- 聚焦详情卡 -->
      <div class="tf-focus-card" v-if="focusedDetail">
        <div class="ff-head">
          <span class="ff-kind" :class="'lane-' + focusedDetail.node.lane">{{ focusedDetail.node.kind }}</span>
          <span class="ff-name">{{ focusedDetail.node.label }}</span>
          <button class="ff-x" @click="clearFocus" :title="tl('取消聚焦')"><X :size="13" /></button>
        </div>
        <div class="ff-room" v-if="focusedDetail.roomName">{{ focusedDetail.roomName }}</div>
        <div class="ff-rows">
          <div class="ff-row"><span>{{ tl('负载') }}</span><b>{{ focusedDetail.node.load }}%</b></div>
          <div class="ff-row" v-if="focusedDetail.node.tempText"><span>{{ tl('温度') }}</span><b>{{ focusedDetail.node.tempText }}</b></div>
          <div class="ff-row"><span>{{ tl('健康') }}</span><b :style="{ color: hColor(focusedDetail.node.health) }">{{ focusedDetail.node.health }}</b></div>
          <div class="ff-row" v-if="focusedDetail.node.redundancy"><span>{{ tl('冗余') }}</span><b>{{ focusedDetail.node.redundancy }}</b></div>
          <div class="ff-row" v-if="focusedDetail.rt">
            <span>{{ tl('在线') }}</span>
            <b :style="{ color: focusedDetail.rt.online ? 'var(--green)' : 'var(--red)' }">{{ focusedDetail.rt.online ? tl('在线') : tl('离线') }}</b>
          </div>
        </div>
        <div class="ff-metrics" v-if="rtFields.length">
          <span class="ff-m" v-for="m in rtFields" :key="m.k">{{ m.k }} <b>{{ m.v }}</b></span>
        </div>
        <div class="ff-hint">{{ tl('点击空白区域取消聚焦') }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount } from "vue";
import { useI18n } from "vue-i18n";
import { X } from "lucide-vue-next";
import type { TopologyGraph, TopologyNode, NodeRealtime, TopologyRealtime } from "@/types";

const props = defineProps<{
  graph: TopologyGraph;
  realtime?: TopologyRealtime | null;
  affectedIds?: number[];
  roomName?: (roomId: number) => string | null;
}>();

const { t, te } = useI18n();
const tl = (k: string) => (te(k) ? t(k) : k);

const canvasRef = ref<HTMLElement | null>(null);
const scrollPos = ref({ x: 0, y: 0 });

const NODE_W = 92;
const NODE_H = 46;
const LEFT = 64;
const COL_GAP = 116;
const ROW_GAP = 30;

const POWERS = ["hv_incomer", "hv_isolator", "hv_breaker", "transformer", "ups", "hvdc", "lv_feeder", "ats"];
const COOLS = ["chiller", "chw_pump", "cooling_tower", "hex", "sec_pump", "valve", "crac"];
const AUX = ["genset", "bus_tie", "battery_group"];
const powerSet = new Set(POWERS);
const coolSet = new Set(COOLS);
const auxSet = new Set(AUX);

// ---- 真实测点映射 (任务①): 接 /api/external/.../metrics/realtime, 驱动能流速度/温度 ----
function rtOf(id: number): NodeRealtime | undefined {
  return (props.realtime?.nodes ?? {})[id];
}
// 有效负载率: 优先真实测点 loadPct, 缺失时回退模拟 loadPct
function effLoadPct(n: TopologyNode, rt?: NodeRealtime): number {
  if (rt && rt.loadPct != null) return Math.max(0, Math.min(100, rt.loadPct));
  return Math.max(0, Math.min(100, n.loadPct ?? 0));
}
// 冷量流温度文本 (供水→回水), 否则通用温度
function nodeTempText(rt?: NodeRealtime): string | null {
  if (!rt) return null;
  if (rt.supplyTemp != null || rt.returnTemp != null) {
    const s = rt.supplyTemp != null ? rt.supplyTemp.toFixed(1) : "–";
    const r = rt.returnTemp != null ? rt.returnTemp.toFixed(1) : "–";
    return `${s}→${r}℃`;
  }
  if (rt.temp != null) return `${rt.temp.toFixed(1)}℃`;
  return null;
}
// 节点负载文本: 真实负载% / 供电域真实功率kW / 模拟负载%
function nodeLoadText(n: TopologyNode, rt?: NodeRealtime, lane?: string): string {
  const health = Math.round(n.health ?? 100);
  if (rt && rt.loadPct != null) return `${Math.round(rt.loadPct)}% · ${health}`;
  if (lane === "power" && rt && rt.powerKw != null) return `${Math.round(rt.powerKw)}kW · ${health}`;
  return `${Math.round(n.loadPct ?? 0)}% · ${health}`;
}

type Lane = "power" | "cool" | "aux";
function laneOf(domain: string, category: string): Lane {
  if (powerSet.has(category)) return "power";
  if (coolSet.has(category)) return "cool";
  if (auxSet.has(category)) return "aux";
  if (domain.startsWith("power")) return "power";
  if (domain.startsWith("hvac")) return "cool";
  return "aux";
}
function hColor(h: number) {
  return h >= 75 ? "var(--green)" : h >= 60 ? "var(--amber)" : "var(--red)";
}

interface LNode {
  id: number; x: number; y: number; lane: string;
  label: string; kind: string; load: number; health: number; redundancy: string;
  affected: boolean; downstream: boolean;
  loadText: string; tempText: string | null;
}
interface LEdge {
  id: string; d: string; type: "power" | "cool"; affected: boolean; dur: string;
  source: number; target: number;
}

const affectedSet = computed(() => new Set(props.affectedIds ?? []));

// ---- 聚焦交互状态 ----
const focusedId = ref<number | null>(null);
const hoveredId = ref<number | null>(null);
const activeId = computed(() => focusedId.value ?? hoveredId.value);

const activeNeighbors = computed(() => {
  const id = activeId.value;
  const s = new Set<number>();
  if (id == null) return s;
  for (const e of props.graph?.edges ?? []) {
    if (e.source === id) s.add(e.target);
    if (e.target === id) s.add(e.source);
  }
  s.add(id);
  return s;
});
function dimNode(n: LNode): boolean {
  return activeId.value != null && !activeNeighbors.value.has(n.id);
}
function dimEdge(e: LEdge): boolean {
  return activeId.value != null && e.source !== activeId.value && e.target !== activeId.value;
}
function hotEdge(e: LEdge): boolean {
  return activeId.value != null && (e.source === activeId.value || e.target === activeId.value);
}
function focusNode(id: number) {
  focusedId.value = id;
}
function clearFocus() {
  focusedId.value = null;
}

// ---- 缩略图视口矩形 (随滚动同步) ----
function onScroll() {
  const c = canvasRef.value;
  if (c) scrollPos.value = { x: c.scrollLeft, y: c.scrollTop };
}
const viewportRect = computed(() => {
  const c = canvasRef.value;
  if (!c) return null;
  scrollPos.value; // 依赖, 触发重算
  const w = Math.min(c.clientWidth, layout.value.width);
  const h = Math.min(c.clientHeight, layout.value.height);
  let x = c.scrollLeft;
  let y = c.scrollTop;
  if (x + w > layout.value.width) x = Math.max(0, layout.value.width - w);
  if (y + h > layout.value.height) y = Math.max(0, layout.value.height - h);
  return { x, y, w, h };
});
function onMinimapClick(ev: MouseEvent) {
  const svg = ev.currentTarget as SVGSVGElement;
  const rect = svg.getBoundingClientRect();
  const gx = ((ev.clientX - rect.left) / rect.width) * layout.value.width;
  const gy = ((ev.clientY - rect.top) / rect.height) * layout.value.height;
  const c = canvasRef.value;
  if (!c) return;
  c.scrollTo({
    left: Math.max(0, gx - c.clientWidth / 2),
    top: Math.max(0, gy - c.clientHeight / 2),
    behavior: "smooth",
  });
}

// ---- 聚焦详情 ----
const focusedDetail = computed(() => {
  const id = focusedId.value;
  if (id == null) return null;
  const node = layout.value.nodes.find((n) => n.id === id);
  if (!node) return null;
  const raw = props.graph?.nodes.find((n) => n.id === id);
  const rt = rtOf(id);
  return {
    node,
    raw,
    rt,
    roomName: props.roomName && raw?.roomId != null ? props.roomName(raw.roomId) : null,
  };
});
const RT_LABEL: Record<string, string> = {
  loadPct: "负载%",
  powerKw: "功率kW",
  supplyTemp: "供水℃",
  returnTemp: "回水℃",
  temp: "温度℃",
};
const rtFields = computed(() => {
  const rt = focusedDetail.value?.rt;
  if (!rt) return [];
  const out: { k: string; v: string }[] = [];
  for (const [k, lab] of Object.entries(RT_LABEL)) {
    const v = (rt as Record<string, unknown>)[k];
    if (v != null && typeof v === "number") {
      const dec = k === "powerKw" ? 0 : 1;
      out.push({ k: lab, v: v.toFixed(dec) });
    }
  }
  return out;
});

function onResize() {
  onScroll();
}
onMounted(() => {
  onScroll();
  window.addEventListener("resize", onResize);
});
onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize);
});

// 拓扑分层: 依据真实边给同 lane 节点分配 stage 列 (无入边=第0列, 沿边递增)
function layerAssign(ids: number[], edgs: { source: number; target: number }[]): Map<number, number> {
  const indeg = new Map<number, number>();
  const adj = new Map<number, number[]>();
  ids.forEach((id) => {
    indeg.set(id, 0);
    adj.set(id, []);
  });
  for (const e of edgs) {
    if (!adj.has(e.source) || !indeg.has(e.target)) continue;
    adj.get(e.source)!.push(e.target);
    indeg.set(e.target, (indeg.get(e.target) ?? 0) + 1);
  }
  const layer = new Map<number, number>();
  indeg.forEach((v, id) => {
    if (v === 0) layer.set(id, 0);
  });
  for (let pass = 0; pass <= ids.length; pass++) {
    let changed = false;
    for (const e of edgs) {
      if (!layer.has(e.source)) continue;
      const ls = layer.get(e.source)!;
      const cur = layer.has(e.target) ? layer.get(e.target)! : -1;
      const want = ls + 1;
      if (cur < 0 || want > cur) {
        layer.set(e.target, want);
        changed = true;
      }
    }
    if (!changed) break;
  }
  ids.forEach((id) => {
    if (!layer.has(id)) layer.set(id, 0);
  });
  return layer;
}

const layout = computed(() => {
  const nodes = props.graph?.nodes ?? [];
  const edges = props.graph?.edges ?? [];

  const byId = new Map<number, TopologyNode>();
  for (const n of nodes) byId.set(n.id, n);

  // 真实测点归一化映射: 每个节点的有效负载率 (驱动能流速度)
  const rtm = props.realtime?.nodes ?? {};
  const effById = new Map<number, number>();
  for (const n of nodes) effById.set(n.id, effLoadPct(n, rtm[n.id]));

  // 1) 按 domain 分 lane, 并用真实边做拓扑分层 (数据驱动, 不依赖后端 stage 命名)
  const laneNodes: Record<Lane, TopologyNode[]> = { power: [], cool: [], aux: [] };
  for (const n of nodes) laneNodes[laneOf(n.domain || "", n.category || "")].push(n);

  const pos = new Map<number, { x: number; y: number }>();
  let laneTop = 14;
  let maxCol = 0;

  const laneOrder: Lane[] = ["power", "aux", "cool"];
  for (const lane of laneOrder) {
    const ns = laneNodes[lane];
    if (!ns.length) continue;
    const idSet = new Set(ns.map((n) => n.id));
    const inLane = edges.filter((e) => idSet.has(e.source) && idSet.has(e.target));
    const layer = layerAssign(ns.map((n) => n.id), inLane);

    // 参与真实边的节点按拓扑层排布; 断连节点(后端未连边)按 category 横向铺开, 避免单列堆叠
    const connected = new Set<number>();
    for (const e of inLane) {
      connected.add(e.source);
      connected.add(e.target);
    }
    let maxConnLayer = 0;
    for (const id of connected) maxConnLayer = Math.max(maxConnLayer, layer.get(id) ?? 0);
    const discCats: string[] = [];
    for (const n of ns) {
      if (!connected.has(n.id) && !discCats.includes(n.category || "")) discCats.push(n.category || "");
    }
    const colOfNode = (n: TopologyNode): number => {
      if (connected.has(n.id)) return layer.get(n.id) ?? 0;
      const ci = discCats.indexOf(n.category || "");
      return maxConnLayer + 1 + (ci < 0 ? 0 : ci);
    };

    const colNodes: Record<number, TopologyNode[]> = {};
    let laneMaxCol = 0;
    let laneMaxCount = 0;
    for (const n of ns) {
      const c = colOfNode(n);
      laneMaxCol = Math.max(laneMaxCol, c);
      (colNodes[c] ??= []).push(n);
      laneMaxCount = Math.max(laneMaxCount, colNodes[c].length);
    }
    maxCol = Math.max(maxCol, laneMaxCol);
    const laneH = laneMaxCount * ROW_GAP + 16;
    for (const [cstr, list] of Object.entries(colNodes)) {
      const c = Number(cstr);
      list.forEach((n, i) => {
        pos.set(n.id, { x: LEFT + c * COL_GAP, y: laneTop + 10 + i * ROW_GAP });
      });
    }
    laneTop += laneH + 22;
  }

  // 2) 故障下游传播: 从波及节点沿边 BFS 标 downstream
  const downstreamSet = new Set<number>();
  const queue = [...affectedSet.value];
  const seen = new Set(queue);
  while (queue.length) {
    const cur = queue.shift()!;
    for (const e of edges) {
      if (e.source === cur && !seen.has(e.target)) {
        seen.add(e.target);
        downstreamSet.add(e.target);
        queue.push(e.target);
      }
    }
  }

  const lnodes: LNode[] = nodes.map((n) => {
    const p = pos.get(n.id) ?? { x: LEFT, y: laneTop };
    const rt = rtm[n.id];
    const lane = laneOf(n.domain || "", n.category || "");
    return {
      id: n.id,
      x: p.x,
      y: p.y,
      lane,
      label: n.label,
      kind: n.kind,
      load: effById.get(n.id) ?? Math.round(n.loadPct ?? 0),
      health: Math.round(n.health ?? 100),
      redundancy: n.redundancy || "",
      affected: affectedSet.value.has(n.id),
      downstream: downstreamSet.has(n.id),
      loadText: nodeLoadText(n, rt, lane),
      tempText: nodeTempText(rt),
    };
  });

  const ledges: LEdge[] = [];
  for (const e of edges) {
    const s = pos.get(e.source);
    const tg = pos.get(e.target);
    const sn = byId.get(e.source);
    const tn = byId.get(e.target);
    if (!s || !tg || !sn || !tn) continue;
    const sx = s.x + NODE_W;
    const sy = s.y + NODE_H / 2;
    const tx = tg.x;
    const ty = tg.y + NODE_H / 2;
    const dx = tx - sx;
    const d = `M ${sx} ${sy} C ${sx + dx * 0.5} ${sy}, ${tx - dx * 0.5} ${ty}, ${tx} ${ty}`;
    const avgLoad = (effById.get(e.source)! + effById.get(e.target)!) / 2;
    const dur = Math.max(0.9, Math.min(3, 2.6 - avgLoad / 45)).toFixed(2) + "s";
    const touch = affectedSet.value.has(e.source) || affectedSet.value.has(e.target);
    ledges.push({
      id: `e-${e.source}-${e.target}`,
      d,
      type: (e.type === "cool" ? "cool" : "power") as "power" | "cool",
      affected: touch,
      dur,
      source: e.source,
      target: e.target,
    });
  }

  const width = LEFT + (maxCol + 1) * COL_GAP + 24;
  const height = laneTop + 10;
  return { nodes: lnodes, edges: ledges, width, height };
});
</script>

<style scoped>
.topo-flow { display: flex; flex-direction: column; gap: 8px; }
.tf-legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 11px; color: var(--txt3); }
.tf-lg { display: inline-flex; align-items: center; gap: 5px; }
.tf-lg.dim { opacity: .7; }
.tf-lg.hint { color: var(--cyan); opacity: .85; }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dot.flow-power { background: #fbbf24; box-shadow: 0 0 6px #fbbf24; }
.dot.flow-cool { background: #22d3ee; box-shadow: 0 0 6px #22d3ee; }
.dot.fault { background: #ff4d4f; box-shadow: 0 0 6px #ff4d4f; }

.tf-stage { position: relative; }
.tf-canvas { width: 100%; max-height: 520px; overflow: auto; background:
  radial-gradient(circle at 20% 10%, rgba(34,211,238,.05), transparent 40%),
  radial-gradient(circle at 80% 90%, rgba(251,191,36,.05), transparent 40%),
  var(--bg); border-radius: 12px; border: 1px solid var(--line); }
.tf-svg { display: block; }

/* 边 */
.edge { stroke-width: 1.6; opacity: .55; transition: opacity .15s ease, stroke-width .15s ease; }
.edge.power { stroke: #fbbf24; }
.edge.cool { stroke: #22d3ee; }
.edge.fault { stroke: #ff4d4f; stroke-width: 2.4; opacity: 1; stroke-dasharray: 6 4; animation: dash 1s linear infinite; }
.edge.dim { opacity: .1; }
.edge.hot { opacity: 1; stroke-width: 2.6; }
@keyframes dash { to { stroke-dashoffset: -20; } }

.flow-dot { fill: #fbbf24; filter: drop-shadow(0 0 3px #fbbf24); }
.flow-dot.cool { fill: #22d3ee; filter: drop-shadow(0 0 3px #22d3ee); }
.flow-dot.fault { fill: #ff4d4f; filter: drop-shadow(0 0 4px #ff4d4f); }
.flow-dot.dim { opacity: .1; }

/* 节点 */
.tf-rect { fill: var(--bg2); stroke: var(--line); stroke-width: 1.4; transition: stroke .15s ease, fill .15s ease; }
.tf-node { cursor: pointer; transition: opacity .15s ease; }
.tf-node.power .tf-rect { stroke: rgba(251,191,36,.5); }
.tf-node.cool .tf-rect { stroke: rgba(34,211,238,.5); }
.tf-node.aux .tf-rect { stroke: rgba(148,163,184,.5); }
.tf-kind { fill: var(--txt); font-size: 11px; font-weight: 700; text-anchor: middle; }
.tf-load { fill: var(--txt3); font-size: 9.5px; text-anchor: middle; }
.tf-temp { fill: #22d3ee; font-size: 9px; text-anchor: middle; font-weight: 600; }
.tf-node.power .tf-temp { fill: #fbbf24; }
.tf-loadbar { fill: rgba(34,197,94,.55); }
.tf-node.affected .tf-rect { stroke: #ff4d4f; stroke-width: 2.4; fill: rgba(255,77,79,.16); animation: pulse 1.1s ease-in-out infinite; }
.tf-node.affected .tf-kind { fill: #ffd7d7; }
.tf-node.downstream .tf-rect { stroke: rgba(255,77,79,.6); }
.tf-node.dim { opacity: .22; }
.tf-node.focus .tf-rect { stroke: #22e3ff; stroke-width: 2.8; fill: rgba(34,227,255,.12); }
@keyframes pulse { 0%,100% { stroke-opacity: 1; } 50% { stroke-opacity: .35; } }
.tf-badge { fill: #ff4d4f; }

/* 缩略图 */
.tf-minimap { position: absolute; top: 10px; right: 10px; width: 184px; background: rgba(10,15,25,.8); border: 1px solid var(--line); border-radius: 10px; padding: 6px 7px 8px; backdrop-filter: blur(4px); box-shadow: 0 6px 18px rgba(0,0,0,.4); z-index: 5; }
.mm-title { display: flex; justify-content: space-between; align-items: center; font-size: 10px; color: var(--txt3); margin-bottom: 4px; }
.mm-tip { color: var(--cyan); opacity: .8; }
.mm-svg { display: block; width: 100%; height: auto; max-height: 150px; cursor: crosshair; background: rgba(0,0,0,.25); border-radius: 6px; }
.mm-edge { stroke: rgba(148,163,184,.3); stroke-width: 1; }
.mm-edge.mm-fault { stroke: rgba(255,77,79,.7); }
.mm-view { fill: rgba(34,227,255,.14); stroke: rgba(34,227,255,.65); stroke-width: 1.2; }
.mm-node { cursor: pointer; }
.mm-node.power { fill: #fbbf24; }
.mm-node.cool { fill: #22d3ee; }
.mm-node.aux { fill: #94a3b8; }
.mm-node.affected { fill: #ff4d4f; }
.mm-node.focus { stroke: #fff; stroke-width: 1.6; }

/* 聚焦详情卡 */
.tf-focus-card { position: absolute; left: 10px; bottom: 10px; width: 232px; background: rgba(12,18,30,.93); border: 1px solid rgba(34,227,255,.35); border-radius: 10px; padding: 10px 12px; z-index: 6; box-shadow: 0 8px 22px rgba(0,0,0,.45); backdrop-filter: blur(4px); }
.ff-head { display: flex; align-items: center; gap: 6px; }
.ff-kind { font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 5px; background: var(--bg2); color: var(--txt2); }
.ff-kind.lane-power { color: #fbbf24; background: rgba(251,191,36,.14); }
.ff-kind.lane-cool { color: #22d3ee; background: rgba(34,211,238,.14); }
.ff-kind.lane-aux { color: #94a3b8; background: rgba(148,163,184,.14); }
.ff-name { font-size: 13px; font-weight: 700; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ff-x { border: none; background: transparent; color: var(--txt3); cursor: pointer; display: inline-flex; padding: 2px; border-radius: 5px; }
.ff-x:hover { color: var(--txt); background: rgba(255,255,255,.08); }
.ff-room { font-size: 11px; color: #7dd3fc; margin: 3px 0 6px; }
.ff-rows { display: flex; flex-direction: column; gap: 4px; }
.ff-row { display: flex; justify-content: space-between; font-size: 12px; color: var(--txt2); }
.ff-row b { color: var(--txt); font-weight: 700; }
.ff-metrics { display: flex; flex-wrap: wrap; gap: 4px 10px; margin-top: 7px; padding-top: 7px; border-top: 1px dashed var(--line); font-size: 11px; color: var(--txt3); }
.ff-m b { color: var(--txt); font-weight: 700; }
.ff-hint { font-size: 10px; color: var(--txt3); margin-top: 7px; opacity: .8; }
</style>
