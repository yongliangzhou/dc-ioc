<template>
  <EmptyStateCard :title="text" :icon="resolvedIcon" :min-height="minHeight">
    <template v-if="$slots.actions" #actions><slot name="actions" /></template>
  </EmptyStateCard>
</template>

<script setup lang="ts">
/** 薄适配层：保留旧的 text/icon 签名，实际渲染统一空态组件。
 *  旧版默认 emoji 图标 📊 已移除，改用 lucide-vue-next 的 Inbox 图标。 */
import { computed } from 'vue'
import { Inbox } from 'lucide-vue-next'
import EmptyStateCard from '@/components/common/EmptyStateCard.vue'

const props = withDefaults(defineProps<{ text?: string; icon?: string; minHeight?: string }>(), {
  text: '暂无数据',
  minHeight: '160px',
})

const resolvedIcon = computed(() =>
  props.icon && typeof props.icon !== 'string' ? props.icon : Inbox,
)
</script>
