<template>
  <div class="ci-page">
    <div class="view-head">
      <h1>{{ t('ciRelation.title') }}</h1>
      <span class="sub">{{ t('ciRelation.subtitle') }}</span>
    </div>

    <p v-if="notice" class="notice">{{ notice }}</p>

    <div class="grid">
      <!-- ===== 新建关系 ===== -->
      <section class="card">
        <h2>{{ t('ciRelation.sectionCreate') }}</h2>
        <label>{{ t('ciRelation.sourceCi') }}</label>
        <select v-model="form.source_ci" class="ipt">
          <option v-for="o in options" :key="o.ci" :value="o.ci">{{ o.ci }} · {{ o.name }}</option>
        </select>
        <label>{{ t('ciRelation.targetCi') }}</label>
        <select v-model="form.target_ci" class="ipt">
          <option v-for="o in options" :key="o.ci" :value="o.ci">{{ o.ci }} · {{ o.name }}</option>
        </select>
        <label>{{ t('ciRelation.relationType') }}</label>
        <select v-model="form.relation_type" class="ipt">
          <option v-for="r in RELATION_TYPES" :key="r" :value="r">
            {{ t('ciRelation.type.' + r) }}
          </option>
        </select>
        <label>{{ t('ciRelation.description') }}</label>
        <input v-model="form.description" class="ipt" type="text" />
        <button class="btn primary" :disabled="!canSubmit || saving" @click="createRelation">
          {{ t('ciRelation.add') }}
        </button>
        <p v-if="formError" class="err">{{ formError }}</p>
      </section>

      <!-- ===== 影响扩散 ===== -->
      <section class="card">
        <h2>{{ t('ciRelation.sectionImpact') }}</h2>
        <label>{{ t('ciRelation.sourceCi') }}</label>
        <select v-model="impactCi" class="ipt">
          <option v-for="o in options" :key="o.ci" :value="o.ci">{{ o.ci }} · {{ o.name }}</option>
        </select>
        <label>{{ t('ciRelation.impactDepth') }} ({{ impactDepth }})</label>
        <input v-model.number="impactDepth" class="ipt" type="range" min="1" max="6" />
        <button class="btn" :disabled="!impactCi" @click="runImpact">
          {{ t('ciRelation.analyze') }}
        </button>
        <div v-if="impact" class="impact-summary">
          <span class="tag" :class="impact.topology_source">
            {{
              impact.topology_source === 'real'
                ? t('ciRelation.sourceLabel') + ': real'
                : t('ciRelation.fallbackNotice')
            }}
          </span>
          <span>{{ t('ciRelation.total') }}: {{ impact.total }}</span>
          <span v-if="impact.has_cycle">cycle</span>
        </div>
        <table v-if="impact && impact.impacted.length" class="tbl">
          <thead>
            <tr>
              <th>CI</th>
              <th>{{ t('ciRelation.hop') }}</th>
              <th>{{ t('ciRelation.via') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="i in impact.impacted" :key="i.ci">
              <td class="mono">{{ i.ci }}</td>
              <td>{{ i.hop }}</td>
              <td>{{ i.via }}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </div>

    <!-- ===== 关系图 ===== -->
    <section class="card">
      <h2>{{ t('ciRelation.graph') }} · {{ graph.total }}</h2>
      <svg v-if="graph.nodes.length" viewBox="0 0 620 320" class="graph">
        <line
          v-for="e in graph.edges"
          :key="e.id"
          :x1="pos(e.source).x"
          :y1="pos(e.source).y"
          :x2="pos(e.target).x"
          :y2="pos(e.target).y"
          stroke="var(--cyan)"
          stroke-opacity="0.45"
          stroke-width="1.5"
        />
        <g v-for="n in graph.nodes" :key="n.id">
          <circle :cx="pos(n.id).x" :cy="pos(n.id).y" r="6" fill="var(--cyan)" />
          <text :x="pos(n.id).x + 10" :y="pos(n.id).y + 4" fill="var(--txt)" font-size="11">
            {{ n.name }}
          </text>
        </g>
      </svg>
      <p v-else class="empty">{{ t('ciRelation.empty') }}</p>
    </section>

    <!-- ===== 关系清单 ===== -->
    <section class="card">
      <h2>{{ t('ciRelation.sectionList') }}</h2>
      <div class="filters">
        <input v-model="keyword" class="ipt" type="text" placeholder="keyword" />
        <select v-model="filterType" class="ipt">
          <option value="">all</option>
          <option v-for="r in RELATION_TYPES" :key="r" :value="r">
            {{ t('ciRelation.type.' + r) }}
          </option>
        </select>
        <button class="btn-sm" @click="reload">{{ t('common.refresh') }}</button>
      </div>
      <table class="tbl">
        <thead>
          <tr>
            <th>{{ t('ciRelation.sourceCi') }}</th>
            <th>{{ t('ciRelation.relationType') }}</th>
            <th>{{ t('ciRelation.targetCi') }}</th>
            <th>{{ t('ciRelation.description') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in filtered" :key="row.id">
            <td class="mono">{{ row.source_name || row.source_ci }}</td>
            <td>{{ t('ciRelation.type.' + row.relation_type) }}</td>
            <td class="mono">{{ row.target_name || row.target_ci }}</td>
            <td>{{ row.description }}</td>
            <td>
              <button class="btn-sm danger" @click="removeRelation(row.id)">
                {{ t('ciRelation.delete') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!filtered.length" class="empty">{{ t('ciRelation.empty') }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { useFilterQuery } from '@/composables/useFilterQuery'
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ciRelationApi,
  type CiGraph,
  type CiImpact,
  type CiOption,
  type CiRelationRow,
  type RelationType,
} from '@/api/ciRelation'

const { t } = useI18n()
const RELATION_TYPES: RelationType[] = ['connects_to', 'powers', 'cools', 'depends_on', 'hosts']

const FALLBACK: CiRelationRow[] = [
  {
    id: -1,
    source_ci: 'equipment:1',
    target_ci: 'cabinet:A01',
    source_name: 'UPS-01',
    target_name: 'A01 Cabinet',
    relation_type: 'powers',
    description: 'A feed',
    created_by: 'demo',
    created_at: null,
    tenant_id: null,
  },
  {
    id: -2,
    source_ci: 'cabinet:A01',
    target_ci: 'server:S1',
    source_name: 'A01 Cabinet',
    target_name: 'Server-01',
    relation_type: 'hosts',
    description: 'U12',
    created_by: 'demo',
    created_at: null,
    tenant_id: null,
  },
]

const rows = ref<CiRelationRow[]>([])
const options = ref<CiOption[]>([])
const graph = ref<CiGraph>({ nodes: [], edges: [], total: 0, topology_source: 'fallback' })
const impact = ref<CiImpact | null>(null)
const notice = ref('')
const formError = ref('')
const saving = ref(false)
const keyword = ref('')
const filterType = ref('')
const impactCi = ref('')
const impactDepth = ref(3)
const form = reactive({
  source_ci: '',
  target_ci: '',
  relation_type: 'powers' as RelationType,
  description: '',
})

const canSubmit = computed(
  () => !!form.source_ci && !!form.target_ci && form.source_ci !== form.target_ci,
)
const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return rows.value.filter((r) => {
    if (filterType.value && r.relation_type !== filterType.value) return false
    if (!kw) return true
    return [r.source_ci, r.target_ci, r.source_name, r.target_name]
      .join(' ')
      .toLowerCase()
      .includes(kw)
  })
})

function pos(id: string): { x: number; y: number } {
  const idx = graph.value.nodes.findIndex((n) => n.id === id)
  if (idx < 0) return { x: 0, y: 0 }
  return { x: 60 + (idx % 4) * 150, y: 40 + Math.floor(idx / 4) * 66 }
}

function useFallback(err: unknown) {
  console.warn('[ci-relations] 后端不可达, 使用本地示例:', err)
  notice.value = t('ciRelation.localFallback')
  rows.value = [...FALLBACK]
  if (!options.value.length) {
    options.value = Array.from(new Set(FALLBACK.flatMap((r) => [r.source_ci, r.target_ci]))).map(
      (ci) => ({ ci, name: ci, kind: 'demo' }),
    )
  }
}

async function reload() {
  try {
    rows.value = await ciRelationApi.list()
    notice.value = ''
  } catch (err) {
    useFallback(err)
  }
}

async function loadAux() {
  try {
    options.value = await ciRelationApi.options()
  } catch (err) {
    console.warn('[ci-relations] CI 选项加载失败:', err)
    if (!options.value.length) {
      options.value = Array.from(new Set(FALLBACK.flatMap((r) => [r.source_ci, r.target_ci]))).map(
        (ci) => ({ ci, name: ci, kind: 'demo' }),
      )
    }
  }
  try {
    graph.value = await ciRelationApi.graph()
  } catch (err) {
    console.warn('[ci-relations] 关系图加载失败:', err)
    if (!graph.value.nodes.length)
      graph.value = { nodes: [], edges: [], total: 0, topology_source: 'fallback' }
  }
  if (!impactCi.value && options.value.length) impactCi.value = options.value[0].ci
  if (!form.source_ci && options.value.length) form.source_ci = options.value[0].ci
  if (!form.target_ci && options.value.length > 1) form.target_ci = options.value[1].ci
}

async function createRelation() {
  if (!canSubmit.value) return
  saving.value = true
  formError.value = ''
  try {
    await ciRelationApi.create({ ...form })
    await Promise.all([reload(), loadAux()])
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    formError.value = msg
  } finally {
    saving.value = false
  }
}

async function removeRelation(id: number) {
  if (id < 0) {
    rows.value = rows.value.filter((r) => r.id !== id)
    return
  }
  try {
    await ciRelationApi.remove(id)
    await Promise.all([reload(), loadAux()])
  } catch (err) {
    formError.value = err instanceof Error ? err.message : String(err)
  }
}

async function runImpact() {
  if (!impactCi.value) return
  try {
    impact.value = await ciRelationApi.impact(impactCi.value, impactDepth.value)
  } catch (err) {
    console.warn('[ci-relations] 影响分析失败:', err)
    impact.value = {
      source_ci: impactCi.value,
      depth: impactDepth.value,
      topology_source: 'fallback',
      impacted: [],
      total: 0,
      has_cycle: false,
    }
  }
}

onMounted(async () => {
  await reload()
  await loadAux()
})

// 04 §6.2: 筛选条件（与分页）写入 URL query
useFilterQuery({ keyword, filterType })
</script>

<style scoped>
.ci-page {
  padding: 20px 24px 40px;
  color: var(--txt-strong);
}
.view-head {
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 18px;
}
.view-head h1 {
  font-size: 20px;
  color: var(--cyan);
  margin: 0;
}
.sub {
  font-size: 12px;
  color: var(--txt2);
}
.notice {
  border: 1px solid color-mix(in srgb, var(--amber) 40%, transparent);
  background: color-mix(in srgb, var(--amber) 8%, transparent);
  color: var(--amber);
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 16px;
}
.card {
  background: var(--accent-02);
  border: 1px solid var(--accent-08);
  border-radius: 10px;
  padding: 16px;
  margin-bottom: 16px;
}
.card h2 {
  font-size: 14px;
  color: var(--blue);
  margin: 0 0 14px;
}
label {
  display: block;
  font-size: 12px;
  color: var(--txt2);
  margin: 10px 0 4px;
}
.ipt {
  width: 100%;
  background: var(--mask);
  border: 1px solid var(--accent-12);
  color: var(--txt-strong);
  border-radius: 6px;
  padding: 7px 9px;
  font-size: 12px;
  box-sizing: border-box;
}
.btn,
.btn-sm {
  margin-top: 14px;
  background: var(--accent-12);
  border: 1px solid var(--accent-35);
  color: var(--cyan);
  border-radius: 6px;
  padding: 7px 14px;
  font-size: 12px;
  cursor: pointer;
}
.btn.primary {
  width: 100%;
  background: color-mix(in srgb, var(--cyan) 20%, transparent);
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn-sm {
  margin: 0 8px 0 0;
  padding: 4px 10px;
}
.btn-sm.danger {
  border-color: color-mix(in srgb, var(--red) 40%, transparent);
  color: var(--red);
  background: color-mix(in srgb, var(--red) 8%, transparent);
}
.filters {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
}
.filters .ipt {
  width: 220px;
}
.tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.tbl th,
.tbl td {
  text-align: left;
  padding: 8px 10px;
  border-bottom: 1px solid var(--accent-08);
}
.tbl th {
  color: var(--txt2);
  font-weight: 500;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
}
.tag {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 10px;
  font-size: 11px;
  margin: 10px 8px 0 0;
  border: 1px solid var(--accent-16);
}
.tag.real {
  color: var(--green);
  border-color: color-mix(in srgb, var(--green) 40%, transparent);
}
.tag.fallback {
  color: var(--amber);
  border-color: color-mix(in srgb, var(--amber) 40%, transparent);
}
.impact-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: var(--txt2);
}
.graph {
  width: 100%;
  height: 260px;
}
.empty,
.err {
  font-size: 12px;
  color: var(--txt2);
  padding: 12px 0;
}
.err {
  color: var(--red);
}
</style>
