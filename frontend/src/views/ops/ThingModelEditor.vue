<template>
  <div class="tm-editor">
    <!-- 顶部 -->
    <div class="view-head">
      <h1>{{ tl('thingModel.title') }}</h1>
      <span class="sub">{{ tl('thingModel.sub') }}</span>
      <div class="head-actions">
        <input v-model.trim="kw" class="ipt" :placeholder="tl('thingModel.search')" style="width: 220px" @keyup.enter="loadList" />
        <button class="btn-sm" @click="loadList">{{ tl('common.detail') }}</button>
        <button class="btn-sm primary" @click="openCreate" :disabled="!canAdmin">{{ tl('thingModel.newModel') }}</button>
      </div>
    </div>

    <div class="tm-grid">
      <!-- 左: 模型列表 -->
      <Panel class="tm-list">
        <div class="list-head">{{ tl('thingModel.title') }} ({{ list.length }})</div>
        <div
          v-for="m in list"
          :key="m.id"
          class="list-item"
          :class="{ active: cur && cur.id === m.id }"
          @click="select(m)"
        >
          <div class="li-name">{{ m.name || m.modelKey }}</div>
          <div class="li-key mono">{{ m.modelKey }}</div>
          <span class="tag b">{{ m.category }}</span>
        </div>
        <div v-if="!list.length" class="empty">{{ tl('common.error') }}</div>
      </Panel>

      <!-- 中: 表单 -->
      <Panel class="tm-form">
        <template v-if="cur">
          <div class="form-head">
            <span>{{ editing ? (cur.id ? tl('thingModel.edit') : tl('thingModel.newModel')) : tl('thingModel.preview') }}</span>
            <div class="row-gap">
              <button v-if="!editing" class="btn-sm" @click="startEdit" :disabled="!canAdmin">{{ tl('common.edit') || '编辑' }}</button>
              <button v-if="editing" class="btn-sm" @click="cancelEdit">{{ tl('common.cancel') || '取消' }}</button>
              <button v-if="editing" class="btn-sm primary" @click="save" :disabled="!canAdmin || saving">{{ saving ? tl('common.loading') : tl('thingModel.save') }}</button>
              <button v-if="cur.id && canAdmin" class="btn-sm danger" @click="remove" :disabled="saving">{{ tl('thingModel.delete') }}</button>
            </div>
          </div>

          <div class="form-cols">
            <label>{{ tl('thingModel.modelKey') }}
              <input v-model.trim="form.modelKey" class="ipt" :disabled="!editing || !!cur.id" />
            </label>
            <label>{{ tl('thingModel.name') }}
              <input v-model.trim="form.name" class="ipt" :disabled="!editing" />
            </label>
            <label>{{ tl('thingModel.category') }}
              <input v-model.trim="form.category" class="ipt" :disabled="!editing" />
            </label>
            <label>{{ tl('thingModel.domain') }}
              <input v-model.trim="form.domain" class="ipt" :disabled="!editing" />
            </label>
            <label>{{ tl('thingModel.protocol') }}
              <input v-model.trim="form.protocol" class="ipt" :disabled="!editing" />
            </label>
            <label>{{ tl('thingModel.vendor') }}
              <input v-model.trim="form.vendor" class="ipt" :disabled="!editing" />
            </label>
          </div>
          <label class="block">{{ tl('thingModel.description') }}
            <textarea v-model.trim="form.description" class="ipt" rows="2" :disabled="!editing"></textarea>
          </label>

          <!-- items tab -->
          <div class="tabs">
            <button
              v-for="t in itemTypes"
              :key="t"
              class="tab"
              :class="{ on: activeTab === t }"
              @click="activeTab = t"
            >{{ tl('thingModel.' + t) }} ({{ itemsOf(t).length }})</button>
          </div>

          <div class="items-table">
            <div class="ith">
              <span>{{ tl('thingModel.identifier') }}</span>
              <span>{{ tl('thingModel.name') }}</span>
              <span>{{ tl('thingModel.dataType') }}</span>
              <span>{{ tl('thingModel.unit') }}</span>
              <span v-if="editing"></span>
            </div>
            <div v-for="(it, i) in itemsOf(activeTab)" :key="i" class="itr">
              <input v-model.trim="it.identifier" class="ipt sm" :disabled="!editing" />
              <input v-model.trim="it.name" class="ipt sm" :disabled="!editing" />
              <select v-model="it.dataType" class="ipt sm" :disabled="!editing">
                <option v-for="d in dataTypes" :key="d" :value="d">{{ d }}</option>
              </select>
              <input v-model.trim="it.unit" class="ipt sm" :disabled="!editing" />
              <button v-if="editing" class="x" @click="removeItem(activeTab, i)">✕</button>
            </div>
            <button v-if="editing" class="btn-sm add" @click="addItem(activeTab)">+ {{ tl('thingModel.addItem') }}</button>
          </div>
        </template>
        <div v-else class="empty">{{ tl('thingModel.empty') }}</div>
      </Panel>

      <!-- 右: 实时预览 + 校验 -->
      <Panel class="tm-preview">
        <div class="list-head">{{ tl('thingModel.preview') }}</div>
        <div v-if="issues.length" class="issues">
          <div v-for="(iss, i) in issues" :key="i" class="issue">⚠ {{ iss }}</div>
        </div>
        <pre class="json">{{ previewJson }}</pre>
      </Panel>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Panel from '@/components/common/Panel.vue'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { usePermission } from '@/hooks/usePermission'
