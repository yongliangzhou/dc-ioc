<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('nav.risk') }}</h1>
      <span class="sub">{{ tl('风险识别与评估管控') }}</span>
    </div>
    <div class="grid cols-5" v-if="stats">
      <MetricCard
        metric-name="risk-total"
        :label="tl('风险总数')"
        :value="stats.total"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="risk-open"
        :label="tl('未关闭')"
        :value="stats.open"
        :quality="stats.open ? 'uncertain' : 'good'"
        :online="true"
      />
      <MetricCard
        metric-name="risk-mitigated"
        :label="tl('已缓解')"
        :value="stats.mitigated"
        quality="good"
        :online="true"
      />
      <MetricCard
        metric-name="risk-critical"
        :label="tl('严重')"
        :value="stats.critical"
        :quality="stats.critical ? 'bad' : 'good'"
        :severity="'crit'"
        :online="true"
      />
      <MetricCard
        metric-name="risk-high"
        :label="tl('高风险')"
        :value="stats.high"
        :quality="stats.high ? 'uncertain' : 'good'"
        :severity="'warn'"
        :online="true"
      />
    </div>
    <Panel style="margin-top: 16px">
      <h5 class="section-title">{{ tl('风险评估列表') }}</h5>
      <div class="tbl" v-if="risks.length">
        <div class="tbl-head">
          <span class="col w-risk-code">{{ tl('编号') }}</span
          ><span class="col w-risk-title">{{ tl('标题') }}</span
          ><span class="col w-risk-cat">{{ tl('类别') }}</span
          ><span class="col w-risk-sev">{{ tl('严重性') }}</span
          ><span class="col w-risk-prob">{{ tl('可能性') }}</span
          ><span class="col w-risk-stat">{{ tl('状态') }}</span
          ><span class="col w-risk-mit">{{ tl('缓解措施') }}</span>
        </div>
        <div v-for="r in risks" :key="r.id" class="tbl-row">
          <span class="col w-risk-code">{{ r.code }}</span>
          <span class="col w-risk-title fw">{{ r.title }}</span>
          <span class="col w-risk-cat muted">{{ r.category }}</span>
          <span class="col w-risk-sev"
            ><span
              class="pill-tag"
              :class="r.severity === 'critical' ? 'r' : r.severity === 'high' ? 'a' : 'g'"
              >{{ sevLabel(r.severity) }}</span
            ></span
          >
          <span class="col w-risk-prob muted">{{ probLabel(r.probability) }}</span>
          <span class="col w-risk-stat"
            ><span class="pill-tag" :class="r.status === 'open' ? 'a' : 'g'">{{
              r.status === 'open' ? '未关闭' : '已缓解'
            }}</span></span
          >
          <span class="col w-risk-mit muted">{{ r.mitigation || '-' }}</span>
        </div>
      </div>
      <div class="empty" v-else>{{ tl('暂无风险') }}</div>
    </Panel>
    <Panel v-if="!risks.length && !e"
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
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import MetricCard from '@/components/common/MetricCard.vue'
import Panel from '@/components/common/Panel.vue'
import { getRisks, getRiskStats, type RiskView, type RiskStats } from '@/api/risk'
const risks = ref<RiskView[]>([])
const stats = ref<RiskStats | null>(null)
const e = ref('')
function sevLabel(s: string) {
  const m: Record<string, string> = { low: '低', medium: '中', high: '高', critical: '严重' }
  return m[s] || s
}
function probLabel(p: string) {
  const m: Record<string, string> = { low: '低', medium: '中', high: '高' }
  return m[p] || p
}
async function load() {
  try {
    const [r, s] = await Promise.all([getRisks(), getRiskStats()])
    risks.value = r
    stats.value = s
  } catch (ex: any) {
    e.value = ex?.message || String(ex)
  }
}
onMounted(load)
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
.w-risk-code {
  width: 100px;
}
.w-risk-title {
  width: 200px;
}
.w-risk-cat {
  width: 90px;
}
.w-risk-sev {
  width: 70px;
}
.w-risk-prob {
  width: 70px;
}
.w-risk-stat {
  width: 80px;
}
.w-risk-mit {
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
.pill-tag.g {
  background: rgba(82, 196, 26, 0.12);
  color: var(--green);
}
.pill-tag.a {
  background: rgba(250, 173, 20, 0.12);
  color: var(--amber);
}
.pill-tag.r {
  background: rgba(255, 77, 79, 0.12);
  color: var(--red);
}
.empty {
  text-align: center;
  padding: 32px;
  color: var(--muted);
  font-size: 13px;
}
</style>
