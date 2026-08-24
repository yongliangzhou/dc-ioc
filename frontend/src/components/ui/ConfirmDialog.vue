<template>
  <teleport to="body">
    <div class="cf-mask" v-if="visible">
      <div class="cf-modal" :class="{ danger }">
        <div class="cf-head">
          <span class="cf-title">{{ title }}</span>
        </div>
        <div class="cf-body">
          <p class="cf-msg">{{ message }}</p>
          <p v-if="detail" class="cf-detail">{{ detail }}</p>
          <div v-if="err" class="cf-err">{{ err }}</div>
        </div>
        <div class="cf-foot">
          <button class="btn-sm" :disabled="loading" @click="onCancel">{{ cancelText }}</button>
          <button
            class="btn-sm"
            :class="danger ? 'danger' : 'primary'"
            :disabled="loading"
            @click="onOk"
          >
            {{ loading ? loadingText : confirmText }}
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const visible = ref(false)
const title = ref('')
const message = ref('')
const detail = ref('')
const confirmText = ref('确定')
const cancelText = ref('取消')
const loadingText = ref('处理中…')
const danger = ref(false)
const loading = ref(false)
const err = ref('')

let resolver: ((v: boolean) => void) | null = null

function open(opts: {
  title?: string
  message: string
  detail?: string
  confirmText?: string
  cancelText?: string
  loadingText?: string
  danger?: boolean
}): Promise<boolean> {
  title.value = opts.title ?? '确认操作'
  message.value = opts.message
  detail.value = opts.detail ?? ''
  confirmText.value = opts.confirmText ?? '确定'
  cancelText.value = opts.cancelText ?? '取消'
  loadingText.value = opts.loadingText ?? '处理中…'
  danger.value = opts.danger ?? false
  loading.value = false
  err.value = ''
  visible.value = true
  return new Promise((resolve) => {
    resolver = resolve
  })
}

function onCancel() {
  visible.value = false
  resolver?.(false)
  resolver = null
}

function onOk() {
  resolver?.(true)
  resolver = null
  // 若外部 await 期间不关闭，由 setLoading 控制
}

// 暴露给 useConfirm 控制 loading / 关闭
function setLoading(v: boolean) {
  loading.value = v
}
function close() {
  visible.value = false
}
function setError(e: string) {
  err.value = e
}

defineExpose({ open, close, setLoading, setError })
</script>

<style scoped>
.cf-mask {
  position: fixed;
  inset: 0;
  background: rgba(6, 11, 20, 0.6);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6vh 16px;
  z-index: 1500;
}
.cf-modal {
  width: min(420px, 94vw);
  background: linear-gradient(180deg, var(--panel), var(--bg2));
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}
.cf-modal.danger {
  border-color: rgba(242, 63, 63, 0.5);
}
.cf-head {
  padding: 14px 16px;
  border-bottom: 1px solid var(--line);
}
.cf-title {
  font-size: 15px;
  font-weight: 700;
}
.cf-body {
  padding: 14px 16px;
  font-size: 13px;
  line-height: 1.6;
}
.cf-msg {
  color: var(--txt);
}
.cf-detail {
  color: var(--txt3);
  font-size: 11px;
  margin-top: 6px;
}
.cf-err {
  color: var(--red);
  font-size: 12px;
  margin-top: 10px;
}
.cf-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  padding: 10px 16px;
  border-top: 1px solid var(--line);
}
.btn-sm {
  padding: 6px 14px;
  border-radius: 7px;
  border: 1px solid var(--line);
  background: var(--bg2);
  color: var(--txt2);
  cursor: pointer;
  font-size: 12px;
}
.btn-sm.primary {
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  color: #04121f;
  border-color: transparent;
  font-weight: 700;
}
.btn-sm.danger {
  background: rgba(242, 63, 63, 0.15);
  color: var(--red);
  border-color: rgba(242, 63, 63, 0.4);
}
.btn-sm.danger:hover:not(:disabled) {
  background: rgba(242, 63, 63, 0.3);
}
.btn-sm:disabled {
  opacity: 0.6;
  cursor: default;
}
</style>