import {
  listThingModels,
  getThingModel,
  createThingModel,
  updateThingModel,
  deleteThingModel,
  type ThingModel,
  type ThingModelItem,
  type ItemType,
  type DataType,
} from '@/api/thingModel'

const { t: tl } = useI18n()
const toast = useToast()
const { can } = usePermission()
const canAdmin = computed(() => can('admin'))

const itemTypes: ItemType[] = ['property', 'service', 'event']
const dataTypes: DataType[] = ['float', 'int', 'bool', 'string', 'enum', 'command']
const KW_RE = /^[a-zA-Z][a-zA-Z0-9_]*$/

const list = ref<ThingModel[]>([])
const cur = ref<ThingModel | null>(null)
const editing = ref(false)
const saving = ref(false)
const kw = ref('')
const activeTab = ref<ItemType>('property')

const form = reactive({
  modelKey: '',
  name: '',
  category: '',
  domain: '',
  protocol: '',
  vendor: '',
  description: '',
  items: [] as ThingModelItem[],
})

function itemsOf(t: ItemType): ThingModelItem[] {
  return form.items.filter((i) => i.itemType === t)
}

function blankItem(t: ItemType): ThingModelItem {
  return { itemType: t, identifier: '', name: '', dataType: 'float', unit: '', desc: '', extra: {} }
}

function addItem(t: ItemType) {
  form.items.push(blankItem(t))
}
function removeItem(t: ItemType, idx: number) {
  const arr = form.items
  let seen = -1
  for (let i = 0; i < arr.length; i++) {
    if (arr[i].itemType !== t) continue
    seen++
    if (seen === idx) {
      arr.splice(i, 1)
      return
    }
  }
}

function loadList() {
  listThingModels({ kw: kw.value }).then((r) => {
    list.value = r || []
    if (!cur.value && list.value.length) select(list.value[0])
  }).catch(() => toast.error('加载物模型失败'))
}

function select(m: ThingModel) {
  getThingModel(m.id)
    .then((full) => {
      cur.value = full
      syncForm(full)
      editing.value = false
    })
    .catch(() => toast.error('加载详情失败'))
}

function syncForm(m: ThingModel) {
  form.modelKey = m.modelKey
  form.name = m.name
  form.category = m.category
  form.domain = m.domain
  form.protocol = m.protocol
  form.vendor = m.vendor
  form.description = m.description
  form.items = (m.items || []).map((i) => ({ ...i, extra: i.extra || {} }))
  activeTab.value = 'property'
}

function openCreate() {
  const blank: ThingModel = {
    id: 0,
    modelKey: '',
    name: '',
    category: '',
    domain: '',
    protocol: '',
    vendor: '',
    description: '',
    items: [],
  }
  cur.value = blank
  syncForm(blank)
  editing.value = true
}

function startEdit() {
  if (cur.value && cur.value.id) editing.value = true
}
function cancelEdit() {
  if (cur.value && cur.value.id) {
    syncForm(cur.value)
    editing.value = false
  } else {
    cur.value = null
  }
}

const issues = computed<string[]>(() => {
  const out: string[] = []
  if (!form.modelKey) out.push(tl('thingModel.issueKey') || '模型 key 必填')
  else if (!KW_RE.test(form.modelKey)) out.push(tl('thingModel.issueKeyFmt') || 'key 须字母开头, 仅含字母数字下划线')
  if (!form.name) out.push(tl('thingModel.issueName') || '名称必填')
  const seen = new Map<string, number>()
  for (const it of form.items) {
    if (!it.identifier) {
      out.push(tl('thingModel.issueItemId') || '存在未填写标识符的成员')
      break
    }
    if (!KW_RE.test(it.identifier)) {
      out.push(`${it.identifier}: ${tl('thingModel.issueKeyFmt')}`)
    }
    seen.set(it.identifier, (seen.get(it.identifier) || 0) + 1)
  }
  for (const [k, v] of seen) if (v > 1) out.push(`${k}: ${tl('thingModel.issueDup') || '标识符重复'}`)
  return out
})

