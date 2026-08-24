<template>
  <div class="page-wrap">
    <div class="view-head">
      <div class="vh-icon">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8">
          <path d="M13 2L4 14h6l-1 8 9-12h-6l1-8z" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>
        <h1>{{ t.title }}</h1>
        <div class="sub">{{ t.sub }}</div>
      </div>
      <div class="vh-right">
        <button class="btn-primary" @click="openCreate">{{ t.newRule }}</button>
      </div>
    </div>

    <!-- 概览 -->
    <div class="grid cols-4">
      <div class="card" style="padding:14px">
        <div class="text-xs" style="color:var(--txt2)">{{ t.total }}</div>
        <div class="text-2xl font-semibold" style="color:var(--txt-strong)">{{ rules.length }}</div>
      </div>
      <div class="card" style="padding:14px">
        <div class="text-xs" style="color:var(--txt2)">{{ t.enabledCount }}</div>
        <div class="text-2xl font-semibold" style="color:var(--green)">{{ rules.filter(r => r.enabled).length }}</div>
      </div>
      <div class="card" style="padding:14px">
        <div class="text-xs" style="color:var(--txt2)">{{ t.highRisk }}</div>
        <div class="text-2xl font-semibold" style="color:var(--red)">{{ rules.filter(r => r.level === 'high').length }}</div>
      </div>
      <div class="card" style="padding:14px">
        <div class="text-xs" style="color:var(--txt2)">{{ t.aiScanned }}</div>
        <div class="text-2xl font-semibold" style="color:var(--blue)">{{ aiScans }}</div>
      </div>
    </div>

    <!-- 筛选 -->
    <div class="flex gap-2 flex-wrap">
      <select v-model="fCat" class="inp w-44">
        <option value="all">{{ t.allCat }}</option>
        <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
      </select>
      <select v-model="fLevel" class="inp w-36">
        <option value="all">{{ t.allLevel }}</option>
        <option value="high">{{ t.high }}</option>
        <option value="mid">{{ t.mid }}</option>
        <option value="low">{{ t.low }}</option>
      </select>
      <input v-model="kw" class="inp flex-1" style="min-width:180px" :placeholder="t.search" />
      <button class="btn-primary" @click="aiScan" :disabled="aiLoading">
        <span v-if="aiLoading" class="spin-ic" style="display:inline-block;animation:spin 1s linear infinite">◐</span>{{ aiLoading ? t.aiScanning : t.aiScanBtn }}
      </button>
    </div>

    <!-- 隐患规则列表 -->
    <div class="grid cols-3">
      <div v-for="r in filtered" :key="r.id" class="card flex flex-col">
        <div class="flex items-start justify-between">
          <div class="flex items-center gap-2">
            <span class="tag" :class="levelClass(r.level)">{{ levelLabel(r.level) }}</span>
            <span class="pill">{{ r.category }}</span>
          </div>
          <button class="btn-sm" :class="r.enabled ? '' : 'btn-primary'" @click="toggle(r)">
            {{ r.enabled ? t.disable : t.enable }}
          </button>
        </div>
        <h3 class="font-semibold mt-2 cell-strong">{{ r.name }}</h3>
        <p class="text-sm mt-1 flex-1" style="color:var(--txt2)">{{ r.desc }}</p>
        <div class="mt-2 text-xs space-y-1" style="color:var(--txt2)">
          <div>{{ t.signal }}: <span class="mono">{{ r.signal }}</span></div>
          <div>{{ t.threshold }}: {{ r.threshold }}</div>
          <div>{{ t.action }}: {{ r.action }}</div>
        </div>
        <div v-if="r.aiNote" class="mt-2 p-2 rounded text-xs" style="background:rgba(59,130,246,.12);color:var(--blue)">
          <b>{{ t.aiTag }}</b> {{ r.aiNote }}
        </div>
        <div class="mt-3 flex gap-2">
          <button class="btn-primary flex-1" @click="aiJudge(r)" :disabled="aiLoading">{{ t.aiJudge }}</button>
          <button class="btn-ghost" @click="edit(r)">{{ t.edit }}</button>
          <button class="btn-danger" @click="remove(r.id)">{{ t.del }}</button>
        </div>
      </div>
    </div>
    <div v-if="!filtered.length" class="card empty-box">{{ t.empty }}</div>

    <!-- 编辑弹窗 -->
    <div v-if="showModal" class="modal-mask" @click.self="showModal = false">
      <div class="modal">
        <h3>{{ editing ? t.editRule : t.newRule }}</h3>
        <div class="space-y">
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>{{ t.name }}</span><input v-model="form.name" class="inp" :placeholder="t.namePlaceholder" /></div>
            <div class="field"><span>{{ t.category }}</span><input v-model="form.category" class="inp" :placeholder="t.catPlaceholder" /></div>
          </div>
          <div class="grid cols-2" style="gap:12px">
            <div class="field"><span>{{ t.level }}</span>
              <select v-model="form.level" class="inp">
                <option value="high">{{ t.high }}</option>
                <option value="mid">{{ t.mid }}</option>
                <option value="low">{{ t.low }}</option>
              </select>
            </div>
            <div class="field"><span>{{ t.signal }}</span><input v-model="form.signal" class="inp mono" :placeholder="t.signalPlaceholder" /></div>
          </div>
          <div class="field"><span>{{ t.threshold }}</span><input v-model="form.threshold" class="inp" :placeholder="t.thresholdPlaceholder" /></div>
          <div class="field"><span>{{ t.desc }}</span><textarea v-model="form.desc" rows="2" class="inp" :placeholder="t.descPlaceholder"></textarea></div>
          <div class="field"><span>{{ t.action }}</span><input v-model="form.action" class="inp" :placeholder="t.actionPlaceholder" /></div>
        </div>
        <div class="modal-actions">
          <button class="btn-ghost" @click="showModal = false">{{ t.cancel }}</button>
          <button class="btn-primary" @click="save">{{ t.save }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { askAssistant } from '@/api'

const { t: raw } = useI18n()
const t = new Proxy({} as any, {
  get(_t, key) {
    const ns = (raw('powerAiHazards') || {}) as any
    return ns && typeof ns === 'object' ? ns[key] : ''
  },
})

interface Hazard {
  id: string; name: string; category: string; level: 'high' | 'mid' | 'low'
  signal: string; threshold: string; desc: string; action: string
  enabled: boolean; aiNote?: string
}

const KEY = 'w10_hazards'
const rules = ref<Hazard[]>([])
const fCat = ref<string>('all')
const fLevel = ref<string>('all')
const kw = ref('')
const showModal = ref(false)
const editing = ref(false)
const form = ref<Hazard>(blank())
const aiScans = ref(Number(localStorage.getItem('w10_ai_scans') || 0))
const aiLoading = ref(false)

function blank(): Hazard {
  return { id: '', name: '', category: 'power', level: 'mid', signal: '', threshold: '', desc: '', action: '', enabled: true }
}

function load() {
  rules.value = JSON.parse(localStorage.getItem(KEY) || 'null') || seed()
  localStorage.setItem(KEY, JSON.stringify(rules.value))
}
function seed(): Hazard[] {
  return [
    { id: 'hz1', name: '断路器触点温升异常', category: 'power', level: 'high', signal: 'breaker.temp', threshold: '> 70℃ 或 温升 > 40K', desc: '断路器触头接触电阻增大导致温升超标，存在熔焊/起火风险。', action: '立即安排红外复测，必要时减载并安排检修', enabled: true },
    { id: 'hz2', name: 'UPS 蓄电池内阻偏高', category: 'power', level: 'high', signal: 'ups.battery.ir', threshold: '内阻 > 标称 1.5 倍', desc: '单体电池内阻持续上升，容量衰减，断电时后备时间不足。', action: '更换异常电池组并做容量核试验证', enabled: true },
    { id: 'hz3', name: '母线谐波畸变率超标', category: 'power', level: 'mid', signal: 'busbar.thd', threshold: 'THD > 8%', desc: '非线性负载引起谐波放大，导致中性线过载与设备误动。', action: '加装滤波装置，核查非线性负载分布', enabled: true },
    { id: 'hz4', name: '馈线三相不平衡', category: 'power', level: 'mid', signal: 'feeder.imbalance', threshold: '不平衡度 > 15%', desc: '三相负荷分配不均，中性点偏移、变压器损耗增加。', action: '重新平衡各相负荷', enabled: false },
    { id: 'hz5', name: '接地电阻异常', category: 'power', level: 'low', signal: 'ground.resistance', threshold: '> 4Ω', desc: '接地网腐蚀或断裂，雷击/故障残压抬升威胁人身安全。', action: '雨后复测，必要时增补接地极', enabled: true },
    { id: 'hz6', name: '变压器油位/温度异常', category: 'power', level: 'high', signal: 'transformer.oil', threshold: '油位低或顶层油温 > 85℃', desc: '冷却失效或内部故障前兆，存在爆燃风险。', action: '核查冷却系统，红外+油色谱分析', enabled: true },
    { id: 'hz7', name: '浪涌保护器失效', category: 'power', level: 'mid', signal: 'spd.status', threshold: '状态指示为失效', desc: 'SPD 窗口变红，雷击防护能力丧失。', action: '更换模块并记录雷击事件', enabled: true },
    { id: 'hz8', name: '柴油发电机带载能力不足', category: 'power', level: 'mid', signal: 'genset.load', threshold: '带载率 < 额定 80% 且 启动超时', desc: '长期空载导致启动困难，市电中断时无法按期接管。', action: '按月带载试机并核查燃油/液位', enabled: false },
    { id: 'hz9', name: 'PDU 插座温升', category: 'power', level: 'low', signal: 'pdu.outlet.temp', threshold: '> 55℃', desc: '插接头松动或过载，局部过热引燃风险。', action: '紧固端子、核查单回路负荷', enabled: true },
    { id: 'hz10', name: '并机环流超标', category: 'power', level: 'high', signal: 'paralleling.circ', threshold: '环流 > 额定 5%', desc: '多机并联均流异常，单机过载老化加速。', action: '调整调差系数，核查同步信号', enabled: true },
    { id: 'hz11', name: '电容补偿柜鼓包', category: 'power', level: 'mid', signal: 'cap.bank', threshold: '外壳鼓包/漏液', desc: '电容器介质劣化，存在爆裂风险。', action: '退出运行并更换，核查投切策略', enabled: true },
    { id: 'hz12', name: '列头柜电压瞬降', category: 'power', level: 'low', signal: 'rpp.voltage.dip', threshold: '瞬时跌落 > 10%', desc: '上游切换或启动冲击导致 IT 设备重启。', action: '核查切换时序，必要时加装 AVR', enabled: false },
    { id: 'hz13', name: '直流屏蓄电池欠压', category: 'power', level: 'high', signal: 'dc.screen.voltage', threshold: '母线电压 < 下限', desc: '直流操作电源失压，保护/开关拒动。', action: '立即充电并核容，排查充电机', enabled: true },
    { id: 'hz14', name: '功率因数偏低', category: 'power', level: 'low', signal: 'pfc', threshold: 'cosφ < 0.9', desc: '无功损耗大，力调电费罚款。', action: '投运补偿、优化分组', enabled: true },
    { id: 'hz15', name: '电流互感器二次侧开路', category: 'power', level: 'high', signal: 'ct.secondary', threshold: '开路高压告警', desc: 'CT 开路产生高电压，危及人身与绝缘。', action: '停电处理，严禁带电拆线', enabled: true },
    { id: 'hz16', name: '开关柜局放超标', category: 'power', level: 'mid', signal: 'switchgear.pd', threshold: 'TEV > 20dB', desc: '绝缘缺陷早期表征，可能发展为击穿。', action: '超声+地电波复测，安排解体', enabled: true },
    { id: 'hz17', name: '应急照明逆变故障', category: 'power', level: 'low', signal: 'emergency.inv', threshold: '切换失败', desc: '事故照明缺失，疏散风险。', action: '季度功能测试并更换电池', enabled: true },
    { id: 'hz18', name: '馈线绝缘老化', category: 'power', level: 'mid', signal: 'feeder.insul', threshold: '绝缘阻值 < 1MΩ', desc: '电缆受潮/老化，漏电与短路风险。', action: '耐压试验，定位并更换段', enabled: false },
    { id: 'hz19', name: 'ATS 切换时间过长', category: 'power', level: 'mid', signal: 'ats.switch', threshold: '切换 > 设计值', desc: '双电源切换间隙导致设备掉电。', action: '校准控制器，核查机械联锁', enabled: true },
    { id: 'hz20', name: '剩余电流保护误动/拒动', category: 'power', level: 'high', signal: 'rcd', threshold: '动作异常', desc: '漏保失效则触电无保护，误动则非计划停电。', action: '月度测试按钮核查定值', enabled: true },
    { id: 'hz21', name: '母线槽连接温升', category: 'power', level: 'mid', signal: 'busway.temp', threshold: '> 65℃', desc: '插接箱接触不良，过热引燃。', action: '扭矩复检，红外巡检', enabled: true },
    { id: 'hz22', name: '电池间氢浓度超标', category: 'power', level: 'high', signal: 'battery.room.h2', threshold: 'H2 > 1%', desc: '充电析氢积聚，爆炸风险。', action: '加强通风，加装氢探', enabled: true },
  ]
}

const categories = computed(() => Array.from(new Set(rules.value.map(r => r.category))))
const filtered = computed(() =>
  rules.value.filter(r =>
    (fCat.value === 'all' || r.category === fCat.value) &&
    (fLevel.value === 'all' || r.level === fLevel.value) &&
    (r.name.includes(kw.value) || r.desc.includes(kw.value) || r.signal.includes(kw.value))
  )
)

function levelClass(l: string) {
  return { high: 'r', mid: 'a', low: 'b' }[l] || ''
}
function levelLabel(l: string) {
  return { high: t.high, mid: t.mid, low: t.low }[l] || l
}
function toggle(r: Hazard) {
  r.enabled = !r.enabled
  localStorage.setItem(KEY, JSON.stringify(rules.value))
}
function openCreate() {
  editing.value = false
  form.value = blank()
  showModal.value = true
}
function edit(r: Hazard) {
  editing.value = true
  form.value = { ...r }
  showModal.value = true
}
function save() {
  if (editing.value) {
    const i = rules.value.findIndex(r => r.id === form.value.id)
    if (i >= 0) rules.value[i] = { ...form.value }
  } else {
    rules.value.push({ ...form.value, id: 'hz' + Date.now() })
  }
  localStorage.setItem(KEY, JSON.stringify(rules.value))
  showModal.value = false
}
function remove(id: string) {
  rules.value = rules.value.filter(r => r.id !== id)
  localStorage.setItem(KEY, JSON.stringify(rules.value))
}

// 模拟全量扫描：对每条规则做一次 AI 研判
async function aiScan() {
  aiLoading.value = true
  try {
    for (const r of rules.value) {
      await judgeOne(r, false)
    }
    aiScans.value++
    localStorage.setItem('w10_ai_scans', String(aiScans.value))
  } finally {
    aiLoading.value = false
  }
}
async function aiJudge(r: Hazard) {
  aiLoading.value = true
  try {
    await judgeOne(r, true)
  } finally {
    aiLoading.value = false
  }
}
async function judgeOne(r: Hazard, _toast: boolean) {
  try {
    const prompt = `作为数据中心供配电运维专家，针对隐患「${r.name}」（测点 ${r.signal}，阈值 ${r.threshold}），结合实时遥测给出一句风险研判与优先级建议（不超过 40 字）。`
    const resp = await askAssistant({ question: prompt })
    const note = (resp as any)?.answer || (resp as any)?.text || ''
    if (note) r.aiNote = note.replace(/\n/g, ' ').slice(0, 80)
    localStorage.setItem(KEY, JSON.stringify(rules.value))
  } catch {
    r.aiNote = t.aiUnavailable
    localStorage.setItem(KEY, JSON.stringify(rules.value))
  }
}

onMounted(load)
</script>
