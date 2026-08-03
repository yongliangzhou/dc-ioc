<template>
  <div class="knowledge-page">
    <div class="view-head">
      <h1>{{ tl('知识库') }}</h1>
      <span class="sub">{{ tl('运维指导书') }} / {{ tl('应急预案') }} / {{ tl('故障案例') }} {{ tl('·') }} {{ tl('分类检索与全文搜索') }}</span>
      <span class="pill" v-if="total > 0">{{ total }} {{ tl('条') }}</span>
    </div>

    <!-- 搜索 + 操作 -->
    <div class="kb-toolbar">
      <div class="kb-search">
        <input v-model="searchQ" :placeholder="tl('搜索标题、内容、标签…')" @keyup.enter="doSearch" />
        <button class="kb-search-btn" @click="doSearch">{{ tl('搜索') }}</button>
      </div>
      <div class="kb-actions">
        <button class="kb-act-btn primary" v-bind="authState('write')" @click="showCreate = true">{{ tl('新建条目') }}</button>
        <button class="kb-act-btn" v-bind="authState('write')" @click="triggerImport">
          <input ref="fileInput" type="file" accept=".txt,.pdf,.docx" style="display:none" @change="handleImport" />
          {{ tl('导入指导书') }}
        </button>
      </div>
    </div>

    <!-- 分类标签 -->
    <div class="kb-cats" v-if="categories.length">
      <button :class="{ on: activeCat === '' }" @click="filterCat('')">{{ tl('全部') }}</button>
      <button v-for="c in categories" :key="c.name" :class="{ on: activeCat === c.name }" @click="filterCat(c.name)">
        {{ c.name }} ({{ c.count }})
      </button>
    </div>

    <!-- 导入状态 -->
    <div v-if="importMsg" class="kb-import-msg" :class="importErr ? 'err' : 'ok'">{{ importMsg }}</div>

    <!-- 知识卡片列表 -->
    <div class="kb-list" v-if="items.length">
      <article v-for="item in items" :key="item.id" class="kb-card" @click="openDetail(item)">
        <div class="kb-card-head">
          <span class="kb-type-tag" :class="'t-' + item.type">{{ typeLabel(item.type) }}</span>
          <span class="kb-domain">{{ item.domain }}</span>
          <span v-if="item.hot" class="kb-hot">🔥 {{ tl('热门') }}</span>
        </div>
        <h3 class="kb-card-title">{{ item.title }}</h3>
        <p class="kb-card-summary">{{ item.summary || (item.content || '').slice(0, 120) + '…' }}</p>
        <div class="kb-card-foot">
          <div class="kb-tags">
            <span v-for="t in item.tags?.slice(0, 4)" :key="t" class="kb-tag">{{ t }}</span>
          </div>
          <span class="kb-version">v{{ item.version }}</span>
        </div>
      </article>
    </div>

    <!-- 空态 -->
    <div v-if="!loading && items.length === 0" class="kb-empty">
      {{ searchQ ? tl('未找到匹配的知识条目') : tl('知识库暂无内容，请新建或导入指导书。') }}
    </div>

    <!-- 分页 -->
    <div class="kb-pager" v-if="total > pageSize">
      <button :disabled="page <= 1" @click="page--; load()">{{ tl('上一页') }}</button>
      <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
      <button :disabled="page * pageSize >= total" @click="page++; load()">{{ tl('下一页') }}</button>
    </div>

    <!-- ===== 详情弹窗 ===== -->
    <transition name="fade">
      <div v-if="detailItem" class="kb-modal-mask" @click.self="detailItem = null">
        <div class="kb-modal">
          <div class="kb-modal-head">
            <h2>{{ detailItem.title }}</h2>
            <button class="kb-modal-close" @click="detailItem = null">✕</button>
          </div>
          <div class="kb-modal-meta">
            <span class="kb-type-tag" :class="'t-' + detailItem.type">{{ typeLabel(detailItem.type) }}</span>
            <span>{{ detailItem.domain }}</span>
            <span>{{ detailItem.category }}</span>
            <span>v{{ detailItem.version }}</span>
          </div>
          <div class="kb-modal-body">
            <div class="kb-section" v-if="detailItem.summary">
              <h4>{{ tl('摘要') }}</h4>
              <p>{{ detailItem.summary }}</p>
            </div>
            <div class="kb-section" v-if="detailItem.content">
              <h4>{{ tl('详细内容') }}</h4>
              <pre class="kb-content">{{ detailItem.content }}</pre>
            </div>
            <div class="kb-section" v-if="detailItem.steps?.length">
              <h4>{{ tl('处置步骤') }}</h4>
              <ol class="kb-steps">
                <li v-for="(s, i) in detailItem.steps" :key="i">{{ s }}</li>
              </ol>
            </div>
            <div class="kb-section" v-if="detailItem.tags?.length">
              <h4>{{ tl('标签') }}</h4>
              <div class="kb-tags">
                <span v-for="t in detailItem.tags" :key="t" class="kb-tag">{{ t }}</span>
              </div>
            </div>
          </div>
          <div class="kb-modal-foot">
            <button class="kb-act-btn" v-bind="authState('write')" @click="openEdit(detailItem!)">{{ tl('编辑') }}</button>
            <button class="kb-act-btn danger" v-bind="authState('write')" @click="handleDelete(detailItem!)">{{ tl('删除') }}</button>
          </div>
        </div>
      </div>
    </transition>

    <!-- ===== 新建/编辑弹窗 ===== -->
    <transition name="fade">
      <div v-if="showCreate" class="kb-modal-mask" @click.self="closeCreate">
        <div class="kb-modal">
          <div class="kb-modal-head">
            <h2>{{ editItem ? tl('编辑知识条目') : tl('新建知识条目') }}</h2>
            <button class="kb-modal-close" @click="closeCreate">✕</button>
          </div>
          <div class="kb-form">
            <label>{{ tl('标题') }}</label>
            <input v-model="form.title" class="kb-input" />
            <label>{{ tl('分类') }}</label>
            <input v-model="form.category" class="kb-input" placeholder="HVAC / Power / Security …" />
            <label>{{ tl('业务域') }}</label>
            <input v-model="form.domain" class="kb-input" placeholder="hvac / power / network …" />
            <label>{{ tl('类型') }}</label>
            <select v-model="form.type" class="kb-input">
              <option value="sop">SOP 标准操作</option>
              <option value="drawing">图纸</option>
              <option value="manual">指导书</option>
              <option value="emergency">应急</option>
              <option value="case">案例</option>
              <option value="training">培训</option>
            </select>
            <label>{{ tl('摘要') }}</label>
            <textarea v-model="form.summary" class="kb-input" rows="2" />
            <label>{{ tl('详细内容') }}</label>
            <textarea v-model="form.content" class="kb-input" rows="6" />
            <label>{{ tl('标签') }} ({{ tl('逗号分隔') }})</label>
            <input v-model="form.tagsStr" class="kb-input" />
          </div>
          <div class="kb-modal-foot">
            <button class="kb-act-btn primary" @click="saveItem" :disabled="saving">{{ saving ? tl('保存中…') : tl('保存') }}</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { KnowledgeItem } from '@/types'
