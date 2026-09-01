<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="page-title">{{ t.title }}</h1>
        <p class="page-sub">{{ t.sub }}</p>
      </div>
      <div class="page-actions">
        <input v-model="kw" class="inp" :placeholder="t.search" />
        <button
          class="btn ghost"
          :disabled="busy"
          :title="tc('tooltipRefresh')"
          :aria-label="tc('tooltipRefresh')"
          @click="page.reload"
        >
          ↻ {{ tc('refresh') }}
        </button>
      </div>
    </header>

    <!-- 概览卡片 -->
    <section class="kpi-row">
      <div class="kpi">
        <span class="kpi-v">{{ shares.length }}</span
        ><span class="kpi-l">{{ t.sharedCount }}</span>
      </div>
      <div class="kpi">
        <span class="kpi-v">{{ favs.length }}</span
        ><span class="kpi-l">{{ t.favTotal }}</span>
      </div>
      <div class="kpi">
        <span class="kpi-v">{{ cites.length }}</span
        ><span class="kpi-l">{{ t.citeTotal }}</span>
      </div>
      <div class="kpi">
        <span class="kpi-v">{{ items.length }}</span
        ><span class="kpi-l">{{ t.mine }}</span>
      </div>
    </section>

    <!-- 标签页 -->
    <nav class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </nav>

    <AsyncSection :page="page" @retry="page.reload">
      <div class="grid cards">
        <article
          v-for="it in filtered"
          :key="it.id"
          class="card"
          :class="{ shared: isShared(it.id) }"
        >
          <div class="card-top">
            <span class="badge" :class="statusCls(it.reviewStatus)">{{
              reviewLabel(it.reviewStatus)
            }}</span>
            <span v-if="isShared(it.id)" class="badge green">{{ t.shared }}</span>
            <span v-if="isFav(it.id)" class="badge amber">★ {{ t.favorite }}</span>
            <button class="x" :title="t.delete" :aria-label="t.delete" @click="remove(it)">
              ×
            </button>
          </div>
          <h3 class="card-title" @click="openDetail(it)">{{ it.title }}</h3>
          <p class="card-desc">{{ it.summary || it.content?.slice(0, 60) || '—' }}</p>
          <div class="card-meta">
            <span>{{ t.author }}：{{ it.owner || '—' }}</span>
            <span>{{ t.version }}：v{{ it.version || 1 }}</span>
          </div>
          <div class="chips">
            <span v-for="tag in it.tags || []" :key="tag" class="chip">#{{ tag }}</span>
          </div>
          <div class="card-actions">
            <button
              class="btn sm"
              :class="isFav(it.id) ? 'ghost' : 'soft'"
              @click="toggleFav(it.id)"
            >
              {{ isFav(it.id) ? '★ ' + t.unfavorite : '☆ ' + t.favorite }}
            </button>
            <button
              class="btn sm"
              :class="isShared(it.id) ? 'ghost' : 'soft'"
              @click="toggleShare(it)"
            >
              {{ isShared(it.id) ? t.cancelShare : t.publish }}
            </button>
            <button
              v-if="it.reviewStatus === 'pending'"
              class="btn sm green"
              @click="openReview(it)"
            >
              {{ t.review }}
            </button>
            <button class="btn sm" @click="openDetail(it)">{{ t.cite }} / {{ t.comment }}</button>
          </div>
          <div class="card-foot">
            <span :title="ratingTip(it.id)" :aria-label="ratingTip(it.id)"
              >⭐ {{ ratingText(it.id) }}</span
            >
            <span :title="t.commentLabel" :aria-label="t.commentLabel"
              >💬 {{ commentsOf(it.id).length }}</span
            >
            <span :title="t.citeLabel" :aria-label="t.citeLabel">🔗 {{ citeCountOf(it.id) }}</span>
          </div>
        </article>
        <div v-if="!filtered.length" class="empty">{{ t.empty }}</div>
      </div>
    </AsyncSection>

    <!-- 详情抽屉 -->
    <div v-if="detail" class="mask" @click.self="detail = null">
      <aside class="drawer">
        <header class="drawer-head">
          <h2>{{ detail.title }}</h2>
          <button
            class="x"
            :title="tc('tooltipClose')"
            :aria-label="tc('tooltipClose')"
            @click="detail = null"
          >
            ×
          </button>
        </header>
        <div class="drawer-body">
          <div class="row">
            <span>{{ t.status }}：</span
            ><b :class="statusCls(detail.reviewStatus)">{{ reviewLabel(detail.reviewStatus) }}</b>
          </div>
          <div class="row">
            <span>{{ t.author }}：</span><b>{{ detail.owner || '—' }}</b>
          </div>
          <div class="row">
            <span>{{ t.createdAt }}：</span><b>{{ fmt(detail.createdAt) }}</b>
          </div>
          <div v-if="detail.reviewer" class="row">
            <span>{{ t.reviewedBy }}：</span><b>{{ detail.reviewer }}</b>
          </div>
          <p class="content">{{ detail.content }}</p>

          <div class="block">
            <div class="block-h">{{ t.rating }}</div>
            <div class="stars">
              <button
                v-for="n in 5"
                :key="n"
                class="star"
                :class="{ on: n <= Math.round(ratingOf(detail.id)) }"
                :title="tc('rateN').replace('{n}', String(n))"
                :aria-label="tc('rateN').replace('{n}', String(n))"
                @click="rate(detail.id, n)"
              >
                ★
              </button>
              <span class="muted"
                >{{ ratingText(detail.id)
                }}<template v-if="ratingCountOf(detail.id)">
                  ·
                  {{
                    String(t.ratingCount || '{n}').replace('{n}', String(ratingCountOf(detail.id)))
                  }}</template
                ></span
              >
            </div>
          </div>

          <div class="block">
            <div class="block-h">{{ t.citeTo }}</div>
            <div class="cite-row">
              <input v-model="citeTarget" class="inp" :placeholder="t.citeTargetPlaceholder" />
              <button class="btn sm green" @click="cite(detail.id)">{{ t.cite }}</button>
            </div>
            <div v-if="citeCountOf(detail.id)" class="muted small">
              {{ t.citeCount }}：{{ citeCountOf(detail.id) }}
            </div>
          </div>

          <div class="block">
            <div class="block-h">{{ t.comments }} ({{ commentsOf(detail.id).length }})</div>
            <div v-if="commentsOf(detail.id).length" class="comment-list">
              <div v-for="(c, i) in commentsOf(detail.id)" :key="i" class="comment">
                <div class="comment-meta">
                  <b>{{ c.user }}</b
                  ><span class="muted">{{ fmt(c.at) }}</span>
                </div>
                <div class="comment-text">{{ c.text }}</div>
              </div>
            </div>
            <div v-else class="muted small">{{ t.noComment }}</div>
            <div class="cite-row">
              <input
                v-model="commentText"
                class="inp"
                :placeholder="t.commentPlaceholder"
                @keyup.enter="sendComment(detail.id)"
              />
              <button class="btn sm" @click="sendComment(detail.id)">{{ t.send }}</button>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- 评审抽屉 -->
    <div v-if="reviewing" class="mask" @click.self="reviewing = null">
      <aside class="drawer">
        <header class="drawer-head">
          <h2>{{ t.review }}：{{ reviewing.title }}</h2>
          <button
            class="x"
            :title="tc('tooltipClose')"
            :aria-label="tc('tooltipClose')"
            @click="reviewing = null"
          >
            ×
          </button>
        </header>
        <div class="drawer-body">
          <p class="content">{{ reviewing.content }}</p>
          <div class="block">
            <div class="block-h">{{ t.reviewNote }}</div>
            <textarea
              v-model="reviewNote"
              class="area"
              :placeholder="t.reviewNotePlaceholder"
            ></textarea>
          </div>
          <div class="drawer-actions">
            <button class="btn green" :disabled="reviewingLoading" @click="doReview('approved')">
              {{ t.approve }}
            </button>
            <button class="btn red" :disabled="reviewingLoading" @click="doReview('rejected')">
              {{ t.reject }}
            </button>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/modules/auth'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { useAsyncPage } from '@/composables/useAsyncPage'
