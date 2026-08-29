<template>
  <div class="ai-page">
    <div class="ai-head">
      <div>
        <h2 class="ai-title">AI {{ tl('运维助手') }}</h2>
        <p class="ai-sub">
          {{ tl('遇到告警或突发情况不确定如何处置') }}？{{ tl('描述现场') }}，AI
          {{ tl('会基于知识库') }} / {{ tl('处置预案给出建议') }}。
        </p>
      </div>
      <div class="ai-head-right">
        <div class="ai-model-select">
          <label>{{ tl('模型') }}</label>
          <select v-model="activeModel" :disabled="modelsLoading" @change="onModelChange">
            <option v-for="m in models" :key="m.id" :value="m.id">
              {{ m.name }} · {{ m.vendor }}
            </option>
          </select>
        </div>
        <button class="ai-diag" :disabled="diagLoading" @click="runDiag">
          {{ diagLoading ? '诊断中…' : '诊断大模型' }}
        </button>
        <span class="ai-badge">{{ engineLabel }}</span>
      </div>
    </div>

    <transition name="fade">
      <div v-if="diag" class="ai-diag-panel" :class="{ err: diag.configured && !diag.reachable }">
        <div class="ai-diag-title">大模型接入诊断</div>
        <div class="ai-diag-row">
          <span>配置</span><b>{{ diag.configured ? '已配置' : '未配置' }}</b>
        </div>
        <div class="ai-diag-row"><span>端点</span>{{ diag.base_url }}</div>
        <div class="ai-diag-row"><span>模型</span>{{ diag.model }}</div>
        <div class="ai-diag-row">
          <span>可达性</span>
          <b :class="diag.reachable ? 'ok' : 'bad'">{{ diag.reachable ? '可达' : '不可达' }}</b>
          <template v-if="diag.http_status !== null">
            (HTTP {{ diag.http_status }}, {{ diag.latency }}s)</template
          >
        </div>
        <div v-if="diag.model_available !== null" class="ai-diag-row">
          <span>模型可用</span
          ><b :class="diag.model_available ? 'ok' : 'bad'">{{
            diag.model_available ? '是' : '否'
          }}</b>
        </div>
        <div class="ai-diag-detail">{{ diag.detail }}</div>
        <!-- Dify RAG 检索层状态 -->
        <template v-if="diag.dify">
          <div class="ai-diag-row ai-diag-sep">
            <span>Dify 检索层</span>
            <b :class="diag.dify.configured ? (diag.dify.reachable ? 'ok' : 'warn') : 'off'">{{
              !diag.dify.configured
                ? '未启用'
                : diag.dify.reachable
                  ? '已连接'
                  : '未连接'
            }}</b>
          </div>
          <template v-if="diag.dify.configured">
            <div class="ai-diag-row"><span>知识库 ID</span>{{ diag.dify.dataset_id || '—' }}</div>
            <div class="ai-diag-row">
              <span>召回探测</span
              ><b :class="diag.dify.reachable ? 'ok' : 'bad'">{{
                diag.dify.reachable ? '可用' : '失败'
              }}</b></div
            >
            <div class="ai-diag-detail">{{ diag.dify.detail }}</div>
          </template>
          <template v-else>
            <div class="ai-diag-detail">
              未配置 DIFY_API_KEY / DIFY_DATASET_ID，知识库检索走本地关键词打分兜底。
            </div>
          </template>
        </template>
      </div>
    </transition>

    <div class="ai-body">
      <!-- 对话区 -->
      <section class="ai-chat">
        <div ref="scrollRef" class="ai-msgs">
          <div v-if="messages.length === 0" class="ai-empty">
            <p>{{ tl('示例问题（点击直接提问）') }}：</p>
            <div class="ai-chips">
              <button v-for="q in examples" :key="q" class="ai-chip" @click="send(q)">
                {{ q }}
              </button>
            </div>
          </div>

          <div v-for="(m, i) in messages" :key="i" class="ai-row" :class="m.role">
            <div class="ai-bubble">
              <div v-if="m.role === 'ai' && m.loading" class="ai-typing">
                <span></span><span></span><span></span> {{ tl('正在检索知识库') }}…
              </div>
              <template v-else>
                <div v-if="m.llmError" class="ai-warn">
                  大模型调用失败：{{
                    m.llmError
                  }}。已回退本地知识库检索，结果仅供参考，建议核对模型配置后重试。
                </div>
                <pre class="ai-text">{{ m.text }}</pre>
                <ol v-if="m.steps && m.steps.length" class="ai-steps">
                  <li v-for="(s, k) in m.steps" :key="k">{{ s }}</li>
                </ol>
                <div v-if="m.refs && m.refs.length" class="ai-refs">
                  <span class="ai-refs-label">{{ tl('参考知识条目') }}：</span>
                  <!-- Dify 来源徽章 -->
                  <span
                    v-if="m.dify && m.dify.enabled"
                    class="ai-refs-badge"
                    :class="{ ok: m.dify.retrieved > 0, warn: m.dify.retrieved === 0 }"
                  >
                    <Sparkles class="ico" />
                    {{
                      m.dify.retrieved > 0
                        ? tl('Dify 知识库召回') + ' ' + m.dify.retrieved
                        : tl('Dify 未命中·本地兜底')
                    }}
                  </span>
                  <button
                    v-for="(r, k) in m.refs"
                    :key="k"
                    class="ai-ref"
                    :class="{ 'dify-ref': r.type === 'dify' }"
                    @click="openRef(r)"
                  >
                    <component :is="typeIcon(r.type)" class="ico" />
                    [{{ r.code }}] {{ r.title }}
                    <b v-if="r.type === 'dify' && r.score != null" class="dify-score">
                      {{ Math.round(r.score * 100) }}%
                    </b>
                  </button>
                </div>
                <div class="ai-fb" v-if="m.role === 'ai' && !m.loading">
                  <button class="ai-fb-btn" :class="{ on: m.feedback === 'up' }" @click="feedback(m, 'up')">
                    👍 {{ tl('有用') }}
                  </button>
                  <button class="ai-fb-btn" :class="{ on: m.feedback === 'down' }" @click="feedback(m, 'down')">
                    👎 {{ tl('无用') }}
                  </button>
                  <button class="ai-fb-btn" @click="openCorrect(m)">{{ tl('纠错') }}</button>
                </div>
              </template>
            </div>
          </div>
        </div>

        <div class="ai-input">
          <textarea
            v-model="question"
            rows="2"
            placeholder="例如：冷机出现喘振声，如何处理？"
            @keydown.enter.exact.prevent="send()"
          ></textarea>
          <button class="ai-send" :disabled="sending || !question.trim()" @click="send()">
            {{ sending ? '思考中…' : '发送' }}
          </button>
        </div>
      </section>

      <!-- 上下文侧栏 -->
      <aside class="ai-side">
        <h3 class="ai-side-title">现场上下文（可选，提升精度）</h3>
        <label class="ai-field">
          <span>业务域</span>
          <select v-model="ctx.domain">
            <option :value="null">— 不确定 —</option>
            <option value="hvac_source">暖通-冷源</option>
            <option value="hvac_terminal">暖通-末端</option>
            <option value="power_hv">电力-中压</option>
            <option value="power_lv">电力-低压</option>
            <option value="power_battery">电力-电池</option>
            <option value="power_genset">电力-柴发</option>
            <option value="security_fire">消防</option>
            <option value="security_cctv">安防-视频</option>
            <option value="security_acs">安防-门禁</option>
          </select>
        </label>
        <label class="ai-field">
          <span>当前系统 / 页面</span>
          <input v-model="ctx.system" placeholder="如 冷源群控 / 消防主机" />
        </label>
        <label class="ai-field">
          <span>当前告警 / 代码</span>
          <input v-model="ctx.alarm" placeholder="如 CH-01 喘振 / 电池内阻超标" />
        </label>
        <label class="ai-field">
          <span>相关测点</span>
          <input v-model="ctx.metric" placeholder="如 supply_temp" />
        </label>
        <p class="ai-tip">
          提示：上下文仅用于检索匹配，不会上传到外部模型；未配置大模型时回答完全基于本地知识库。
        </p>
      </aside>
    </div>

    <!-- 纠错弹窗 -->
    <transition name="fade">
      <div v-if="correctMsg" class="ai-corrmask" @click.self="correctMsg = null">
        <div class="ai-corrmodal">
          <div class="kb-modal-head">
            <h2>{{ tl('纠错 / 补充正确答案') }}</h2>
            <button class="kb-modal-close" @click="correctMsg = null">✕</button>
          </div>
          <p class="ai-corrtip">{{ tl('请描述正确处置方式，反馈将用于优化知识库与检索') }}：</p>
          <textarea v-model="correctText" class="ai-corrta" rows="5" :placeholder="tl('如：正确做法应为…')" />
          <div class="kb-modal-foot">
            <button class="kb-act-btn" @click="correctMsg = null">{{ tl('取消') }}</button>
            <button class="kb-act-btn primary" @click="submitCorrect">{{ tl('提交') }}</button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t: tl } = useI18n()
