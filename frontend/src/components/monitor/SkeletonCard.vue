<template>
  <div class="skeleton-card card" :class="sizeClass">
    <div class="sk-line w-40"></div>
    <div class="sk-line w-70"></div>
    <div class="sk-line w-55"></div>
    <div v-if="size !== 'sm'" class="sk-line w-85"></div>
    <div v-if="size === 'lg'" class="sk-bar"></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{ size?: 'sm' | 'md' | 'lg' }>(), { size: 'md' })
const sizeClass = computed(() => `skeleton-${props.size}`)
</script>

<style scoped>
.skeleton-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sk-line {
  height: 12px;
  border-radius: 4px;
  background: linear-gradient(
    90deg,
    var(--track) 25%,
    rgba(34, 227, 255, 0.06) 50%,
    var(--track) 75%
  );
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.w-40 {
  width: 40%;
}
.w-55 {
  width: 55%;
}
.w-70 {
  width: 70%;
}
.w-85 {
  width: 85%;
}
.sk-bar {
  height: 6px;
  border-radius: 3px;
  background: var(--track);
  margin-top: 4px;
  width: 100%;
}
.skeleton-sm .sk-line {
  height: 10px;
}
.skeleton-lg .sk-line {
  height: 14px;
}
@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}
</style>
