<template>
  <div v-if="count > 0" class="error-banner" role="alert">
    <AlertTriangle :size="15" class="eb-icon" />
    <div class="eb-body">
      <span class="eb-title">
        {{ count }} 项数据加载失败
        <span v-if="labels.length" class="eb-labels">· {{ labels.join('、') }}</span>
      </span>
      <span class="eb-desc">页面其余内容仍为最近一次成功数据，可能影响判断，建议立即重试。</span>
    </div>
    <div class="eb-actions">
      <button class="eb-btn primary" :disabled="retrying" @click="$emit('retry')">
        <span v-if="retrying" class="eb-spin" />
        {{ retrying ? '重试中…' : '重试失败项' }}
      </button>
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ErrorBanner — 部分失败汇总横幅
 *
 * 多数据源页面（如驾驶舱、健康报告）允许"部分失败仍渲染"，
 * 但绝不允许"静默降级"：失败项必须在页面顶部显式露出并可一键重试。
 */
import { AlertTriangle } from 'lucide-vue-next'

withDefaults(
  defineProps<{
    /** 失败项数量，0 时不渲染 */
    count: number
    /** 失败项名称，用于文案里说清是哪几项 */
    labels?: string[]
    retrying?: boolean
  }>(),
  { labels: () => [], retrying: false },
)

defineEmits<{ retry: [] }>()
</script>

<style scoped>
.error-banner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 12px;
  border-radius: 10px;
  background: color-mix(in srgb, var(--amber) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--amber) 35%, transparent);
  color: var(--txt-strong);
}
.eb-icon {
  color: var(--amber);
  flex-shrink: 0;
}
.eb-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.eb-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--amber);
}
.eb-labels {
  font-weight: 400;
  color: var(--amber);
}
.eb-desc {
  font-size: 11px;
  color: var(--txt);
  line-height: 1.5;
}
.eb-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.eb-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 7px;
  font-size: 12px;
  cursor: pointer;
  border: 1px solid transparent;
  background: color-mix(in srgb, var(--amber) 18%, transparent);
  border-color: color-mix(in srgb, var(--amber) 45%, transparent);
  color: var(--amber);
  transition: all 0.18s;
  white-space: nowrap;
}
.eb-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--amber) 30%, transparent);
}
.eb-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.eb-spin {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  border: 2px solid color-mix(in srgb, var(--amber) 30%, transparent);
  border-top-color: var(--amber-line);
  animation: eb-rotate 0.6s linear infinite;
}
@keyframes eb-rotate {
  to {
    transform: rotate(360deg);
  }
}

@media (max-width: 640px) {
  .error-banner {
    flex-wrap: wrap;
  }
  .eb-actions {
    width: 100%;
  }
}
</style>
