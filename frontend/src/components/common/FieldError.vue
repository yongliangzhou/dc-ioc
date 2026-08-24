<template>
  <Transition name="fe">
    <div v-if="message" class="field-error" role="alert" :aria-live="'polite'">
      <svg class="fe-icon" viewBox="0 0 16 16" width="13" height="13" aria-hidden="true">
        <circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.5" />
        <path d="M8 4.5v4.2" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
        <circle cx="8" cy="11.3" r="0.9" fill="currentColor" />
      </svg>
      <span class="fe-text">{{ message }}</span>
    </div>
  </Transition>
</template>

<script setup lang="ts">
defineProps<{ message?: string }>()
</script>

<style scoped>
.field-error {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 5px;
  font-size: 12px;
  line-height: 1.4;
  color: #ff6b6b;
  animation: fe-in 0.18s ease;
}
.fe-icon {
  flex: none;
  color: #ff6b6b;
}
.fe-text {
  word-break: break-word;
}
@keyframes fe-in {
  from {
    opacity: 0;
    transform: translateY(-3px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
.fe-enter-active,
.fe-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}
.fe-enter-from,
.fe-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}
</style>
