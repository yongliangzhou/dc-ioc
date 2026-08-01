<template>
  <div class="card" v-if="title || items.length">
    <div class="ct" v-if="title">{{ title }}</div>
    <div class="kvs">
      <template v-for="(it, i) in items" :key="i">
        <span class="k">{{ it.k }}</span>
        <span class="v" :class="{ 'v-strong': it.strong, 'v-ok': it.ok, 'v-warn': it.warn, 'v-err': it.err }">{{ it.v }}</span>
      </template>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
export interface KvsItem {
  k: string;
  v: string;
  strong?: boolean;
  ok?: boolean;
  warn?: boolean;
  err?: boolean;
}
defineProps<{
  title?: string;
  items: KvsItem[];
}>();
</script>

<style scoped>
.kvs {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 6px 12px;
  font-size: 12.5px;
}
.kvs .k { color: var(--txt2); white-space: nowrap; }
.kvs .v { color: var(--txt); text-align: right; }
.v-strong { font-weight: 700; color: var(--cyan); }
.v-ok { color: var(--green); }
.v-warn { color: var(--amber); }
.v-err { color: var(--red); }
</style>