import { getKnowledgeItems, reviewKnowledge, deleteKnowledgeItem } from '@/api/knowledge'
import type { KnowledgeItem } from '@/types'
import { useConfirm } from '@/hooks/useConfirm'

const { t: rawT } = useI18n()
const t = rawT('knowledgeCollab') as any
/** 通用动作文案（common 命名空间），用于图标按钮的 title / aria-label */
const tc = (k: string) => (rawT('common.' + k) as string) || ''
const auth = useAuthStore()
const me = computed(() => auth.user?.username || 'me')

const items = ref<KnowledgeItem[]>([])
const kw = ref('')
const activeTab = ref<string>('all')

// ---- localStorage 协作层 ----
const LS = {
  fav: 'kc_fav',
  share: 'kc_share',
  cite: 'kc_cite',
  rate: 'kc_rate',
  comment: 'kc_comment',
}
function read<T>(k: string, def: T): T {
  try {
    return JSON.parse(localStorage.getItem(k) || JSON.stringify(def))
  } catch {
    return def
  }
}
function write(k: string, v: any) {
  localStorage.setItem(k, JSON.stringify(v))
}

const favs = ref<number[]>(read(LS.fav, []))
const shares = ref<{ id: number; by: string; at: string }[]>(read(LS.share, []))
const cites = ref<{ id: number; target: string; at: string }[]>(read(LS.cite, []))
const rates = ref<Record<number, number[]>>(read(LS.rate, {}))
const comments = ref<Record<number, { user: string; text: string; at: string }[]>>(
  read(LS.comment, {}),
)