import {
  getKnowledgeItems, getKnowledgeCategories,
  createKnowledgeItem, updateKnowledgeItem, deleteKnowledgeItem,
  importKnowledge,
} from '@/api/knowledge'
import { useToast } from '@/hooks/useToast'
import { useConfirm } from '@/hooks/useConfirm'
import { usePermission, type PermAction } from '@/hooks/usePermission'

const { t } = useI18n()
const tl = (key: string) => t(key) || key
const toast = useToast()
const { can, denyTip } = usePermission()

/** 权限按钮：禁用态 + 提示 */
function authState(action: PermAction) {
  const ok = can(action)
  return { disabled: !ok, title: ok ? '' : denyTip(action) }
}

// ---- list state ----
const items = ref<KnowledgeItem[]>([])
const categories = ref<{ name: string; count: number }[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)
const searchQ = ref('')
const activeCat = ref('')

// ---- detail ----
const detailItem = ref<KnowledgeItem | null>(null)

// ---- create/edit ----
const showCreate = ref(false)
const editItem = ref<KnowledgeItem | null>(null)
const saving = ref(false)
const form = reactive({
  title: '', category: '', domain: '', type: 'sop', summary: '', content: '', tagsStr: '',
})

// ---- import ----
const fileInput = ref<HTMLInputElement | null>(null)
const importMsg = ref('')
const importErr = ref(false)

const typeLabel = (t: string) =>
  ({ sop: 'SOP', drawing: tl('图纸'), manual: tl('指导书'), emergency: tl('应急'), case: tl('案例'), training: tl('培训') } as any)[t] || t