import { ref, reactive, nextTick } from 'vue'
import { toErrorMessage } from '@/composables/useAsyncPage'
import { useRouter } from 'vue-router'
import { askAssistant, submitAssistantFeedback, getAssistantModels, selectAssistantModel, assistantModelStatus } from '@/api'
import type { AssistantAskResp, AssistantRef, AssistantStatusResp, AssistantModel } from '@/types'
import { useToast } from '@/hooks/useToast'
import { BookOpen, Sparkles, FileText, Server, Database, Wrench, AlertTriangle } from 'lucide-vue-next'

// 知识来源类型 → 图标 (dify 为向量召回来源)
const REF_ICONS: Record<string, any> = {
  sop: FileText,
  manual: BookOpen,
  alarm: AlertTriangle,
  rule: Wrench,
  model: Server,
  dataset: Database,
  dify: Sparkles,
}
function typeIcon(type: string) {
  return REF_ICONS[type] || FileText
}

const router = useRouter()
const toast = useToast()

// 纠错弹窗
const correctMsg = ref<Msg | null>(null)
const correctText = ref('')

const question = ref('')
const sending = ref(false)
const scrollRef = ref<HTMLElement | null>(null)
const engineLabel = ref('知识库检索生成')

// 自定义模型列表
const models = ref<AssistantModel[]>([])
const activeModel = ref('')
const modelsLoading = ref(false)

