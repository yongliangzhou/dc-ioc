<template>
  <div class="empty-state">
    <span class="empty-icon">{{ icon }}</span>
    <span class="empty-text">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    text?: string
    icon?: string
  }>(),
  {
    text: '暂无数据',
    icon: '📊',
  },
)
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 16px;
  color: var(--txt3);
}
.empty-icon {
  font-size: 32px;
  opacity: 0.5;
}
.empty-text {
  font-size: 13px;
}
</style>
