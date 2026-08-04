<template>
  <section class="panel moni-card" :class="{ 'panel--head': hasHead }">
    <header v-if="hasHead" class="panel-head card-head">
      <div class="panel-ct ct">
        <component :is="iconComp" v-if="iconComp" :size="16" class="panel-ico" />
        <slot name="ct">{{ title }}</slot>
      </div>
      <div class="panel-extra"><slot name="extra" /></div>
    </header>
    <div class="panel-body"><slot /></div>
  </section>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue'
import type { Component } from 'vue'
import { Activity, Gauge, Server, Network, Share2, Building2, BookOpen } from 'lucide-vue-next'

const props = defineProps<{ title?: string; icon?: string }>()
const slots = useSlots()

const ICONS: Record<string, Component> = {
  Activity,
  Gauge,
  Server,
  Network,
  Share2,
  Building2,
  BookOpen,
}
const iconComp = computed<Component | null>(() => ICONS[props.icon ?? ''] ?? null)
// 有标题/图标或自定义头部插槽时才渲染头部
const hasHead = computed(() => !!(props.title || props.icon || slots.ct || slots.extra))
</script>

<style scoped>
/* 外观由全局 .moni-card 提供，这里只做布局/对齐补充 */
.panel {
  display: block;
}
.panel-head {
  align-items: center;
}
.panel-ico {
  color: var(--cyan);
  flex: none;
  margin-right: 6px;
}
.panel-ct {
  display: inline-flex;
  align-items: center;
  min-width: 0;
}
.panel-extra {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--txt2);
  flex: none;
  margin-left: auto;
}
.panel-body {
  color: var(--txt);
}
</style>