async function loadModels() {
  modelsLoading.value = true
  try {
    const data = await getAssistantModels()
    models.value = data.models || []
    activeModel.value = data.active || (models.value[0] && models.value[0].id) || ''
  } catch (e) {
    models.value = []
  } finally {
    modelsLoading.value = false
  }
}

async function onModelChange() {
  if (!activeModel.value) return
  try {
    const res = await selectAssistantModel(activeModel.value)
    activeModel.value = res.active || activeModel.value
    toast.success('已切换模型：' + activeModel.value)
  } catch (e: any) {
    toast.error('切换模型失败：' + (toErrorMessage(e) || '未知错误'))
    loadModels() // 还原
  }
}

const diag = ref<AssistantStatusResp | null>(null)
const diagLoading = ref(false)

// 进入页面即加载自定义模型列表
loadModels()

interface Msg {
  role: 'user' | 'ai'
  text: string
  steps?: string[]
  refs?: AssistantRef[]
  loading?: boolean
  /** 大模型调用失败原因（配置了大模型却回退时填充） */
  llmError?: string
  /** Dify RAG 检索层状态: enabled / retrieved / error */
  dify?: { enabled: boolean; retrieved: number; error: string | null } | null
  /** 已反馈状态: up / down / null */
  feedback?: 'up' | 'down' | null
}

const messages = ref<Msg[]>([])

const ctx = reactive<{
  system: string
  domain: string | null
  metric: string
  alarm: string
  page: string | null
}>({
  system: '',
  domain: null,
  metric: '',
  alarm: '',
  page: null,
})

const examples = [
  '冷机运行中突然出现喘振声和振动，怎么办？',
  '市电中断后柴发怎么带载？',
  'UPS 蓄电池内阻超标怎么处理？',
  '机房温湿度超标要巡检哪些？',
  '消防主机报火警如何确认与疏散？',
]

async function send(q?: string) {
  const text = (q ?? question.value).trim()
  if (!text || sending.value) return
  lastQuestion.value = text
  messages.value.push({ role: 'user', text })
  const aiMsg: Msg = { role: 'ai', text: '', loading: true }
  messages.value.push(aiMsg)
  question.value = ''
  sending.value = true
  await scroll()

  const payload = {
    question: text,
    context: {
      system: ctx.system || null,
      domain: ctx.domain,
      metric: ctx.metric || null,
      alarm: ctx.alarm || null,
      page: ctx.page,
    },
  }

  try {
    const res = (await askAssistant(payload)) as AssistantAskResp
    aiMsg.loading = false
    aiMsg.text = res.answer
    aiMsg.steps = res.steps
    aiMsg.refs = res.refs
    aiMsg.llmError = res.llmError ?? undefined
    aiMsg.dify = res.dify ?? null
    if (res.grounded && res.llmError) {
      engineLabel.value = '知识库检索（大模型不可用）'
    } else {
      engineLabel.value = res.grounded ? '知识库检索生成' : `大模型 (${res.model})`
    }
  } catch (e: unknown) {
    aiMsg.loading = false
    aiMsg.text = '调用 AI 助手失败：' + (toErrorMessage(e) || '服务异常，请稍后重试。')
  } finally {
    sending.value = false
    await scroll()
  }
}

