<template>
  <teleport to="body">
    <div v-if="modelValue" class="ge-mask" @click.self="close">
      <aside class="ge-panel" role="dialog" aria-modal="true">
        <header class="ge-head">
          <div>
            <h3>{{ title }}</h3>
            <div class="ge-sub">{{ t('graphicEditor.subtitle') }} · {{ editor.kind }}</div>
          </div>
          <button class="ge-x" :aria-label="t('graphicEditor.close')" @click="close">✕</button>
        </header>

        <!-- 后端不可达: 明确告知"仅本地生效", 不假装已保存 -->
        <div v-if="editor.usingFallback.value" class="ge-banner warn">
          {{ t('graphicEditor.fallback') }}
        </div>
        <div v-if="editor.error.value" class="ge-banner err">{{ editor.error.value }}</div>

        <!-- ===== 节点 ===== -->
        <section class="ge-sec">
          <div class="ge-sec-h">
            <b>{{ t('graphicEditor.nodes') }} ({{ rows.length }})</b>
            <button class="ge-btn" @click="startAdd">+ {{ t('graphicEditor.addNode') }}</button>
          </div>
          <div class="ge-list">
            <div v-for="r in rows" :key="r.id" class="ge-row">
              <div class="ge-row-main">
                <span class="ge-name">{{ r.label || r.id }}</span>
                <span class="ge-tag">{{ r.type || '-' }}</span>
                <span v-if="r.status" class="ge-tag st">{{ r.status }}</span>
                <span class="ge-id mono">#{{ r.id }}</span>
              </div>
              <div class="ge-row-act">
                <button class="ge-link" @click="startEdit(r)">{{ t('graphicEditor.edit') }}</button>
                <button class="ge-link danger" @click="onRemove(r)">
                  {{ t('graphicEditor.remove') }}
                </button>
              </div>
            </div>
            <div v-if="!rows.length" class="ge-empty">{{ t('graphicEditor.empty') }}</div>
          </div>
          <div v-if="removedIds.length" class="ge-removed">
            {{ t('graphicEditor.removed') }}
            <span v-for="id in removedIds" :key="id" class="ge-chip">
              {{ id }}
              <button @click="editor.restoreNode(id)">{{ t('graphicEditor.restore') }}</button>
            </span>
          </div>
        </section>

        <!-- ===== 节点编辑表单 ===== -->
        <section v-if="form" class="ge-sec form">
          <div class="ge-sec-h">
            <b>{{ formIsNew ? t('graphicEditor.newNode') : t('graphicEditor.editNode') }}</b>
          </div>
          <label class="ge-fld"
            >{{ t('graphicEditor.id')
            }}<input v-model="form!.id" :disabled="!formIsNew" class="ge-ipt"
          /></label>
          <label class="ge-fld"
            >{{ t('graphicEditor.name') }}<input v-model="form!.label" class="ge-ipt"
          /></label>
          <div class="ge-2">
            <label class="ge-fld"
              >{{ t('graphicEditor.type') }}<input v-model="form!.type" class="ge-ipt"
            /></label>
            <label class="ge-fld"
              >{{ t('graphicEditor.status') }}<input v-model="form!.status" class="ge-ipt"
            /></label>
          </div>
          <div class="ge-2">
            <label class="ge-fld"
              >{{ t('graphicEditor.posX')
              }}<input v-model.number="form!.x" type="number" class="ge-ipt"
            /></label>
            <label class="ge-fld"
              >{{ t('graphicEditor.posY')
              }}<input v-model.number="form!.y" type="number" class="ge-ipt"
            /></label>
          </div>
          <div class="ge-sec-h sub">
            <b>{{ t('graphicEditor.params') }}</b>
            <button class="ge-btn sm" @click="addParamRow">
              + {{ t('graphicEditor.addParam') }}
            </button>
          </div>
          <div v-for="(p, i) in paramRows" :key="'p' + i" class="ge-kv">
            <input v-model="p.k" class="ge-ipt" :placeholder="t('graphicEditor.name')" />
            <input v-model="p.v" class="ge-ipt" :placeholder="t('graphicEditor.value')" />
            <button class="ge-link danger" @click="paramRows.splice(i, 1)">
              {{ t('graphicEditor.remove') }}
            </button>
          </div>
          <div class="ge-form-act">
            <button class="ge-btn primary" @click="submitForm">{{ t('graphicEditor.ok') }}</button>
            <button class="ge-btn" @click="form = null">{{ t('graphicEditor.cancel') }}</button>
          </div>
        </section>

        <!-- ===== 连线 (页面提供 edgeDefaults 时可用) ===== -->
        <section v-if="allowEdges" class="ge-sec">
          <div class="ge-sec-h">
            <b>{{ t('graphicEditor.edges') }} ({{ edgeRows.length }})</b>
            <button class="ge-btn" @click="startAddEdge">+ {{ t('graphicEditor.addEdge') }}</button>
          </div>
          <div v-for="e in edgeRows" :key="e.id" class="ge-kv">
            <span class="ge-name">{{ e.source }} → {{ e.target }}</span>
            <span class="ge-tag">{{ e.label || '-' }}</span>
            <button class="ge-link" @click="startEditEdge(e)">{{ t('graphicEditor.edit') }}</button>
            <button class="ge-link danger" @click="editor.removeEdge(e.id)">
              {{ t('graphicEditor.remove') }}
            </button>
          </div>
          <div v-if="edgeForm" class="ge-kv">
            <input
              v-model="edgeForm.source"
              class="ge-ipt"
              :placeholder="t('graphicEditor.source')"
            />
            <input
              v-model="edgeForm.target"
              class="ge-ipt"
              :placeholder="t('graphicEditor.target')"
            />
            <input v-model="edgeForm.label" class="ge-ipt" :placeholder="t('graphicEditor.name')" />
            <button class="ge-btn primary sm" @click="submitEdge">
              {{ t('graphicEditor.ok') }}
            </button>
          </div>
        </section>

        <!-- ===== 页面参数配置 ===== -->
        <section v-if="allowParams" class="ge-sec">
          <div class="ge-sec-h">
            <b>{{ t('graphicEditor.pageParams') }}</b>
            <button class="ge-btn sm" @click="addGlobalParam">
              + {{ t('graphicEditor.addParam') }}
            </button>
          </div>
          <div v-for="(p, i) in globalParamRows" :key="'g' + i" class="ge-kv">
            <input v-model="p.k" class="ge-ipt" :placeholder="t('graphicEditor.name')" />
            <input v-model="p.v" class="ge-ipt" :placeholder="t('graphicEditor.value')" />
            <button class="ge-link danger" @click="removeGlobalParam(i)">
              {{ t('graphicEditor.remove') }}
            </button>
          </div>
          <div v-if="!globalParamRows.length" class="ge-empty">{{ t('graphicEditor.empty') }}</div>
        </section>

        <footer class="ge-foot">
          <span v-if="editor.updatedAt.value" class="ge-meta"
            >{{ editor.updatedBy.value }} · {{ editor.updatedAt.value }}</span
          >
          <span v-else-if="editor.dirty.value" class="ge-meta warn">{{
            t('graphicEditor.dirty')
          }}</span>
          <span v-else class="ge-meta">{{ t('graphicEditor.synced') }}</span>
          <button class="ge-btn" :disabled="editor.saving.value" @click="onReset">
            {{ t('graphicEditor.reset') }}
          </button>
          <button class="ge-btn primary" :disabled="editor.saving.value" @click="onSave">
            {{ editor.saving.value ? t('graphicEditor.saving') : t('graphicEditor.save') }}
          </button>
        </footer>
      </aside>
    </div>
  </teleport>
