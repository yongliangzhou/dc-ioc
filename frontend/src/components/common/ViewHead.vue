<template>
  <header class="view-head">
    <div class="vh-text">
      <h1 class="vh-title">{{ title }}</h1>
      <p class="vh-sub" v-if="sub">{{ sub }}</p>
    </div>
    <div class="vh-actions"><slot name="actions" /></div>
  </header>
</template>

<script setup lang="ts">
defineProps<{ title: string; sub?: string }>();
</script>

<style scoped>
.view-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 4px;
}
.vh-text {
  min-width: 0;
}
.vh-title {
  font-size: 20px;
  font-weight: 800;
  margin: 0;
  color: var(--txt);
}
.vh-sub {
  font-size: 12px;
  color: var(--txt3);
  margin: 4px 0 0;
}
.vh-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  margin-left: auto;
  flex: none;
}
</style>