function openRef(r: AssistantRef) {
  router.push({ path: '/ops/knowledge', query: { q: r.code } })
}

const lastQuestion = ref('')

async function feedback(m: Msg, rating: 'up' | 'down') {
  if (m.feedback) return
  m.feedback = rating
  try {
    await submitAssistantFeedback({
      question: lastQuestion.value,
      answer: m.text,
      rating,
      grounded: engineLabel.value.includes('知识库') ? 'yes' : 'no',
      model: engineLabel.value,
    })
    toast.success(rating === 'up' ? tl('已记录好评') : tl('已记录差评'))
  } catch {
    m.feedback = null
    toast.error(tl('反馈提交失败'))
  }
}

function openCorrect(m: Msg) {
  correctMsg.value = m
  correctText.value = ''
}

async function submitCorrect() {
  if (!correctMsg.value) return
  const m = correctMsg.value
  try {
    await submitAssistantFeedback({
      question: lastQuestion.value,
      answer: m.text,
      rating: 'down',
      correction: correctText.value,
      grounded: engineLabel.value.includes('知识库') ? 'yes' : 'no',
      model: engineLabel.value,
    })
    m.feedback = 'down'
    toast.success(tl('纠错已提交，感谢反馈'))
    correctMsg.value = null
  } catch {
    toast.error(tl('纠错提交失败'))
  }
}

async function scroll() {
  await nextTick()
  if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight
}

async function runDiag() {
  diagLoading.value = true
  try {
    const target = activeModel.value
    diag.value = await assistantModelStatus(target || activeModel.value)
  } catch (e: unknown) {
    diag.value = {
      configured: false,
      base_url: '-',
      model: activeModel.value || '-',
      reachable: false,
      http_status: null,
      latency: null,
      model_available: null,
      detail: '诊断失败：' + (toErrorMessage(e) || '无法连接后端'),
    }
  } finally {
    diagLoading.value = false
  }
}
</script>

<style scoped>
.ai-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  gap: 14px;
}
.ai-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}
.ai-title {
  margin: 0;
  font-size: 20px;
  color: var(--txt);
}
.ai-sub {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 13px;
  max-width: 720px;
}
.ai-badge {
  flex: none;
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: var(--cyan);
  font-size: 12px;
  background: var(--panel);
}
.ai-head-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}
.ai-model-select {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--bg2);
  color: var(--txt);
  font-size: 12px;
}
.ai-model-select label {
  color: var(--txt2);
}
.ai-model-select select {
  background: transparent;
  border: none;
  color: var(--txt-strong);
  font-size: 12px;
  outline: none;
  cursor: pointer;
  max-width: 200px;
}
.ai-model-select select option {
  background: var(--bg2);
  color: var(--txt);
}
.ai-diag {
  padding: 6px 14px;
  border: 1px solid var(--cyan);
  border-radius: 8px;
  background: transparent;
  color: var(--cyan);
  font-size: 12px;
  cursor: pointer;
}
.ai-diag:hover {
  background: rgba(34, 211, 238, 0.12);
}
.ai-diag:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-diag-panel {
  margin-top: 2px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 10px;
  background: var(--panel);
  font-size: 13px;
  color: var(--txt);
}
.ai-diag-panel.err {
  border-color: #f59e0b;
}
.ai-diag-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--cyan);
}
.ai-diag-row {
  display: flex;
  gap: 8px;
  padding: 2px 0;
}
.ai-diag-row > span {
  flex: none;
  width: 64px;
  color: var(--muted);
}
.ai-diag-row .ok {
  color: #22c55e;
}
.ai-diag-row .bad {
  color: #f59e0b;
}
.ai-diag-detail {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--line);
  color: var(--muted);
  line-height: 1.6;
}
.ai-diag-sep {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--line);
}
.ai-diag-detail b.ok {
  color: #22c55e;
}
.ai-diag-detail b.bad {
  color: #ef4444;
}
.ai-diag-detail b.warn {
  color: #f59e0b;
}
.ai-diag-detail b.off {
  color: var(--muted);
}

.ai-warn {
  margin-bottom: 8px;
  padding: 8px 10px;
  border: 1px solid #f59e0b;
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.1);
  color: #f59e0b;
  font-size: 12px;
  line-height: 1.6;
}

.ai-body {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 14px;
  flex: 1;
  min-height: 0;
}
.ai-chat {
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}

.ai-msgs {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.ai-empty {
  color: var(--muted);
  font-size: 13px;
}
.ai-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 10px;
}
.ai-chip {
  background: var(--bg2);
  border: 1px solid var(--line);
  color: var(--txt);
  border-radius: 999px;
  padding: 6px 12px;
  font-size: 12px;
  cursor: pointer;
}
.ai-chip:hover {
  border-color: var(--cyan);
}

