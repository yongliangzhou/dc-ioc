<template>
  <teleport to="body">
    <div v-if="open" class="dm-mask" @click.self="close">
      <div class="dm-modal">
        <div class="dm-head">
          <h3>{{ title }}</h3>
          <button class="dm-x" @click="close">✕</button>
        </div>
        <div class="dm-body">
          <div class="dm-row" v-for="(r, i) in rows" :key="i">
            <span class="dm-k">{{ r.label }}</span>
            <span class="dm-v" :style="r.color ? { color: r.color } : {}">{{ r.value }}</span>
          </div>
          <div v-if="extra" class="dm-extra">
            <b>{{ extraTitle || "说明" }}</b>
            <p>{{ extra }}</p>
          </div>
          <slot name="extra-append" />
        </div>
        <div class="dm-foot">
          <button class="dm-btn" @click="close">关闭</button>
          <slot name="footer" />
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
export interface DetailRow { label: string; value: string | number; color?: string }
const props = defineProps<{
  open: boolean;
  title: string;
  rows: DetailRow[];
  extra?: string;
  extraTitle?: string;
}>();
const emit = defineEmits<{ close: [] }>();
function close() { emit("close"); }
</script>

<style scoped>
.dm-mask {
  position: fixed; inset: 0; z-index: 1000;
  background: rgba(4, 8, 20, 0.66);
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(3px);
}
.dm-modal {
  width: 460px; max-width: 92vw; max-height: 86vh; overflow: auto;
  background: var(--panel, #131a30);
  border: 1px solid var(--line, rgba(255,255,255,.1));
  border-radius: 12px; box-shadow: 0 20px 60px rgba(0,0,0,.5);
}
.dm-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px; border-bottom: 1px solid var(--line, rgba(255,255,255,.1));
}
.dm-head h3 { margin: 0; font-size: 14.5px; color: var(--cyan, #22e3ff); }
.dm-x { background: none; border: none; color: var(--txt2, #8892b0); font-size: 15px; cursor: pointer; }
.dm-body { padding: 14px 18px; }
.dm-row { display: flex; gap: 10px; font-size: 12.5px; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,.04); }
.dm-k { color: var(--txt3, #5a6380); width: 92px; flex-shrink: 0; }
.dm-v { color: var(--txt, #e6f1ff); word-break: break-all; }
.dm-extra { margin-top: 12px; font-size: 12.5px; color: var(--txt2, #8892b0); }
.dm-extra p { margin: 4px 0 0; white-space: pre-wrap; line-height: 1.5; color: var(--txt, #e6f1ff); }
.dm-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 12px 18px; border-top: 1px solid var(--line, rgba(255,255,255,.1)); }
.dm-btn { padding: 7px 16px; border-radius: 7px; font-size: 13px; cursor: pointer; background: transparent; border: 1px solid var(--line, rgba(255,255,255,.15)); color: var(--txt2, #8892b0); }
</style>
