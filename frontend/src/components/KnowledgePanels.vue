<script setup lang="ts">
import type { PowerKnowledge } from '@/types'

defineProps<{ knowledge?: PowerKnowledge | null }>()
</script>

<template>
  <template v-if="knowledge">
    <!-- 设计 / 告警阈值 -->
    <div v-if="knowledge.thresholds && knowledge.thresholds.length" class="card">
      <div class="section-title"><span class="bar"></span>设计 / 告警阈值</div>
      <div class="kv-grid">
        <div v-for="t in knowledge.thresholds" :key="t.k" class="kv">
          <span class="k">{{ t.k }}</span>
          <span class="v">{{ t.v }}</span>
          <span v-if="t.note" class="note">{{ t.note }}</span>
        </div>
      </div>
    </div>

    <!-- 系统架构与组成 -->
    <div v-if="knowledge.arch" class="card">
      <div class="section-title"><span class="bar"></span>系统架构与组成</div>
      <p class="design">{{ knowledge.arch.design }}</p>
      <div class="chips">
        <span v-for="c in knowledge.arch.components" :key="c" class="chip">{{ c }}</span>
      </div>
      <p v-if="knowledge.arch.redundancy" class="redundancy">
        冗余配置：{{ knowledge.arch.redundancy }}
      </p>
    </div>

    <!-- 控制 / 切换逻辑 -->
    <div v-for="g in knowledge.logic || []" :key="g.title" class="card">
      <div class="section-title"><span class="bar"></span>{{ g.title }}</div>
      <div class="logic-list">
        <div v-for="s in g.steps" :key="s.step" class="logic-step">
          <span class="step-no">{{ s.step }}</span>
          <span class="step-text">{{ s.text }}</span>
          <span v-if="s.ok !== undefined" class="ok" :class="s.ok ? 'ok-y' : 'ok-n'">{{
            s.ok ? '满足' : '未满足'
          }}</span>
        </div>
      </div>
    </div>

    <!-- 故障锁定知识库 -->
    <div v-if="knowledge.faults && knowledge.faults.length" class="card">
      <div class="section-title"><span class="bar"></span>故障锁定知识库</div>
      <table class="fault-table">
        <thead>
          <tr>
            <th>序号</th>
            <th>故障</th>
            <th>锁定 / 影响</th>
            <th>处置动作</th>
            <th>复位</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in knowledge.faults" :key="f.no">
            <td>{{ f.no }}</td>
            <td>{{ f.fault }}</td>
            <td>{{ f.lock }}</td>
            <td>{{ f.action }}</td>
            <td>
              <span class="tag" :class="f.manualReset ? 'a' : 'g'">{{
                f.manualReset ? '人工复位' : '自动'
              }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="knowledge.note" class="knote">{{ knowledge.note }}</p>
  </template>
</template>

<style scoped>
/* 暗色主题卡片：复用全局变量，避免浅色 callout 与暗色主题割裂（N6 修复） */
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 16px;
}
.bar {
  width: 4px;
  height: 14px;
  background: var(--cyan);
  border-radius: 2px;
}
.kv-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 4px 18px;
}
.kv {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 0;
  border-bottom: 1px dashed var(--line);
}
.k {
  font-size: 12px;
  color: var(--txt2);
}
.v {
  font-size: 14px;
  color: var(--txt);
  font-weight: 600;
}
.note {
  font-size: 11px;
  color: var(--txt3);
}
.design {
  font-size: 13px;
  color: var(--txt2);
  line-height: 1.6;
  margin: 0 0 10px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  background: var(--badge-bg);
  color: var(--cyan);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 3px 10px;
  font-size: 12px;
}
.redundancy {
  font-size: 12px;
  color: var(--txt2);
  margin: 10px 0 0;
}
.logic-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.logic-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: var(--txt2);
  line-height: 1.5;
}
.step-no {
  flex: 0 0 auto;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--cyan);
  color: #04121f;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}
.step-text {
  flex: 1;
}
.ok {
  flex: 0 0 auto;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 999px;
}
.ok-y {
  background: rgba(43, 212, 122, 0.12);
  color: var(--green);
}
.ok-n {
  background: rgba(255, 77, 94, 0.12);
  color: var(--red);
}
.fault-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.fault-table th {
  text-align: left;
  background: var(--panel2);
  color: var(--txt2);
  padding: 6px 8px;
  border: 1px solid var(--line);
}
.fault-table td {
  padding: 6px 8px;
  border: 1px solid var(--line);
  color: var(--txt2);
  vertical-align: top;
}
.knote {
  font-size: 12px;
  color: var(--txt2);
  font-style: italic;
}
</style>
