<template>
  <div class="pager" v-if="total > 0">
    <span class="pg-info">共 {{ total }} 条 · 第 {{ start }}-{{ end }} 条</span>
    <div class="pg-ctrl">
      <button class="pg-btn" :disabled="page <= 1" @click="go(page - 1)">‹ 上一页</button>
      <template v-for="p in pages" :key="p.key">
        <span v-if="p.gap" class="pg-gap">…</span>
        <button v-else class="pg-btn" :class="{ active: p.page === page }" @click="go(p.page ?? 1)">{{ p.label }}</button>
      </template>
      <button class="pg-btn" :disabled="page >= totalPages" @click="go(page + 1)">下一页 ›</button>
    </div>
    <select class="pg-size" :value="size" @change="onSize($event)">
      <option v-for="s in sizes" :key="s" :value="s">{{ s }}/页</option>
    </select>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  total: number;
  page: number;
  size: number;
  sizes?: number[];
}>();
const emit = defineEmits<{
  (e: "change", page: number): void;
  (e: "size-change", size: number): void;
}>();

const sizes = computed(() => props.sizes ?? [10, 20, 50, 100]);
const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.size)));
const start = computed(() => (props.total === 0 ? 0 : (props.page - 1) * props.size + 1));
const end = computed(() => Math.min(props.total, props.page * props.size));

// 计算要显示的页码: 始终包含 1 / 末页 / 当前页及左右邻居, 中间用 … 省略
const pages = computed(() => {
  const tp = totalPages.value;
  const cur = props.page;
  const wanted = new Set<number>([1, tp, cur, cur - 1, cur + 1]);
  const nums = [...wanted].filter((n) => n >= 1 && n <= tp).sort((a, b) => a - b);
  const out: { key: string; page?: number; label?: string; gap: boolean }[] = [];
  let prev = 0;
  for (const n of nums) {
    if (n - prev > 1) out.push({ key: "gap" + n, gap: true });
    out.push({ key: "p" + n, page: n, label: String(n), gap: false });
    prev = n;
  }
  return out;
});

function go(p: number) {
  if (p >= 1 && p <= totalPages.value && p !== props.page) emit("change", p);
}
function onSize(e: Event) {
  emit("size-change", Number((e.target as HTMLSelectElement).value));
}
</script>

<style scoped>
.pager {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  flex-wrap: wrap;
}
.pg-info { font-size: 12px; color: var(--muted); }
.pg-ctrl { display: flex; align-items: center; gap: 4px; }
.pg-btn {
  min-width: 30px;
  height: 28px;
  padding: 0 9px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt);
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: border-color .15s, color .15s;
}
.pg-btn:hover:not(:disabled):not(.active) { border-color: var(--cyan); }
.pg-btn.active { background: var(--cyan); color: #04222b; border-color: var(--cyan); font-weight: 600; }
.pg-btn:disabled { opacity: .4; cursor: default; }
.pg-gap { color: var(--muted); padding: 0 2px; }
.pg-size {
  margin-left: auto;
  height: 28px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt);
  border-radius: 6px;
  font-size: 12px;
  padding: 0 6px;
  outline: none;
}
</style>
