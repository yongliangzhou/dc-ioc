<template>
  <div class="empty-state" :style="{ minHeight }">
    <div class="es-icon" v-if="icon" aria-hidden="true">
      <component :is="icon" v-if="isComponent" />
      <svg v-else viewBox="0 0 48 48" width="44" height="44">
        <rect
          x="7"
          y="11"
          width="34"
          height="26"
          rx="4"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        />
        <path d="M7 19h34" stroke="currentColor" stroke-width="2" />
        <path d="M16 28h10" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
      </svg>
    </div>
    <div class="es-title">{{ title }}</div>
    <div v-if="desc" class="es-desc">{{ desc }}</div>
    <div v-if="$slots.actions" class="es-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, type Component } from 'vue'

const props = defineProps<{
  title: string
  desc?: string
  icon?: string | Component
  minHeight?: string
}>()

const isComponent = computed(() => typeof props.icon !== 'string' && props.icon !== undefined)
</script>

<style scoped>
/* 颜色只来自全局 :root token，无硬编码兜底 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  padding: 40px var(--space-5);
  text-align: center;
  color: var(--txt2);
}
.es-icon {
  color: var(--txt3);
  margin-bottom: var(--space-1);
}
.es-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--txt-strong);
}
.es-desc {
  font-size: 12px;
  line-height: 1.6;
  max-width: 320px;
  color: var(--txt2);
}
.es-actions {
  margin-top: var(--space-3);
  display: flex;
  gap: 10px;
}
</style>
