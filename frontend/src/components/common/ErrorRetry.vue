<template>
  <div class="error-retry" :style="{ minHeight }">
    <div class="er-icon" aria-hidden="true">
      <svg viewBox="0 0 24 24" width="32" height="32">
        <path
          d="M12 3a9 9 0 0 1 8.49 6"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
        <path d="M21 3v5h-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
        <path
          d="M12 21a9 9 0 0 1-8.49-6"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        />
        <path d="M3 21v-5h5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </div>
    <div class="er-title">{{ title }}</div>
    <div v-if="message" class="er-message">{{ message }}</div>
    <div class="er-actions">
      <button v-if="retryable" class="er-btn primary" :disabled="retrying" @click="$emit('retry')">
        <span v-if="retrying" class="er-btn-spin"></span>
        {{ retrying ? '重试中…' : '重新加载' }}
      </button>
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    title?: string
    message?: string
    retryable?: boolean
    retrying?: boolean
    minHeight?: string
  }>(),
  { title: '加载失败', retryable: true, retrying: false, minHeight: '200px' },
)

defineEmits<{ retry: [] }>()
</script>

<style scoped>
.error-retry {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 32px 24px;
  text-align: center;
}
.er-icon {
  color: #ffb020;
  margin-bottom: 2px;
}
.er-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--txt, #e6edf3);
}
.er-message {
  font-size: 12px;
  line-height: 1.6;
  max-width: 360px;
  color: var(--txt2, #8892b0);
  word-break: break-word;
}
.er-actions {
  margin-top: 10px;
  display: flex;
  gap: 10px;
}
.er-btn {
  padding: 8px 22px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: transparent;
  border: 1px solid var(--line, rgba(255, 255, 255, 0.15));
  color: var(--txt2, #8892b0);
  transition: all 0.2s;
}
.er-btn:hover:not(:disabled) {
  color: var(--txt, #e6edf3);
  border-color: rgba(255, 255, 255, 0.3);
}
.er-btn.primary {
  background: rgba(66, 165, 245, 0.15);
  border-color: rgba(66, 165, 245, 0.4);
  color: #42a5f5;
}
.er-btn.primary:hover:not(:disabled) {
  background: rgba(66, 165, 245, 0.25);
}
.er-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.er-btn-spin {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid rgba(66, 165, 245, 0.3);
  border-top-color: #42a5f5;
  animation: er-spin 0.6s linear infinite;
}
@keyframes er-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