const detail = ref<KnowledgeItem | null>(null)
const reviewing = ref<KnowledgeItem | null>(null)
const reviewingLoading = ref(false)
const reviewNote = ref('')
const citeTarget = ref('')
const commentText = ref('')

const tabs = computed(() => [
  { key: 'all', label: t.all },
  { key: 'pending', label: t.pendingReview },
  { key: 'approved', label: t.approved },
  { key: 'rejected', label: t.rejected },
  { key: 'shared', label: t.shared },
  { key: 'fav', label: t.favorites },
  { key: 'review', label: t.reviews },
])

const filtered = computed(() => {
  let list = items.value.slice()
  const q = kw.value.trim().toLowerCase()
  if (q)
    list = list.filter((it) =>
      (it.title + ' ' + (it.tags || []).join(' ') + ' ' + (it.owner || ''))
        .toLowerCase()
        .includes(q),
    )
  switch (activeTab.value) {
    case 'pending':
      return list.filter((i) => i.reviewStatus === 'pending')
    case 'approved':
      return list.filter((i) => i.reviewStatus === 'approved')
    case 'rejected':
      return list.filter((i) => i.reviewStatus === 'rejected')
    case 'shared':
      return list.filter((i) => isShared(i.id))
    case 'fav':
      return list.filter((i) => isFav(i.id))
    case 'review':
      return list.filter((i) => i.reviewer)
  }
  return list
})

function isFav(id: number) {
  return favs.value.includes(id)
}
function isShared(id: number) {
  return shares.value.some((s) => s.id === id)
}
function citeCountOf(id: number) {
  return cites.value.filter((c) => c.id === id).length
}
function ratingOf(id: number) {
  const a = rates.value[id]
  return a && a.length ? a.reduce((s, n) => s + n, 0) / a.length : 0
}
function commentsOf(id: number) {
  return comments.value[id] || []
}
/** 评分数：无人评分时返回 0，与"有人打了 0 分"区分开 */
function ratingCountOf(id: number) {
  return (rates.value[id] || []).length
}
function ratingText(id: number) {
  return ratingCountOf(id) ? ratingOf(id).toFixed(1) : String(t.noRating || '—')
}
function ratingTip(id: number) {
  const n = ratingCountOf(id)
  if (!n) return String(t.noRating || '')
  const cnt = String(t.ratingCount || '{n}').replace('{n}', String(n))
  return `${t.ratingLabel} ${ratingOf(id).toFixed(1)} · ${cnt}`
}

