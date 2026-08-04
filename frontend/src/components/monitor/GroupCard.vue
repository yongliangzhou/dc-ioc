<template>
  <div class="group-card card" :class="{ collapsed: isCollapsed }">
    <div class="gc-header" @click="toggle">
      <div class="gc-title">
        <span class="gc-dot" :style="{ background: dotColor }"></span>
        <span class="gc-name">{{ title }}</span>
        <span v-if="subtitle" class="gc-sub">{{ subtitle }}</span>
      </div>
      <div class="gc-actions">
        <slot name="header-actions" />
        <span class="gc-toggle">{{ isCollapsed ? '展开' : '收起' }}</span>
      </div>
    </div>
    <div class="gc-body" v-show="!isCollapsed">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

withDefaults(
  defineProps<{
    title: string
    subtitle?: string
    dotColor?: string
    defaultCollapsed?: boolean
  }>(),
  {
    dotColor: 'var(--cyan)',
    defaultCollapsed: false,
  },
)

const isCollapsed = ref(false) // start expanded by default; use defaultCollapsed if needed
const toggle = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>

<style scoped>
.group-card {
  margin-bottom: 10px;
}

.gc-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  user-select: none;
}
.gc-title {
  display: flex;
  align-items: center;
  gap: 8px;
}
.gc-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.gc-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--txt);
}
.gc-sub {
  font-size: 11px;
  color: var(--txt2);
}
.gc-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.gc-toggle {
  font-size: 11px;
  color: var(--txt3);
}
.gc-body {
  margin-top: 12px;
}
.collapsed .gc-body {
  display: none;
}
</style>
