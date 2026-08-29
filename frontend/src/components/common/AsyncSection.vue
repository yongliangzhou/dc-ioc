<template>
  <div class="async-section">
    <!-- 加载中 -->
    <LoadingState
      v-if="state.loading"
      :variant="skeletonVariant"
      :text="loadingText"
      :rows="skeletonRows"
      :row-height="skeletonRowHeight"
      :min-height="minHeight"
    />

    <!-- 失败: 必须可重试 -->
    <ErrorRetry
      v-else-if="state.error"
      :title="errorTitle"
      :message="state.error"
      :retryable="retryable"
      :retrying="state.retrying"
      :min-height="minHeight"
      @retry="$emit('retry')"
    >
      <template v-if="$slots['error-actions']" #actions>
        <slot name="error-actions" />
      </template>
    </ErrorRetry>

    <!-- 空: 必须给出下一步动作 -->
    <EmptyStateCard
      v-else-if="state.empty"
      :title="emptyTitle"
      :desc="emptyDesc"
      :icon="emptyIcon"
      :min-height="minHeight"
    >
      <template v-if="$slots['empty-actions']" #actions>
        <slot name="empty-actions" />
      </template>
    </EmptyStateCard>

    <!-- 成功 -->
    <slot v-else />
  </div>
</template>

<script setup lang="ts">
/**
 * AsyncSection — 声明式异步区块
 *
 * 把 LoadingState / ErrorRetry / EmptyStateCard 三件套收敛成一个组件，
 * 页面从手写 15 行 if-else 变成一处声明，保证全站状态呈现一致。
 *
 * 用法 A（推荐，直接吃 useAsyncPage 返回对象）：
 *   <AsyncSection :page="alarmsPage" skeleton-variant="skeleton"
 *                 empty-title="暂无告警" @retry="alarmsPage.reload">
 *     <AlarmTable :rows="alarmsPage.data.value" />
 *   </AsyncSection>
 *
 * 用法 B（尚未迁移的页面，逐个传 props）：
 *   <AsyncSection :loading="loading" :error="error" :empty="!list.length" @retry="load">
 */
import { computed, unref, type Component, type Ref } from 'vue'
import LoadingState from './LoadingState.vue'
import ErrorRetry from './ErrorRetry.vue'
import EmptyStateCard from './EmptyStateCard.vue'

/**
 * 结构化最小契约：只依赖四个状态。
 * 声明为 Ref<boolean>/Ref<string> 而非 AsyncPageResult<T>，
 * 避免泛型 Ref<T> 在函数属性上的型变冲突；
 * 同时允许传普通值，便于从「非 useAsyncPage 状态源」（如全局引擎单例）派生。
 */
type MaybeRef<T> = T | Ref<T>
export interface AsyncStateLike {
  loading: MaybeRef<boolean>
  error: MaybeRef<string>
  empty: MaybeRef<boolean>
  retrying?: MaybeRef<boolean>
}

const props = withDefaults(
  defineProps<{
    /** 直接传 useAsyncPage() 的返回对象，优先级高于下列单独 props */
    page?: AsyncStateLike | null
    loading?: boolean
    error?: string
    empty?: boolean
    retrying?: boolean

    skeletonVariant?: 'spinner' | 'skeleton' | 'dots'
    skeletonRows?: number
    skeletonRowHeight?: string
    loadingText?: string

    emptyTitle?: string
    emptyDesc?: string
    emptyIcon?: string | Component

    errorTitle?: string
    retryable?: boolean

    minHeight?: string
  }>(),
  {
    page: null,
    loading: false,
    error: '',
    empty: false,
    retrying: false,
    skeletonVariant: 'skeleton',
    skeletonRows: 4,
    skeletonRowHeight: '16px',
    loadingText: '',
    emptyTitle: '暂无数据',
    emptyDesc: '',
    errorTitle: '加载失败',
    retryable: true,
    minHeight: '180px',
  },
)

defineEmits<{ retry: [] }>()

const state = computed(() => {
  const p = props.page
  return {
    loading: p ? !!unref(p.loading) : props.loading,
    error: p ? unref(p.error) || '' : props.error,
    empty: p ? !!unref(p.empty) : props.empty,
    retrying: p ? !!unref(p.retrying) : props.retrying,
  }
})
</script>

<style scoped>
.async-section {
  width: 100%;
}
</style>
