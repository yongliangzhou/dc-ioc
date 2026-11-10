<template>
  <LoadingState
    class="card skeleton-adapter"
    variant="skeleton"
    :rows="rows"
    :row-height="rowHeight"
    :min-height="minHeight"
  />
</template>

<script setup lang="ts">
/** 薄适配层：把旧的 size 签名映射到统一 LoadingState 的 skeleton 变体。 */
import { computed } from 'vue'
import LoadingState from '@/components/common/LoadingState.vue'

const props = withDefaults(defineProps<{ size?: 'sm' | 'md' | 'lg' }>(), { size: 'md' })
const rows = computed(() => (props.size === 'sm' ? 3 : props.size === 'lg' ? 5 : 4))
const rowHeight = computed(() =>
  props.size === 'sm' ? '10px' : props.size === 'lg' ? '14px' : '12px',
)
const minHeight = computed(() =>
  props.size === 'sm' ? '80px' : props.size === 'lg' ? '180px' : '120px',
)
</script>