function toggleFav(id: number) {
  if (isFav(id)) favs.value = favs.value.filter((x) => x !== id)
  else favs.value = [...favs.value, id]
  write(LS.fav, favs.value)
}
function toggleShare(it: KnowledgeItem) {
  if (isShared(it.id)) shares.value = shares.value.filter((s) => s.id !== it.id)
  else shares.value = [...shares.value, { id: it.id, by: me.value, at: new Date().toISOString() }]
  write(LS.share, shares.value)
}
function rate(id: number, n: number) {
  const a = rates.value[id] ? [...rates.value[id]] : []
  a.push(n)
  rates.value = { ...rates.value, [id]: a }
  write(LS.rate, rates.value)
}
function cite(id: number) {
  const target = citeTarget.value.trim()
  if (!target) return
  cites.value = [...cites.value, { id, target, at: new Date().toISOString() }]
  write(LS.cite, cites.value)
  citeTarget.value = ''
}
function sendComment(id: number) {
  const text = commentText.value.trim()
  if (!text) return
  const arr = comments.value[id] ? [...comments.value[id]] : []
  arr.push({ user: me.value, text, at: new Date().toISOString() })
  comments.value = { ...comments.value, [id]: arr }
  write(LS.comment, comments.value)
  commentText.value = ''
}
async function remove(it: KnowledgeItem) {
  if (!(await useConfirm({ message: t.confirmDelete, danger: true }))) return
  try {
    await deleteKnowledgeItem(it.id)
  } catch {
    /* 离线也允许本地移除 */
  }
  items.value = items.value.filter((x) => x.id !== it.id)
}

const page = useAsyncPage<KnowledgeItem[]>(
  async () => {
    const r = await getKnowledgeItems({ page: 1, page_size: 200 })
    items.value = r.items || []
    return items.value
  },
  { isEmpty: (d) => !d || d.length === 0 },
)
const { busy } = page

// 评审
function openReview(it: KnowledgeItem) {
  reviewing.value = it
  reviewNote.value = ''
}
async function doReview(status: 'approved' | 'rejected') {
  if (!reviewing.value) return
  reviewingLoading.value = true
  try {
    const updated = await reviewKnowledge(reviewing.value.id, status, reviewNote.value)
    const idx = items.value.findIndex((x) => x.id === updated.id)
    if (idx >= 0) items.value[idx] = updated
    reviewing.value = null
  } finally {
    reviewingLoading.value = false
  }
}

function openDetail(it: KnowledgeItem) {
  detail.value = it
}

function statusCls(s?: string) {
  return { pending: 'amber', approved: 'green', rejected: 'red' }[s || 'pending'] || 'gray'
}
function reviewLabel(s?: string) {
  return (
    ({ pending: t.pendingReview, approved: t.approved, rejected: t.rejected } as any)[
      s || 'pending'
    ] || t.pendingReview
  )
}
function fmt(d?: string) {
  return d ? new Date(d).toLocaleString() : '—'
}

onMounted(() => page.reload())
</script>