// ---- load ----
async function load() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (activeCat.value) params.category = activeCat.value
    if (searchQ.value) params.q = searchQ.value
    const r = await getKnowledgeItems(params)
    items.value = r.items || []
    total.value = r.total || 0
  } catch {
    items.value = []
  } finally { loading.value = false }
}

async function loadCats() {
  try {
    const r = await getKnowledgeCategories()
    categories.value = r.categories || []
  } catch { /* noop */ }
}

function doSearch() { page.value = 1; load() }
function filterCat(cat: string) { activeCat.value = cat; page.value = 1; load() }

// ---- detail ----
function openDetail(item: KnowledgeItem) { detailItem.value = item }

// ---- create/edit ----
function openEdit(item: KnowledgeItem) {
  // 注意顺序：先取 item，再关闭详情，再填充表单，避免 detailItem 先置空
  editItem.value = item
  detailItem.value = null
  showCreate.value = true
  form.title = item.title || ''
  form.category = item.category || ''
  form.domain = item.domain || ''
  form.type = item.type || 'sop'
  form.summary = item.summary || ''
  form.content = item.content || ''
  form.tagsStr = (item.tags || []).join(', ')
}

function closeCreate() {
  showCreate.value = false
  editItem.value = null
  form.title = form.category = form.domain = form.summary = form.content = form.tagsStr = ''
  form.type = 'sop'
}

async function saveItem() {
  if (!form.title.trim()) {
    toast.warning(tl('标题不能为空'))
    return
  }
  saving.value = true
  try {
    const tags = form.tagsStr.split(',').map(s => s.trim()).filter(Boolean)
    const data: Partial<KnowledgeItem> = {
      title: form.title, category: form.category, domain: form.domain,
      type: form.type, summary: form.summary, content: form.content, tags,
    }
    if (editItem.value) {
      await updateKnowledgeItem(editItem.value.id, data)
      toast.success(tl('已更新知识条目'))
    } else {
      await createKnowledgeItem(data)
      toast.success(tl('已新建知识条目'))
    }
    closeCreate()
    load()
  } catch (e: any) {
    toast.error(e?.detail || e?.response?.data?.detail || e?.message || tl('保存失败'))
  } finally { saving.value = false }
}

async function handleDelete(item: KnowledgeItem) {
  const ok = await useConfirm({
    title: tl('删除知识条目'),
    message: tl('确定要删除该知识条目') + '「' + item.title + '」？',
    detail: tl('此操作不可恢复。'),
    danger: true,
    confirmText: tl('删除'),
    onConfirm: async () => { await deleteKnowledgeItem(item.id) },
  })
  if (ok) {
    detailItem.value = null
    toast.success(tl('已删除'))
    load()
  }
}

function triggerImport() { fileInput.value?.click() }
async function handleImport(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file) return
  importMsg.value = tl('正在解析并入库') + '…'
  importErr.value = false
  try {
    const r = await importKnowledge(file)
    importMsg.value = tl('导入完成') + '：' + r.imported + ' ' + tl('条')
    load(); loadCats()
    toast.success(tl('导入完成'))
  } catch (e: any) {
    importMsg.value = tl('导入失败') + '，' + (e?.detail || e?.response?.data?.detail || e?.message || tl('请检查文件格式'))
    importErr.value = true
  }
}

onMounted(() => { load(); loadCats() })
</script>

<style scoped>
.knowledge-page { padding: 4px 0; }
.view-head { margin-bottom: 16px; }
.view-head h1 { margin: 0 0 4px; font-size: 20px; color: var(--txt); }
.sub { color: var(--muted); font-size: 13px; }
.pill { float: right; background: var(--bg2); border: 1px solid var(--line); border-radius: 999px; padding: 3px 12px; font-size: 12px; color: var(--muted); }

