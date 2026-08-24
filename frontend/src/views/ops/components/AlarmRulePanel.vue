<template>
  <div>
    <div class="section-title">{{ tl('告警规则列表') }} · {{ tl('按类别分组') }}</div>
    <div class="grid cols-2">
      <div
        v-for="cat in ruleCats"
        :key="cat"
        class="pwr-card"
        :class="catIndex(cat) === 0 ? 'primary' : ''"
      >
        <div class="pwr-head">
          <div>
            <h3>{{ cat }}</h3>
            <span class="sub">{{ ruleCatCount(cat) }} {{ tl('条规则') }}</span>
          </div>
          <span class="pill g" v-if="rulesByCat(cat).every((r) => r.enabled)">{{
            tl('全部启用')
          }}</span>
          <span class="pill a" v-else>{{ tl('部分停用') }}</span>
        </div>
        <div style="margin-top: 8px">
          <div v-for="rule in rulesByCat(cat)" :key="rule.id" class="rule-row">
            <div class="rule-info">
              <div class="rule-name">
                <span class="dot" :class="rule.enabled ? 'g' : 'a'"></span>
                <span class="mono">{{ rule.metric }}</span>
                <span class="tag tiny">{{ rule.ruleCode || rule.category }}</span>
              </div>
              <div class="rule-meta">
                <span class="mono"
                  >{{ band(rule.warnLo, rule.warnHi) }} / {{ band(rule.critLo, rule.critHi) }}</span
                >
              </div>
            </div>
            <div class="rule-actions">
              <button
                class="rule-btn"
                :class="rule.enabled ? 'on' : 'off'"
                @click="$emit('toggle', rule)"
                :title="rule.enabled ? tl('点击停用') : tl('点击启用')"
              >
                {{ rule.enabled ? tl('已启用') : tl('已停用') }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { AlarmRuleDef } from '@/types'

const { t: tl } = useI18n()
const props = defineProps<{ rules: AlarmRuleDef[] }>()
defineEmits<{ (e: 'toggle', rule: AlarmRuleDef): void }>()

const ruleCats = computed(() => Array.from(new Set(props.rules.map((r) => r.category))))
function catIndex(c: string) {
  return ruleCats.value.indexOf(c)
}
function rulesByCat(c: string) {
  return props.rules.filter((r) => r.category === c)
}
function ruleCatCount(c: string) {
  return rulesByCat(c).length
}
function band(lo: number | null | undefined, hi: number | null | undefined): string {
  if (lo == null && hi == null) return '—'
  const f = (v: typeof lo) => (v == null ? '∞' : String(v))
  return `${f(lo)}~${f(hi)}`
}
</script>

<style scoped>
.grid {
  display: grid;
  gap: 12px;
}
.cols-2 {
  grid-template-columns: repeat(2, 1fr);
}
.pwr-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 12px;
}
.pwr-card.primary {
  border-color: var(--cyan);
}
.pwr-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.pwr-head h3 {
  font-size: 14px;
  margin: 0;
}
.sub {
  font-size: 11px;
  color: var(--txt3);
}

.rule-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-top: 1px dashed var(--line);
}
.rule-row:first-child {
  border-top: none;
}
.rule-name {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--txt3);
}
.dot.g {
  background: var(--green);
}
.dot.a {
  background: var(--amber);
}
.mono {
  font-family: ui-monospace, Menlo, Consolas, monospace;
}
.tag.tiny {
  font-size: 10px;
}
.rule-meta {
  font-size: 11px;
  color: var(--txt3);
  margin-top: 2px;
}
.rule-btn {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  border: 1px solid var(--line);
  cursor: pointer;
  background: var(--bg2);
}
.rule-btn.on {
  color: var(--green);
  border-color: var(--green);
}
.rule-btn.off {
  color: var(--txt2);
}
</style>