<style scoped>
.page {
  padding: 18px 22px 40px;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  margin-bottom: 16px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
}
.page-sub {
  color: var(--muted);
  font-size: 13px;
  margin-top: 4px;
}
.page-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}
.inp {
  background: var(--panel-2);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 8px;
  padding: 7px 10px;
  min-width: 220px;
}
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.kpi {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
}
.kpi-v {
  font-size: 26px;
  font-weight: 800;
  color: var(--cyan);
}
.kpi-l {
  font-size: 12px;
  color: var(--muted);
  margin-top: 4px;
}
.tabs {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.tab {
  background: var(--panel-2);
  border: 1px solid var(--line);
  color: var(--muted);
  padding: 6px 14px;
  border-radius: 999px;
  cursor: pointer;
  font-size: 13px;
}
.tab.active {
  background: var(--cyan);
  color: #04121a;
  border-color: var(--cyan);
  font-weight: 600;
}
.grid.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}
.card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.card.shared {
  border-color: var(--green);
}
.card-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}
.card-title:hover {
  color: var(--cyan);
}
.card-desc {
  font-size: 12px;
  color: var(--muted);
  line-height: 1.5;
}
.card-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--muted);
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.chip {
  font-size: 11px;
  background: var(--panel-2);
  color: var(--muted);
  border-radius: 6px;
  padding: 2px 6px;
}
.card-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 4px;
}
.card-foot {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--muted);
  border-top: 1px dashed var(--line);
  padding-top: 8px;
}
.x {
  margin-left: auto;
  background: transparent;
  border: none;
  color: var(--muted);
  font-size: 16px;
  cursor: pointer;
}
.badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
}
.badge.green {
  background: rgba(34, 197, 94, 0.16);
  color: #4ade80;
}
.badge.amber {
  background: rgba(245, 158, 11, 0.16);
  color: #fbbf24;
}
.badge.red {
  background: rgba(239, 68, 68, 0.16);
  color: #f87171;
}
.badge.gray {
  background: var(--panel-2);
  color: var(--muted);
}
.btn {
  border: 1px solid var(--line);
  background: var(--panel-2);
  color: var(--text);
  border-radius: 8px;
  padding: 7px 12px;
  cursor: pointer;
  font-size: 13px;
}
.btn.sm {
  padding: 4px 10px;
  font-size: 12px;
}
.btn.ghost {
  background: transparent;
}
.btn.soft {
  background: rgba(34, 211, 238, 0.12);
  color: var(--cyan);
  border-color: transparent;
}
.btn.green {
  background: var(--green);
  color: #04121a;
  border-color: var(--green);
  font-weight: 600;
}
.btn.red {
  background: rgba(239, 68, 68, 0.16);
  color: #f87171;
  border-color: transparent;
}
.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.empty {
  grid-column: 1/-1;
  text-align: center;
  color: var(--muted);
  padding: 40px;
}
.mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: flex-end;
  z-index: 50;
}
.drawer {
  width: 460px;
  max-width: 92vw;
  background: var(--panel);
  height: 100%;
  overflow-y: auto;
  padding: 18px 20px;
}
.drawer-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.drawer-head h2 {
  font-size: 17px;
}
.row {
  font-size: 13px;
  margin: 6px 0;
  color: var(--muted);
}
.row b {
  color: var(--text);
}
.content {
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
  white-space: pre-wrap;
  background: var(--panel-2);
  border-radius: 10px;
  padding: 12px;
  margin: 10px 0;
}
.block {
  margin-top: 14px;
  border-top: 1px solid var(--line);
  padding-top: 12px;
}
.block-h {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
}
.stars {
  display: flex;
  align-items: center;
  gap: 4px;
}
.star {
  background: none;
  border: none;
  font-size: 22px;
  color: var(--line);
  cursor: pointer;
}
.star.on {
  color: #fbbf24;
}
.cite-row {
  display: flex;
  gap: 8px;
  margin: 8px 0;
}
.area {
  width: 100%;
  min-height: 90px;
  background: var(--panel-2);
  border: 1px solid var(--line);
  color: var(--text);
  border-radius: 8px;
  padding: 10px;
  resize: vertical;
}
.comment-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}
.comment {
  background: var(--panel-2);
  border-radius: 8px;
  padding: 8px 10px;
}
.comment-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
}
.comment-text {
  font-size: 13px;
  margin-top: 4px;
}
.muted {
  color: var(--muted);
}
.small {
  font-size: 12px;
}
.drawer-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}
</style>