const previewJson = computed(() => {
  const payload = {
    modelKey: form.modelKey,
    name: form.name,
    category: form.category,
    domain: form.domain,
    protocol: form.protocol,
    vendor: form.vendor,
    description: form.description,
    items: form.items
      .filter((i) => i.identifier || i.name)
      .map((i) => ({
        itemType: i.itemType,
        identifier: i.identifier,
        name: i.name,
        dataType: i.dataType,
        unit: i.unit,
        desc: i.desc,
        extra: i.extra,
      })),
  }
  return JSON.stringify(payload, null, 2)
})

function save() {
  if (issues.value.length) {
    toast.warning(issues.value[0])
    return
  }
  saving.value = true
  const payload = {
    modelKey: form.modelKey,
    name: form.name,
    category: form.category,
    domain: form.domain,
    protocol: form.protocol,
    vendor: form.vendor,
    description: form.description,
    items: form.items
      .filter((i) => i.identifier)
      .map((i) => ({
        itemType: i.itemType,
        identifier: i.identifier,
        name: i.name,
        dataType: i.dataType,
        unit: i.unit,
        desc: i.desc,
        extra: i.extra,
      })),
  }
  const op = cur.value && cur.value.id
    ? updateThingModel(cur.value.id, payload)
    : createThingModel(payload as any)
  op.then((saved) => {
    toast.success(tl('thingModel.saved'))
    editing.value = false
    loadList()
    getThingModel(saved.id).then(syncForm)
    cur.value = saved
  })
    .catch((e: any) => toast.error(e?.detail || '保存失败'))
    .finally(() => (saving.value = false))
}

async function remove() {
  if (!cur.value?.id) return
  if (!(await useConfirm({ message: tl('thingModel.confirmDelete'), danger: true }))) return
  deleteThingModel(cur.value.id)
    .then(() => {
      toast.success(tl('thingModel.deleted'))
      cur.value = null
      loadList()
    })
    .catch((e: any) => toast.error(e?.detail || '删除失败'))
}

loadList()
</script>

<style scoped>
.tm-editor { height: 100%; display: flex; flex-direction: column; gap: 12px; }
.head-actions { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.tm-grid {
  flex: 1;
  display: grid;
  grid-template-columns: 240px 1fr 320px;
  gap: 12px;
  min-height: 0;
}
.tm-list, .tm-form, .tm-preview { overflow: auto; }
.list-head { font-size: 13px; font-weight: 700; color: var(--txt-strong); margin-bottom: 10px; }
.list-item {
  padding: 10px; border: 1px solid var(--line); border-radius: 10px;
  margin-bottom: 8px; cursor: pointer; background: var(--panel);
  transition: border-color .15s, transform .1s;
}
.list-item:hover { border-color: var(--cyan); }
.list-item.active { border-color: var(--cyan); box-shadow: 0 0 0 1px var(--cyan) inset; }
.li-name { font-weight: 600; color: var(--txt-strong); font-size: 13px; }
.li-key { font-size: 11px; color: var(--muted); margin: 2px 0 6px; }
.form-head { display: flex; justify-content: space-between; align-items: center; font-weight: 700; color: var(--txt-strong); margin-bottom: 12px; }
.row-gap { display: flex; gap: 8px; }
.form-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px; }
.block { display: block; margin-bottom: 10px; }
label { font-size: 12px; color: var(--txt2); display: flex; flex-direction: column; gap: 4px; }
.ipt { width: 100%; }
.btn-sm.danger { color: var(--red); border-color: rgba(255,77,94,.35); }
.btn-sm.primary { color: #04121a; background: var(--cyan); border-color: var(--cyan); font-weight: 600; }
.btn-sm.add { margin-top: 8px; color: var(--cyan); border-color: rgba(34,211,238,.35); }
.tabs { display: flex; gap: 6px; margin: 12px 0 8px; }
.tab { font-size: 12px; padding: 6px 12px; border-radius: 8px; border: 1px solid var(--line); background: var(--panel); color: var(--txt2); cursor: pointer; }
.tab.on { color: var(--cyan); border-color: var(--cyan); }
.items-table { display: flex; flex-direction: column; gap: 6px; }
.ith, .itr { display: grid; grid-template-columns: 1.4fr 1.4fr 1fr 0.8fr 28px; gap: 6px; align-items: center; }
.ith { font-size: 11px; color: var(--muted); }
.itr .ipt.sm { font-size: 12px; padding: 5px 8px; }
.x { background: none; border: none; color: var(--red); cursor: pointer; font-size: 14px; }
.issues { margin-bottom: 10px; }
.issue { font-size: 12px; color: var(--amber); background: rgba(255,176,32,.08); border: 1px solid rgba(255,176,32,.3); padding: 6px 10px; border-radius: 8px; margin-bottom: 6px; }
.json { font-size: 11px; line-height: 1.5; color: var(--txt2); white-space: pre-wrap; word-break: break-all; background: var(--track); padding: 12px; border-radius: 10px; }
.empty { text-align: center; color: var(--muted); padding: 30px; font-size: 13px; }
</style>
