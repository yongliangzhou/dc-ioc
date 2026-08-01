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
      <p v-if="knowledge.arch.redundancy" class="redundancy">冗余配置：{{ knowledge.arch.redundancy }}</p>
    </div>

    <!-- 控制 / 切换逻辑 -->
    <div v-for="g in (knowledge.logic || [])" :key="g.title" class="card">
      <div class="section-title"><span class="bar"></span>{{ g.title }}</div>
      <div class="logic-list">
        <div v-for="s in g.steps" :key="s.step" class="logic-step">
          <span class="step-no">{{ s.step }}</span>
          <span class="step-text">{{ s.text }}</span>
          <span v-if="s.ok !== undefined" class="ok" :class="s.ok ? 'ok-y' : 'ok-n'">{{ s.ok ? '满足' : '未满足' }}</span>
        </div>
      </div>
    </div>

    <!-- 故障锁定知识库 -->
    <div v-if="knowledge.faults && knowledge.faults.length" class="card">
      <div class="section-title"><span class="bar"></span>故障锁定知识库</div>
      <table class="fault-table">
        <thead>
          <tr><th>序号</th><th>故障</th><th>锁定 / 影响</th><th>处置动作</th><th>复位</th></tr>
        </thead>
        <tbody>
          <tr v-for="f in knowledge.faults" :key="f.no">
            <td>{{ f.no }}</td>
            <td>{{ f.fault }}</td>
            <td>{{ f.lock }}</td>
            <td>{{ f.action }}</td>
            <td>{{ f.manualReset ? '人工复位' : '自动' }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="knowledge.note" class="knote">{{ knowledge.note }}</p>
  </template>
</template>

<style scoped>
.card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; margin-bottom: 16px; }
.section-title { font-size: 14px; font-weight: 600; color: #0f172a; display: flex; align-items: center; gap: 8px; margin-bottom: 12px; }
.bar { width: 4px; height: 14px; background: #38bdf8; border-radius: 2px; }
.kv-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 4px 18px; }
.kv { display: flex; flex-direction: column; gap: 2px; padding: 6px 0; border-bottom: 1px dashed #e2e8f0; }
.k { font-size: 12px; color: #64748b; }
.v { font-size: 14px; color: #0f172a; font-weight: 600; }
.note { font-size: 11px; color: #94a3b8; }
.design { font-size: 13px; color: #334155; line-height: 1.6; margin: 0 0 10px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; border-radius: 999px; padding: 3px 10px; font-size: 12px; }
.redundancy { font-size: 12px; color: #475569; margin: 10px 0 0; }
.logic-list { display: flex; flex-direction: column; gap: 8px; }
.logic-step { display: flex; align-items: flex-start; gap: 10px; font-size: 13px; color: #334155; line-height: 1.5; }
.step-no { flex: 0 0 auto; width: 22px; height: 22px; border-radius: 50%; background: #38bdf8; color: #fff; font-size: 12px; display: flex; align-items: center; justify-content: center; font-weight: 600; }
.step-text { flex: 1; }
.ok { flex: 0 0 auto; font-size: 11px; padding: 1px 8px; border-radius: 999px; }
.ok-y { background: #dcfce7; color: #15803d; }
.ok-n { background: #fee2e2; color: #b91c1c; }
.fault-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.fault-table th { text-align: left; background: #f1f5f9; color: #475569; padding: 6px 8px; border: 1px solid #e2e8f0; }
.fault-table td { padding: 6px 8px; border: 1px solid #e2e8f0; color: #334155; vertical-align: top; }
.knote { font-size: 12px; color: #64748b; font-style: italic; }
</style>