</template>

<script setup lang="ts">
/**
 * GraphicEditDrawer — 统一图形编辑抽屉
 *
 * 与 useGraphicEditor 配套: 抽屉只负责"编辑交互", 状态与持久化由 editor 承担。
 * 页面只需提供 defaults (当前渲染出来的节点快照), 抽屉即支持:
 *   · 改名 / 改类型 / 改状态 / 改坐标 / 改参数 (写入覆盖层, 留空字段回退默认)
 *   · 删除节点 (页面自带节点记入 removed, 自建节点直接移除)
 *   · 新增节点 (覆盖层新增条目, 由页面 adapter 转成可渲染节点)
 *   · 连线与页面级参数配置 (可选)
 * 保存走 PUT /api/ops/graphic-config/{kind}; 后端不可达时落 localStorage 并显式提示。
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useToast } from '@/hooks/useToast'
import type { GraphicEdge, GraphicNode } from '@/types/graphic'
import { mergeNode, type GraphicEditorApi } from '@/composables/useGraphicEditor'

const { t } = useI18n()
const toast = useToast()

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    editor: GraphicEditorApi
    title: string
    /** 页面当前渲染出的节点快照 (用于列出可编辑项与生成 diff) */
    defaults: () => GraphicNode[]
    /** 页面当前连线快照 (不传则不显示连线编辑) */
    edgeDefaults?: () => GraphicEdge[]
    /** 页面级参数默认值 (不传则不显示参数配置) */
    paramDefaults?: () => Record<string, string>
  }>(),
  { edgeDefaults: undefined, paramDefaults: undefined },
)

