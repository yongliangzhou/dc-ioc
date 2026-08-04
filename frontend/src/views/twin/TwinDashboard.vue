<template>
  <div class="twin-db">
    <div class="view-head">
      <h1>{{ tl('nav.twin') }}</h1>
      <span class="sub">{{ tl('实时数字孪生拓扑 · 供电/冷量能流可视化') }}</span>
    </div>

    <!-- KPI -->
    <div class="grid cols-4" v-if="overview">
      <MetricCard
        metricName="activeModels"
        :label="tl('活跃模型')"
        :value="overview.activeModelCount"
        unit="个"
      />
      <MetricCard
        metricName="totalNodes"
        :label="tl('总节点')"
        :value="overview.totalNodes"
        unit="个"
      />
      <MetricCard
        metricName="totalEdges"
        :label="tl('总链路')"
        :value="overview.totalEdges"
        unit="条"
      />
      <MetricCard
        metricName="modelCount"
        :label="tl('模型总数')"
        :value="overview.modelCount"
        unit="个"
      />
    </div>
    <Panel v-else-if="loading"
      ><div class="flex center">
        <span class="muted">{{ tl('加载中...') }}</span>
      </div></Panel
    >
    <Panel v-else-if="err"
      ><div class="flex center">
        <span class="muted">{{ err }}</span>
      </div></Panel
    >

    <!-- 模型选择器 -->
    <Panel v-if="overview?.models?.length" :title="tl('模型列表')">
      <div class="model-chips">
        <button
          v-for="m in overview.models"
          :key="m.id"
          :class="['chip', { active: activeModelId === m.id }]"
          @click="selectModel(m.id)"
        >
          <span class="chip-name">{{ m.name }}</span>
          <span class="chip-meta">{{ m.nodeCount }} 节点 · {{ m.edgeCount }} 链路</span>
        </button>
      </div>
    </Panel>

    <!-- 拓扑图 -->
    <Panel v-if="topo" :title="topo.name">
      <template #extra
        ><span class="pill dim">{{ topo.description }}</span></template
      >
      <TopologyFlow v-if="topoGraph" :graph="topoGraph" />
    </Panel>
  </div>
</template>

<script setup lang="ts">
import type { ErrorLike } from '@/utils/error'
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import TopologyFlow from '@/components/twin/TopologyFlow.vue'
import {
  getTwinOverview,
  getTwinTopology,
  type TwinOverview,
  type TwinTopology,
} from '@/api/twin'
import type { TopologyGraph, TopologyNode, TopologyEdge } from '@/types'
const { t: tl } = useI18n()

const loading = ref(true)
const err = ref('')
const overview = ref<TwinOverview | null>(null)
const topo = ref<TwinTopology | null>(null)
const activeModelId = ref<number | null>(null)

function toTopologyGraph(t: TwinTopology): TopologyGraph {
  return {
    generatedAt: new Date().toISOString(),
    source: 'db',
    nodes: t.nodes.map((n, i): TopologyNode => ({
      id: i + 1,
      label: n.label,
      kind: n.kind,
      domain: n.lane === 'power' ? 'power' : n.lane === 'cool' ? 'hvac' : 'other',
      category: n.kind.toLowerCase(),
      roomId: null,
      roomCode: '',
      status: 'running',
      health: (n.health ?? 100) as number,
      loadPct: (n.load ?? 0) as number,
      redundancy: n.redundancy ?? '',
    })),
    edges: t.edges.map((e): TopologyEdge => {
      const fromIdx = t.nodes.findIndex((n) => n.id === e.from)
      const toIdx = t.nodes.findIndex((n) => n.id === e.to)
      return {
        source: fromIdx >= 0 ? fromIdx + 1 : 0,
        target: toIdx >= 0 ? toIdx + 1 : 0,
        type: e.type as 'power' | 'cool',
        label: e.label ?? '',
      }
    }),
    redundancy: { 'N+1': 0, '2N': 0, single: 0 },
  }
}

const topoGraph = computed(() => (topo.value ? toTopologyGraph(topo.value) : null))

async function selectModel(id: number) {
  activeModelId.value = id
  try {
    topo.value = await getTwinTopology()
  } catch (e: unknown) {
    err.value = (e as ErrorLike)?.message || String(e)
  }
}

onMounted(async () => {
  try {
    overview.value = await getTwinOverview()
    if (overview.value?.models?.length) {
      await selectModel(overview.value.models[0].id)
    }
  } catch (e: unknown) {
    err.value = (e as ErrorLike)?.message || String(e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.twin-db {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.model-chips {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  padding: 4px 0;
}
.chip {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 16px;
  border-radius: 10px;
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--txt);
  cursor: pointer;
  transition: 0.2s;
  text-align: left;
  min-width: 180px;
}
.chip:hover {
  border-color: var(--cyan);
  box-shadow: var(--glow);
}
.chip.active {
  border-color: var(--cyan);
  background: rgba(34, 227, 255, 0.08);
}
.chip-name {
  font-weight: 700;
  font-size: 14px;
}
.chip-meta {
  font-size: 11px;
  color: var(--txt2);
}
</style>
