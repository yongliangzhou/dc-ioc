<template>
  <div class="loading-state" :class="variant" :style="{ minHeight }">
    <template v-if="variant === 'spinner'">
      <div class="ls-spinner" aria-hidden="true"></div>
      <div v-if="text" class="ls-text">{{ text }}</div>
    </template>
    <template v-else-if="variant === 'skeleton'">
      <div v-for="n in rows" :key="n" class="ls-skel-row" :style="{ height: rowHeight }">
        <div class="ls-skel-block" :style="{ width: blockWidth(n) }"></div>
      </div>
      <div v-if="text" class="ls-text">{{ text }}</div>
    </template>
    <template v-else>
      <div class="ls-dots"><span></span><span></span><span></span></div>
      <div v-if="text" class="ls-text">{{ text }}</div>
    </template>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    variant?: 'spinner' | 'skeleton' | 'dots'
    text?: string
    rows?: number
    rowHeight?: string
    minHeight?: string
  }>(),
  { variant: 'spinner', rows: 4, rowHeight: '16px', minHeight: '120px' },
)

function blockWidth(n: number) {
  // 错落宽度, 更像真实表格
  const widths = ['92%', '78%', '85%', '70%', '88%', '64%', '80%', '72%']
  return widths[(n - 1) % widths.length]
}
</script>

<style scoped>
/* 颜色只来自全局 :root token，无硬编码兜底（亮色主题同样可见） */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: var(--space-5);
  color: var(--txt2);
}
.ls-text {
  font-size: 13px;
  color: var(--txt2);
  letter-spacing: 0.02em;
}
.ls-spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2.5px solid var(--line);
  border-top-color: var(--cyan);
  animation: ls-spin 0.7s linear infinite;
}
@keyframes ls-spin {
  to {
    transform: rotate(360deg);
  }
}
.ls-dots {
  display: flex;
  gap: 6px;
}
.ls-dots span {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--cyan);
  animation: ls-bounce 1.1s infinite ease-in-out;
}
.ls-dots span:nth-child(2) {
  animation-delay: 0.15s;
}
.ls-dots span:nth-child(3) {
  animation-delay: 0.3s;
}
@keyframes ls-bounce {
  0%,
  80%,
  100% {
    transform: scale(0.5);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
.ls-skel-row {
  width: 100%;
  display: flex;
  align-items: center;
}
.ls-skel-block {
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--track) 25%, var(--accent-08) 37%, var(--track) 63%);
  background-size: 400% 100%;
  animation: ls-shimmer 1.3s ease infinite;
}
@keyframes ls-shimmer {
  0% {
    background-position: 100% 0;
  }
  100% {
    background-position: -100% 0;
  }
}
</style>
