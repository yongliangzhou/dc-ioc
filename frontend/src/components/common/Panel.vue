<template>
  <section class="panel">
    <header class="panel-head">
      <div class="panel-title">
        <component :is="iconComp" :size="16" class="panel-ico" />
        <h3>{{ title }}</h3>
      </div>
      <div class="panel-extra"><slot name="extra" /></div>
    </header>
    <div class="panel-body"><slot /></div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Component } from "vue";
import {
  Activity,
  Gauge,
  Server,
  Network,
  Share2,
  Building2,
  BookOpen,
} from "lucide-vue-next";

const props = defineProps<{ title: string; icon?: string }>();

const ICONS: Record<string, Component> = {
  Activity,
  Gauge,
  Server,
  Network,
  Share2,
  Building2,
  BookOpen,
};
const iconComp = computed<Component>(() => ICONS[props.icon ?? ""] ?? Activity);
</script>

<style scoped>
.panel {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 16px;
}
.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.panel-ico {
  color: var(--cyan);
  flex: none;
}
.panel-title h3 {
  font-size: 14px;
  font-weight: 700;
  margin: 0;
  color: var(--txt);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.panel-extra {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--txt2);
  flex: none;
}
.panel-body {
  color: var(--txt);
}
</style>