/* toolbar */
.kb-toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 14px; flex-wrap: wrap; }
.kb-search { display: flex; gap: 8px; flex: 1; }
.kb-search input { flex: 1; background: var(--bg); color: var(--txt); border: 1px solid var(--line); border-radius: 8px; padding: 8px 12px; font-size: 13px; font-family: inherit; }
.kb-search input:focus { outline: none; border-color: var(--cyan); }
.kb-search-btn { background: var(--cyan); color: #04181d; border: none; border-radius: 8px; padding: 8px 16px; font-weight: 600; cursor: pointer; font-size: 13px; }
.kb-actions { display: flex; gap: 8px; }
.kb-act-btn { background: var(--bg2); color: var(--txt); border: 1px solid var(--line); border-radius: 8px; padding: 8px 14px; font-size: 13px; cursor: pointer; }
.kb-act-btn:hover { border-color: var(--cyan); }
.kb-act-btn.primary { background: var(--cyan); color: #04181d; border-color: var(--cyan); font-weight: 600; }
.kb-act-btn.danger { color: #f87171; border-color: #f87171; }

/* cats */
.kb-cats { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.kb-cats button { background: var(--bg2); color: var(--muted); border: 1px solid var(--line); border-radius: 999px; padding: 5px 14px; font-size: 12px; cursor: pointer; }
.kb-cats button:hover { border-color: var(--cyan); color: var(--txt); }
.kb-cats button.on { background: var(--cyan); color: #04181d; border-color: var(--cyan); }

/* import msg */
.kb-import-msg { margin-bottom: 12px; padding: 10px 14px; border-radius: 8px; font-size: 13px; }
.kb-import-msg.ok { background: rgba(34,197,94,0.1); border: 1px solid #22c55e; color: #22c55e; }
.kb-import-msg.err { background: rgba(248,113,113,0.1); border: 1px solid #f87171; color: #f87171; }

/* card list */
.kb-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 12px; }
.kb-card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px 16px; cursor: pointer; transition: border-color 0.15s; }
.kb-card:hover { border-color: var(--cyan); }
.kb-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.kb-type-tag { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
.t-sop { background: #dcfce7; color: #166534; }
.t-drawing { background: #e0f2fe; color: #0369a1; }
.t-manual { background: #fef3c7; color: #92400e; }
.t-emergency { background: #fee2e2; color: #991b1b; }
.t-case { background: #f3e8ff; color: #6b21a8; }
.t-training { background: #e0e7ff; color: #3730a3; }
.kb-domain { font-size: 11px; color: var(--muted); }
.kb-hot { font-size: 11px; color: #f59e0b; }
.kb-card-title { margin: 0 0 6px; font-size: 15px; color: var(--txt); }
.kb-card-summary { margin: 0 0 10px; font-size: 12px; color: var(--muted); line-height: 1.6; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.kb-card-foot { display: flex; justify-content: space-between; align-items: center; }
.kb-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.kb-tag { background: var(--bg); border: 1px solid var(--line); border-radius: 999px; padding: 2px 8px; font-size: 11px; color: var(--muted); }
.kb-version { font-size: 11px; color: var(--muted); }

.kb-empty { text-align: center; padding: 48px 0; color: var(--muted); font-size: 14px; }

/* pager */
.kb-pager { display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 16px; font-size: 13px; color: var(--muted); }
.kb-pager button { background: var(--bg2); color: var(--txt); border: 1px solid var(--line); border-radius: 8px; padding: 6px 14px; cursor: pointer; }
.kb-pager button:disabled { opacity: 0.4; cursor: not-allowed; }

/* modal */
.kb-modal-mask { position: fixed; inset: 0; z-index: 100; background: rgba(0,0,0,0.55); display: flex; align-items: center; justify-content: center; }
.kb-modal { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; width: min(720px, 92vw); max-height: 86vh; overflow-y: auto; padding: 20px 24px; }
.kb-modal-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.kb-modal-head h2 { margin: 0; font-size: 17px; color: var(--txt); }
.kb-modal-close { background: none; border: none; color: var(--muted); font-size: 18px; cursor: pointer; }
.kb-modal-meta { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; font-size: 12px; color: var(--muted); }
.kb-modal-body { display: flex; flex-direction: column; gap: 16px; }
.kb-section h4 { margin: 0 0 6px; font-size: 13px; color: var(--txt); }
.kb-section p { margin: 0; font-size: 13px; color: var(--muted); line-height: 1.7; }
.kb-content { margin: 0; font-size: 12px; color: var(--txt); background: var(--bg); border: 1px solid var(--line); border-radius: 8px; padding: 12px; white-space: pre-wrap; line-height: 1.7; font-family: inherit; }
.kb-steps { margin: 0; padding-left: 20px; color: var(--muted); font-size: 13px; line-height: 1.8; }
.kb-modal-foot { display: flex; gap: 10px; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--line); }

/* form */
.kb-form { display: flex; flex-direction: column; gap: 6px; }
.kb-form label { font-size: 12px; color: var(--muted); margin-top: 4px; }
.kb-input { background: var(--bg); color: var(--txt); border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; font-size: 13px; font-family: inherit; width: 100%; box-sizing: border-box; }
.kb-input:focus { outline: none; border-color: var(--cyan); }
textarea.kb-input { resize: vertical; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
