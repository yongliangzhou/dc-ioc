<template>
  <teleport to="body">
    <div class="toast-wrap">
      <transition-group name="toast">
        <div
          v-for="t in toast.items"
          :key="t.id"
          class="toast"
          :class="t.type"
          @click="toast.remove(t.id)"
        >
          <span class="dot" />
          <span class="msg">{{ t.message }}</span>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { useToast } from "@/hooks/useToast";
const toast = useToast();
</script>

<style scoped>
.toast-wrap {
  position: fixed;
  top: 18px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}
.toast {
  pointer-events: auto;
  cursor: pointer;
  min-width: 240px;
  max-width: 460px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 10px;
  font-size: 13px;
  color: var(--txt);
  background: linear-gradient(180deg, var(--panel), var(--bg2));
  border: 1px solid var(--line);
  box-shadow: 0 12px 32px rgba(0, 0, 0, .45);
  backdrop-filter: blur(4px);
}
.toast .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex: none;
  box-shadow: 0 0 8px currentColor;
}
.toast.success { border-color: rgba(43, 212, 122, .5); }
.toast.success .dot { background: var(--green); color: var(--green); }
.toast.error { border-color: rgba(242, 63, 63, .5); }
.toast.error .dot { background: var(--red); color: var(--red); }
.toast.warning { border-color: rgba(255, 176, 32, .5); }
.toast.warning .dot { background: var(--amber); color: var(--amber); }
.toast.info { border-color: rgba(34, 211, 238, .5); }
.toast.info .dot { background: var(--cyan); color: var(--cyan); }
.toast .msg { line-height: 1.4; word-break: break-word; }

.toast-enter-active,
.toast-leave-active { transition: all .25s ease; }
.toast-enter-from { opacity: 0; transform: translateY(-8px); }
.toast-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