const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [] }>()

const allowEdges = computed(() => typeof props.edgeDefaults === 'function')
const allowParams = computed(() => typeof props.paramDefaults === 'function')

function close() {
  emit('update:modelValue', false)
}

/* ---------------- 节点 ---------------- */
const baseNodes = computed<GraphicNode[]>(() => {
  try {
    return props.defaults?.() ?? []
  } catch {
    return []
  }
})

/** 默认节点(排除已删除) + 覆盖/自建节点 → 抽屉里展示的清单 */
const rows = computed<GraphicNode[]>(() => {
  const scene = props.editor.scene.value
  const removed = new Set(scene.removed ?? [])
  const ovMap = new Map(scene.nodes.map((n) => [n.id, n]))
  const out = baseNodes.value
    .filter((d) => !removed.has(d.id))
    .map((d) => {
      const ov = ovMap.get(d.id)
      return ov ? mergeNode(d, ov) : d
    })
  const ids = new Set(baseNodes.value.map((d) => d.id))
  for (const n of scene.nodes) {
    if (!ids.has(n.id) && !removed.has(n.id)) out.push(n)
  }
  return out
})
const removedIds = computed(() => props.editor.scene.value.removed ?? [])

const form = ref<GraphicNode | null>(null)
const formIsNew = ref(false)
const paramRows = ref<{ k: string; v: string }[]>([])

