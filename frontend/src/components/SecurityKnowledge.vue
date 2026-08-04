<script setup lang="ts">
interface LogicStep {
  step: number
  text: string
  ok?: boolean
}
interface LogicItem {
  title: string
  steps: LogicStep[]
}
interface FaultItem {
  no: number
  fault: string
  lock: string
  action: string
  manualReset?: boolean
}
interface Knowledge {
  thresholds?: { k: string; v: string; note?: string }[]
  arch?: { components: string[]; design: string; redundancy: string }
  logic?: LogicItem[]
  faults?: FaultItem[]
  note?: string
}

defineProps<{
  knowledge: Knowledge
  title?: string
  logicTitle?: string
  resetHeader?: string
}>()
</script>

<template>
  <div
    v-if="
      knowledge?.thresholds?.length ||
      knowledge?.arch ||
      knowledge?.logic?.length ||
      knowledge?.faults?.length
    "
    class="know-grid"
  >
    <div v-if="knowledge.thresholds?.length" class="know-col">
      <h4>设计阈值</h4>
      <ul>
        <li v-for="t in knowledge.thresholds" :key="t.k">
          <b>{{ t.k }}</b
          >：{{ t.v }}<em v-if="t.note">（{{ t.note }}）</em>
        </li>
      </ul>
    </div>
    <div v-if="knowledge.arch" class="know-col">
      <h4>架构组成</h4>
      <p>{{ knowledge.arch.design }}</p>
      <ul>
        <li v-for="c in knowledge.arch.components" :key="c">{{ c }}</li>
      </ul>
      <p class="redundancy">冗余：{{ knowledge.arch.redundancy }}</p>
    </div>
    <div v-if="knowledge.logic?.length" class="know-col">
      <h4>{{ logicTitle || '联动逻辑' }}</h4>
      <div v-for="l in knowledge.logic" :key="l.title" class="logic">
        <b>{{ l.title }}</b>
        <ol>
          <li v-for="st in l.steps" :key="st.step" :class="{ ok: st.ok }">{{ st.text }}</li>
        </ol>
      </div>
    </div>
    <div v-if="knowledge.faults?.length" class="know-col">
      <h4>故障锁定表</h4>
      <table class="fault-tbl">
        <thead>
          <tr>
            <th>故障</th>
            <th>锁定</th>
            <th>处理</th>
            <th>{{ resetHeader || '复位' }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in knowledge.faults" :key="f.no">
            <td>{{ f.fault }}</td>
            <td>{{ f.lock }}</td>
            <td>{{ f.action }}</td>
            <td>
              <span class="tag" :class="f.manualReset ? 'crit' : 'ok'">{{
                f.manualReset ? '需' : '否'
              }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="knote" v-if="knowledge.note">{{ knowledge.note }}</p>
  </div>
</template>

<style scoped>
.know-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.know-col h4 {
  margin: 0 0 6px;
  font-size: 13px;
}
.know-col ul {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
  color: var(--text-2);
}
.know-col p {
  font-size: 12px;
  color: var(--text-2);
  margin: 4px 0;
}
.redundancy {
  color: #3f9fcf;
}
.logic {
  margin-bottom: 8px;
}
.logic ol {
  margin: 4px 0 0;
  padding-left: 18px;
  font-size: 12px;
  color: var(--text-2);
}
.logic li.ok::marker {
  content: '✓ ';
}
.fault-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.fault-tbl th,
.fault-tbl td {
  border: 1px solid var(--border);
  padding: 3px 5px;
  text-align: left;
}
.knote {
  grid-column: 1 / -1;
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--text-2);
}

@media (max-width: 1100px) {
  .know-grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
