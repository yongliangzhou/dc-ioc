<template>
  <div class="grid" :class="gridClass">
    <div v-for="(t, i) in tiles" :key="i" class="kpi-card">
      <div class="kpi-label">{{ t.label }}</div>
      <div class="kpi-val" :style="t.color ? { color: t.color } : undefined">{{ t.value }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
export interface MetricTile {
  label: string;
  value: string;
  color?: string;
}
import { computed } from "vue";
const props = withDefaults(defineProps<{ tiles: MetricTile[]; cols?: number }>(), { cols: 6 });
const gridClass = computed(() => `cols-${props.cols ?? 6}`);
</script>

<style scoped>
.grid { display: grid; gap: 10px; margin-bottom: 14px; }
.grid.cols-6 { grid-template-columns: repeat(6, 1fr); }
.grid.cols-5 { grid-template-columns: repeat(5, 1fr); }
.grid.cols-4 { grid-template-columns: repeat(4, 1fr); }
.grid.cols-3 { grid-template-columns: repeat(3, 1fr); }
.kpi-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 10px 12px;
  min-height: 64px;
  display: flex; flex-direction: column; justify-content: center;
}
.kpi-label { font-size: 11px; color: var(--txt2); margin-bottom: 4px; }
.kpi-val { font-size: 20px; font-weight: 800; color: var(--txt); line-height: 1; }
</style>
