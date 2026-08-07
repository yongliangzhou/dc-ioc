<template>
  <div class="placeholder-view">
    <div class="view-head">
      <h1>{{ tl('nav.datacenter') }}</h1>
      <span class="sub">{{ tl('placeholder.sub') }}</span>
    </div>
    <Panel :title="tl('placeholder.title')">
      <div class="flex center">
        <span class="muted">{{ tl('placeholder.desc') }}</span>
      </div>
    </Panel>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Panel from '@/components/common/Panel.vue'

const { t: tl } = useI18n()
</script>

<style scoped>
.placeholder-view {
  padding: 4px;
}
.flex.center {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}
.muted {
  color: var(--text-muted, #8a94a6);
}
</style>