.ai-row {
  display: flex;
}
.ai-row.user {
  justify-content: flex-end;
}
.ai-row.ai {
  justify-content: flex-start;
}
.ai-bubble {
  max-width: 86%;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: var(--bg2);
  font-size: 13px;
  line-height: 1.7;
}
.ai-row.user .ai-bubble {
  background: #0e2a33;
  border-color: var(--cyan);
  color: var(--txt);
}
.ai-row.ai .ai-bubble {
  border-left: 3px solid var(--cyan);
}
.ai-text {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  color: var(--txt);
}
.ai-steps {
  margin: 10px 0 0;
  padding-left: 20px;
  color: var(--txt);
}
.ai-steps li {
  margin: 2px 0;
}
.ai-refs {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.ai-refs-label {
  color: var(--muted);
  font-size: 12px;
}
.ai-ref {
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--cyan);
  border-radius: 6px;
  padding: 3px 8px;
  font-size: 12px;
  cursor: pointer;
}
.ai-ref:hover {
  border-color: var(--cyan);
}
/* Dify 召回来源标识 */
.ai-ref.dify-ref {
  color: #c084fc;
  border-color: rgba(192, 132, 252, 0.45);
  background: rgba(192, 132, 252, 0.08);
}
.ai-ref .ico {
  width: 12px;
  height: 12px;
  vertical-align: -2px;
  margin-right: 3px;
}
.dify-score {
  margin-left: 4px;
  color: #c084fc;
  font-weight: 700;
}
.ai-refs-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
}
.ai-refs-badge .ico {
  width: 12px;
  height: 12px;
}
.ai-refs-badge.ok {
  color: #c084fc;
  background: rgba(192, 132, 252, 0.12);
  border: 1px solid rgba(192, 132, 252, 0.4);
}
.ai-refs-badge.warn {
  color: #f59e0b;
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.4);
}

.ai-typing {
  color: var(--muted);
  display: flex;
  align-items: center;
  gap: 4px;
}
.ai-typing span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--cyan);
  animation: blink 1.2s infinite;
}
.ai-typing span:nth-child(2) {
  animation-delay: 0.2s;
}
.ai-typing span:nth-child(3) {
  animation-delay: 0.4s;
}
@keyframes blink {
  0%,
  100% {
    opacity: 0.2;
  }
  50% {
    opacity: 1;
  }
}

.ai-input {
  display: flex;
  gap: 10px;
  padding: 12px;
  border-top: 1px solid var(--line);
  background: var(--bg2);
}
.ai-input textarea {
  flex: 1;
  resize: none;
  background: var(--bg);
  color: var(--txt);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
}
.ai-input textarea:focus {
  outline: none;
  border-color: var(--cyan);
}
.ai-send {
  flex: none;
  align-self: stretch;
  padding: 0 18px;
  border: none;
  border-radius: 8px;
  background: var(--cyan);
  color: #04181d;
  font-weight: 600;
  cursor: pointer;
}
.ai-send:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.ai-side {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: fit-content;
}
.ai-side-title {
  margin: 0;
  font-size: 14px;
  color: var(--txt);
}
.ai-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
}
.ai-field select,
.ai-field input {
  background: var(--bg);
  color: var(--txt);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 7px 9px;
  font-size: 13px;
  font-family: inherit;
}
.ai-field select:focus,
.ai-field input:focus {
  outline: none;
  border-color: var(--cyan);
}
.ai-tip {
  font-size: 11px;
  color: var(--muted);
  line-height: 1.6;
  margin: 0;
}

.ai-fb {
  margin-top: 10px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.ai-fb-btn {
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--muted);
  border-radius: 999px;
  padding: 3px 12px;
  font-size: 12px;
  cursor: pointer;
}
.ai-fb-btn:hover {
  border-color: var(--cyan);
  color: var(--txt);
}
.ai-fb-btn.on {
  background: rgba(34, 211, 238, 0.12);
  border-color: var(--cyan);
  color: var(--cyan);
}

.ai-corrmask {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
}
.ai-corrmodal {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 12px;
  width: min(520px, 92vw);
  padding: 20px 24px;
}
.ai-corrtip {
  font-size: 12px;
  color: var(--muted);
  margin: 4px 0 10px;
}
.ai-corrta {
  width: 100%;
  box-sizing: border-box;
  background: var(--bg);
  color: var(--txt);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
}
.ai-corrta:focus {
  outline: none;
  border-color: var(--cyan);
}
</style>