function startEdit(row: GraphicNode) {
  formIsNew.value = false
  form.value = { ...row, params: { ...(row.params ?? {}) } }
  paramRows.value = Object.entries(row.params ?? {}).map(([k, v]) => ({ k, v }))
}
function startAdd() {
  formIsNew.value = true
  form.value = {
    id: 'node-' + Date.now().toString(36),
    label: '',
    type: '',
    x: null,
    y: null,
    status: '',
    params: {},
  }
  paramRows.value = []
}
function addParamRow() {
  paramRows.value.push({ k: '', v: '' })
}
function submitForm() {
  const f = form.value
  if (!f) return
  if (!f.id.trim()) {
    toast.warning(t('graphicEditor.idRequired'))
    return
  }
  const params: Record<string, string> = {}
  for (const p of paramRows.value) {
    if (p.k.trim()) params[p.k.trim()] = p.v
  }
  const node: GraphicNode = { ...f, id: f.id.trim(), params }

  if (formIsNew.value) {
    // 自建节点: 整条存进去
    props.editor.upsertNode(node)
  } else {
    // 页面自带节点: 只存与默认不同的字段, 未改的字段继续跟随接口数据
    const base = baseNodes.value.find((d) => d.id === node.id)
    if (base) {
      const diffParams: Record<string, string> = {}
      for (const [k, v] of Object.entries(params)) {
        if ((base.params ?? {})[k] !== v) diffParams[k] = v
      }
      for (const k of Object.keys(base.params ?? {})) {
        if (!(k in params)) diffParams[k] = '' // 删除的参数用空串标记覆盖
      }
      props.editor.upsertNode({
        id: node.id,
        label: node.label !== base.label ? node.label : '',
        type: node.type !== (base.type ?? '') ? node.type : '',
        x: node.x != null && node.x !== base.x ? node.x : null,
        y: node.y != null && node.y !== base.y ? node.y : null,
        status: node.status !== (base.status ?? '') ? node.status : '',
        params: diffParams,
      })
    } else {
      props.editor.upsertNode(node)
    }
  }
  form.value = null
}
function onRemove(row: GraphicNode) {
  const isCustom = !baseNodes.value.some((d) => d.id === row.id)
  props.editor.removeNode(row.id, isCustom)
}

/* ---------------- 连线 ---------------- */
const edgeRows = computed<GraphicEdge[]>(() => {
  const scene = props.editor.scene.value
  const base = allowEdges.value ? props.edgeDefaults!() : []
  const ids = new Set(base.map((e) => e.id))
  return [...base, ...scene.edges.filter((e) => !ids.has(e.id))]
})
const edgeForm = ref<GraphicEdge | null>(null)
function startAddEdge() {
  edgeForm.value = { id: 'edge-' + Date.now().toString(36), source: '', target: '', label: '' }
}
function startEditEdge(e: GraphicEdge) {
  edgeForm.value = { ...e }
}
function submitEdge() {
  const e = edgeForm.value
  if (!e) return
  if (!e.source.trim() || !e.target.trim()) {
    toast.warning(t('graphicEditor.edgeRequired'))
    return
  }
  props.editor.setEdge({ ...e, source: e.source.trim(), target: e.target.trim() })
  edgeForm.value = null
}

/* ---------------- 页面参数 ---------------- */
const globalParamRows = computed<{ k: string; v: string }[]>(() => {
  const base = allowParams.value ? props.paramDefaults!() : {}
  const merged = { ...base, ...props.editor.scene.value.params }
  return Object.entries(merged).map(([k, v]) => ({ k, v }))
})
function addGlobalParam() {
  let i = 1
  let key = 'param' + i
  const cur = props.editor.scene.value.params ?? {}
  while (key in cur) key = 'param' + ++i
  props.editor.setParam(key, '')
}
function removeGlobalParam(i: number) {
  const row = globalParamRows.value[i]
  if (row) props.editor.removeParam(row.k)
}

/* ---------------- 保存 / 重置 ---------------- */
async function onSave() {
  // 参数编辑是行内输入: 提交前把当前值写回覆盖层
  if (allowParams.value) {
    const base = props.paramDefaults!()
    for (const p of globalParamRows.value) {
      if (!p.k.trim()) continue
      if (base[p.k] !== p.v) props.editor.setParam(p.k, p.v)
    }
  }
  const ok = await props.editor.save()
  if (ok) {
    toast.success(t('graphicEditor.saveSuccess'))
    emit('saved')
  } else {
    toast.error(props.editor.error.value || t('graphicEditor.saveFailed'))
  }
}
async function onReset() {
  const ok = await props.editor.reset()
  if (ok) toast.success(t('graphicEditor.resetDone'))
  else toast.error(props.editor.error.value || t('graphicEditor.saveFailed'))
}

// 打开抽屉时若尚未加载过, 触发一次拉取
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      form.value = null
      edgeForm.value = null
      if (!props.editor.loading.value && !props.editor.updatedAt.value) void props.editor.reload()
    }
  },
)
</script>

