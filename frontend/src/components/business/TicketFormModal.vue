<template>
  <teleport to="body">
    <div v-if="open" class="tf-mask" @click.self="onClose">
      <div class="tf-modal">
        <div class="tf-head">
          <h3>{{ isEdit ? '编辑工单' : title }}</h3>
          <button class="tf-x" @click="onClose">✕</button>
        </div>
        <div class="tf-body">
          <label>工单标题 <span class="req">*</span></label>
          <input v-model.trim="form.title" class="tf-input" placeholder="简述处理事项" />

          <div class="tf-row">
            <div class="tf-col">
              <label>业务系统 <span class="req">*</span></label>
              <select v-model="form.sys" class="tf-input">
                <option v-for="s in SYSTEMS" :key="s" :value="s">{{ s }}</option>
              </select>
            </div>
            <div class="tf-col">
              <label>级别 <span class="req">*</span></label>
              <select v-model="form.lv" class="tf-input">
                <option value="crit">紧急</option>
                <option value="warn">重要</option>
                <option value="info">提示</option>
              </select>
            </div>
          </div>

          <div class="tf-row">
            <div class="tf-col">
              <label>责任班组 / 人</label>
              <input v-model.trim="form.owner" class="tf-input" placeholder="如: 暖通班组" />
            </div>
            <div class="tf-col">
              <label>SLA 时限</label>
              <input v-model.trim="form.sla" class="tf-input" placeholder="如: 4h / 1h" />
            </div>
          </div>

          <label>处理说明 / 描述</label>
          <textarea
            v-model.trim="form.description"
            class="tf-input tf-area"
            rows="4"
            placeholder="详细描述问题现象、影响范围与处理要求"
          />

          <div v-if="initialSource === 'alarm'" class="tf-badge">
            <span class="tag r">来源: 告警自动转单</span>
          </div>
        </div>
        <div class="tf-foot">
          <button class="tf-btn ghost" @click="onClose">取消</button>
          <button class="tf-btn primary" :disabled="!canSubmit" @click="onSubmit">
            确认{{ isEdit ? '保存' : '创建' }}
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import type { TicketCreateRequest } from '@/types'

const props = defineProps<{
  open: boolean
  title?: string
  isEdit?: boolean
  initial?: Partial<TicketCreateRequest>
  initialSource?: 'manual' | 'alarm'
}>()
const emit = defineEmits<{ close: []; submit: [data: TicketCreateRequest] }>()

const SYSTEMS = ['暖通空调', '电力', '安防', '消防', '智能运营', '运维作业', '其他']

const form = reactive<TicketCreateRequest>({
  title: '',
  sys: '暖通空调',
  lv: 'warn',
  owner: '',
  sla: '',
  description: '',
})

// 外部 initial 变化时回填表单
watch(
  () => [props.open, props.initial],
  () => {
    if (!props.open) return
    form.title = props.initial?.title ?? ''
    form.sys = props.initial?.sys ?? '暖通空调'
    form.lv = props.initial?.lv ?? 'warn'
    form.owner = props.initial?.owner ?? ''
    form.sla = props.initial?.sla ?? ''
    form.description = props.initial?.description ?? ''
  },
  { immediate: true },
)

const canSubmit = computed(() => form.title.length > 0 && form.sys.length > 0)

function onClose() {
  emit('close')
}
function onSubmit() {
  if (!canSubmit.value) return
  emit('submit', { ...form })
}
</script>

<style scoped>
.tf-mask {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(4, 8, 20, 0.66);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(3px);
}
.tf-modal {
  width: 520px;
  max-width: 92vw;
  max-height: 88vh;
  overflow: auto;
  background: var(--panel, #131a30);
  border: 1px solid var(--line, rgba(255, 255, 255, 0.1));
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}
.tf-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 18px;
  border-bottom: 1px solid var(--line, rgba(255, 255, 255, 0.1));
}
.tf-head h3 {
  margin: 0;
  font-size: 15px;
  color: var(--cyan, #22e3ff);
}
.tf-x {
  background: none;
  border: none;
  color: var(--txt2, #8892b0);
  font-size: 15px;
  cursor: pointer;
}
.tf-body {
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tf-row {
  display: flex;
  gap: 12px;
}
.tf-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tf-body label {
  font-size: 11.5px;
  color: var(--txt2, #8892b0);
  margin-top: 6px;
}
.req {
  color: var(--red, #ff4d5e);
}
.tf-input {
  background: var(--bg2, #0e1426);
  border: 1px solid var(--line, rgba(255, 255, 255, 0.12));
  border-radius: 7px;
  color: var(--txt, #e6f1ff);
  padding: 8px 10px;
  font-size: 13px;
  outline: none;
  width: 100%;
  box-sizing: border-box;
}
.tf-input:focus {
  border-color: var(--cyan, #22e3ff);
}
.tf-area {
  resize: vertical;
  font-family: inherit;
}
.tf-badge {
  margin-top: 8px;
}
.tf-foot {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px 18px;
  border-top: 1px solid var(--line, rgba(255, 255, 255, 0.1));
}
.tf-btn {
  padding: 8px 18px;
  border-radius: 7px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid transparent;
}
.tf-btn.ghost {
  background: transparent;
  border-color: var(--line, rgba(255, 255, 255, 0.15));
  color: var(--txt2, #8892b0);
}
.tf-btn.primary {
  background: linear-gradient(135deg, #1a73e8, #22e3ff);
  color: #fff;
  font-weight: 600;
}
.tf-btn.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