<style scoped>
.ge-mask {
  position: fixed;
  inset: 0;
  background: rgba(4, 10, 20, 0.55);
  z-index: 1200;
  display: flex;
  justify-content: flex-end;
}
.ge-panel {
  width: min(520px, 96vw);
  height: 100%;
  background: var(--panel);
  border-left: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 16px 18px;
}
.ge-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.ge-head h3 {
  margin: 0;
  font-size: 16px;
  color: var(--txt-strong);
}
.ge-sub {
  font-size: 11px;
  color: var(--txt3, #8595ad);
  margin-top: 3px;
}
.ge-x {
  background: transparent;
  border: none;
  color: var(--txt2);
  font-size: 18px;
  cursor: pointer;
}
.ge-banner {
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 12px;
  margin-bottom: 10px;
}
.ge-banner.warn {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.35);
  color: #fbbf24;
}
.ge-banner.err {
  background: rgba(242, 63, 63, 0.12);
  border: 1px solid rgba(242, 63, 63, 0.35);
  color: #f87171;
}
.ge-sec {
  margin-bottom: 16px;
}
.ge-sec-h {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: var(--txt2);
}
.ge-sec-h.sub {
  margin-top: 10px;
}
.ge-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 240px;
  overflow-y: auto;
}
.ge-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 9px;
}
.ge-row-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}
.ge-name {
  font-size: 12px;
  color: var(--txt);
  font-weight: 600;
}
.ge-tag {
  font-size: 10px;
  color: var(--txt3, #8595ad);
  background: var(--bg);
  border: 1px solid var(--line);
  border-radius: 999px;
  padding: 1px 7px;
}
.ge-tag.st {
  color: var(--cyan);
}
.ge-id {
  font-size: 10px;
  color: var(--txt3, #8595ad);
}
.ge-row-act {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.ge-link {
  background: transparent;
  border: none;
  color: var(--cyan);
  font-size: 11px;
  cursor: pointer;
  padding: 0;
}
.ge-link.danger {
  color: #f87171;
}
.ge-btn {
  background: var(--bg2);
  border: 1px solid var(--line);
  color: var(--txt);
  border-radius: 7px;
  padding: 5px 12px;
  font-size: 11px;
  cursor: pointer;
}
.ge-btn.primary {
  background: linear-gradient(90deg, var(--cyan), var(--blue));
  color: #04121f;
  border-color: transparent;
  font-weight: 700;
}
.ge-btn.sm {
  padding: 3px 9px;
  font-size: 10px;
}
.ge-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ge-removed {
  margin-top: 8px;
  font-size: 11px;
  color: var(--txt3, #8595ad);
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.ge-chip {
  background: rgba(242, 63, 63, 0.12);
  border: 1px solid rgba(242, 63, 63, 0.3);
  color: #f87171;
  border-radius: 999px;
  padding: 1px 8px;
  display: inline-flex;
  gap: 6px;
  align-items: center;
}
.ge-chip button {
  background: transparent;
  border: none;
  color: var(--cyan);
  font-size: 10px;
  cursor: pointer;
}
.ge-fld {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11px;
  color: var(--txt2);
  margin-bottom: 8px;
  flex: 1;
}
.ge-2 {
  display: flex;
  gap: 8px;
}
.ge-ipt {
  background: var(--bg2);
  border: 1px solid var(--line);
  border-radius: 7px;
  color: var(--txt);
  padding: 6px 9px;
  font-size: 12px;
  outline: none;
  width: 100%;
}
.ge-ipt:focus {
  border-color: var(--cyan);
}
.ge-kv {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}
.ge-form-act {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.ge-empty {
  font-size: 11px;
  color: var(--txt3, #8595ad);
  padding: 8px 0;
}
.ge-foot {
  margin-top: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}
.ge-meta {
  font-size: 11px;
  color: var(--txt3, #8595ad);
  margin-right: auto;
}
.ge-meta.warn {
  color: #fbbf24;
}
</style>
