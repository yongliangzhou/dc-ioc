<template>
  <div>
    <div class="view-head">
      <h1>{{ tl('运维作业') }} {{ tl('·') }} {{ tl('事件工单中心') }}</h1>
      <span class="sub">{{ tl('工单') }} CRUD {{ tl('生命周期') }} {{ tl('·') }} {{ tl('告警自动转单') }} {{ tl('·') }} {{ tl('状态流转') }} {{ tl('·') }} SLA {{ tl('跟踪') }} {{ tl('·') }} {{ tl('按看板分组') }}</span>
      <button class="hdr-btn" v-bind="authState('write')" @click="openCreate">+ {{ tl('新建工单') }}</button>
    </div>

    <!-- KPI -->
    <div class="grid cols-4" v-if="store">
      <div class="card kpi-card"><div class="ct">{{ tl('待处理') }}</div><div class="cv" style="color:var(--amber)">{{ stats.open }}<small>{{ tl('单') }}</small></div></div>
      <div class="card kpi-card"><div class="ct">{{ tl('处理中') }}</div><div class="cv" style="color:var(--cyan)">{{ stats.doing }}<small>{{ tl('单') }}</small></div></div>
      <div class="card kpi-card"><div class="ct">{{ tl('待归档') }}</div><div class="cv">{{ stats.pending }}<small>{{ tl('单') }}</small></div></div>
      <div class="card kpi-card"><div class="ct">{{ tl('累计闭环') }}</div><div class="cv" style="color:var(--green)">{{ stats.done }}<small>{{ tl('单') }}</small></div></div>
    </div>

    <!-- 工具条 -->
    <div class="card toolbar">
      <input v-model.trim="kw" class="ipt" :placeholder="tl('搜索工单号 / 标题 / 责任')" style="width:220px" />
      <select v-model="fStatus" class="ipt" style="width:120px">
        <option value="">{{ tl('全部状态') }}</option>
        <option v-for="s in STATUS_ORDER" :key="s" :value="s">{{ statusLabel(s) }}</option>
      </select>
      <select v-model="fLv" class="ipt" style="width:110px">
        <option value="">{{ tl('全部级别') }}</option>
        <option value="crit">{{ tl('紧急') }}</option>
        <option value="warn">{{ tl('重要') }}</option>
        <option value="info">{{ tl('提示') }}</option>
      </select>
      <div class="flex1"></div>
      <div class="seg">
        <button :class="{ on: view==='kanban' }" @click="view='kanban'">{{ tl('看板') }}</button>
        <button :class="{ on: view==='table' }" @click="view='table'">{{ tl('列表') }}</button>
      </div>
    </div>

    <!-- 看板视图 -->
    <template v-if="view==='kanban'">
      <div class="kanban" v-if="store">
        <div class="kcol" v-for="col in STATUS_ORDER" :key="col">
          <div class="kh">
            <span :style="{ color: colColor(col) }">{{ statusLabel(col) }}</span>
            <span class="muted">{{ filtered.filter(x => x.state === col).length }}</span>
          </div>
          <div class="kcard-i" v-for="x in filtered.filter(y => y.state === col)" :key="x.id" @click="openDetail(x)">
            <div class="flex between">
              <b>{{ x.title }}</b>
              <span class="tag" :class="lvClass(x.lv)">{{ lvText(x.lv) }}</span>
            </div>
            <div class="km">{{ x.id }} {{ tl('·') }} {{ x.sys }} {{ tl('·') }} {{ x.owner }}</div>
            <div class="km">{{ tl('创建') }} {{ x.created }} {{ tl('·') }} SLA {{ x.sla }}</div>
            <div class="progress kbar" style="height:5px"><i :style="{ width: x.progress + '%', background: colColor(col) }"></i></div>
            <div class="kacts" @click.stop>
              <button class="kbtn" v-if="col!=='done'" v-bind="authState('write')" @click="advance(x)" :title="tl('推进到下一状态')">{{ tl('推进') }} ▸</button>
              <button class="kbtn ghost" v-bind="authState('write')" @click="openEdit(x)" :title="tl('编辑')">✎</button>
              <button class="kbtn ghost danger" v-bind="authState('write')" @click="askDelete(x)" :title="tl('删除')">🗑</button>
            </div>
          </div>
          <div class="kempty muted" v-if="!filtered.filter(y => y.state === col).length">{{ tl('无工单') }}</div>
        </div>
      </div>
    </template>

    <!-- 列表视图 -->
    <template v-else>
      <div class="card scroll-x" v-if="store">
        <table>
          <thead><tr><th>工单号</th><th>标题</th><th>系统</th><th>级别</th><th>状态</th><th>责任</th><th>创建时间</th><th>SLA</th><th>进度</th><th style="width:140px">操作</th></tr></thead>
          <tbody>
            <tr v-for="x in filtered" :key="x.id" @click="openDetail(x)" style="cursor:pointer">
              <td class="mono">{{ x.id }}</td><td>{{ x.title }}</td><td>{{ x.sys }}</td>
              <td><span class="tag" :class="lvClass(x.lv)">{{ lvText(x.lv) }}</span></td>
              <td><span class="tag" :class="tagClass(x.state)">{{ statusLabel(x.state) }}</span></td>
              <td>{{ x.owner }}</td><td class="mono">{{ x.created }}</td><td>{{ x.sla }}</td>
              <td><div class="progress" style="width:80px"><i :style="{ width: x.progress + '%', background: pctColor(x.progress, 50, 80) }"></i></div></td>
              <td>
                <div class="flex gap4" @click.stop>
                  <button class="act-btn" v-if="x.state!=='done'" v-bind="authState('write')" @click="advance(x)">推进</button>
                  <button class="act-btn ghost" v-bind="authState('write')" @click="openEdit(x)">编辑</button>
                  <button class="act-btn danger" v-bind="authState('write')" @click="askDelete(x)">删</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="muted" style="text-align:center;padding:18px" v-if="!filtered.length">无匹配工单</div>
      </div>
    </template>

    <!-- 新建 / 编辑弹窗 -->
    <TicketFormModal
      :open="formOpen"
      :title="editing ? '编辑工单' : '新建工单'"
      :is-edit="!!editing"
      :initial="formInitial"
      @close="closeForm"
      @submit="onFormSubmit"
    />

    <!-- 详情 / 生命周期弹窗 -->
    <teleport to="body">
      <div v-if="detail" class="tf-mask" @click.self="detail=null">
        <div class="tf-modal">
          <div class="tf-head">
            <h3>工单详情 · 生命周期</h3>
            <button class="tf-x" @click="detail=null">✕</button>
          </div>
          <div class="tf-body">
            <div class="dv-row"><span class="dv-k">工单号</span><span class="dv-v mono">{{ detail.id }}</span></div>
            <div class="dv-row"><span class="dv-k">标题</span><span class="dv-v">{{ detail.title }}</span></div>
            <div class="dv-row"><span class="dv-k">系统 / 级别</span><span class="dv-v">{{ detail.sys }} · <span class="tag" :class="lvClass(detail.lv)">{{ lvText(detail.lv) }}</span></span></div>
            <div class="dv-row"><span class="dv-k">责任 / SLA</span><span class="dv-v">{{ detail.owner }} · {{ detail.sla }}</span></div>
            <div class="dv-row"><span class="dv-k">来源</span><span class="dv-v">
              <span class="tag" :class="detail.source==='alarm' ? 'r' : 'b'">{{ detail.source==='alarm' ? '告警转单' : '手动创建' }}</span>
              <span v-if="detail.sourceAlarmId" class="mono muted"> ({{ detail.sourceAlarmId }})</span>
            </span></div>
            <div class="dv-row"><span class="dv-k">进度</span><span class="dv-v">
              <div class="progress" style="width:160px;display:inline-block;vertical-align:middle"><i :style="{ width: detail.progress + '%', background: pctColor(detail.progress, 50, 80) }"></i></div>
              {{ detail.progress }}%
            </span></div>
            <div class="dv-desc"><b>描述</b><p>{{ detail.description || '—' }}</p></div>

            <div class="dv-section">状态流转</div>
            <div class="seg full">
              <button
                v-for="s in STATUS_ORDER" :key="s"
                :class="{ on: detail.state===s }"
                :disabled="detail.state===s"
                @click="jumpState(detail, s)"
              >{{ statusLabel(s) }}</button>
            </div>

            <div class="dv-section">操作日志 ({{ detail.logs.length }})</div>
            <div class="loglist">
              <div class="logitem" v-for="(l, i) in [...detail.logs].reverse()" :key="i">
                <span class="ldot" :class="logColor(l.action)"></span>
                <div class="ltxt">
                  <b>{{ logText(l) }}</b>
                  <div class="lmeta">{{ l.operator }} · {{ l.ts }}<span v-if="l.note"> · {{ l.note }}</span></div>
                </div>
              </div>
            </div>
          </div>
          <div class="tf-foot">
            <button class="tf-btn ghost" @click="detail=null">关闭</button>
            <button class="tf-btn primary" v-if="detail.state!=='done'" @click="advance(detail); detail=store.getById(detail.id) ?? null">推进状态</button>
          </div>
        </div>
      </div>
    </teleport>

    <!-- 删除确认 -->
    <teleport to="body">
      <div v-if="toDelete" class="tf-mask" @click.self="toDelete=null">
        <div class="tf-modal" style="width:380px">
          <div class="tf-head"><h3>确认删除工单</h3><button class="tf-x" @click="toDelete=null">✕</button></div>
          <div class="tf-body">
            <p style="color:var(--txt);font-size:13px;margin:0">
              确定删除工单 <b class="mono">{{ toDelete.id }}</b>「{{ toDelete.title }}」？此操作不可恢复。
            </p>
          </div>
          <div class="tf-foot">
            <button class="tf-btn ghost" @click="toDelete=null">取消</button>
            <button class="tf-btn primary" style="background:var(--red,#ff4d5e)" @click="doDelete">删除</button>
          </div>
        </div>
      </div>
    </teleport>

    <KnowledgePanels :knowledge="ticketKb" />

    <div class="footer-note">运维作业·事件工单中心 — 全生命周期 CRUD · {{ store?.tickets.length ?? 0 }} 张工单 · 数据存于本地 (localStorage)</div>
  </div>
</template>

<script setup lang="ts">import { useI18n } from "vue-i18n";
const { t: tl } = useI18n();
import { computed, ref } from "vue";
import { storeToRefs } from "pinia";
import { useTicketsStore } from "@/stores/modules/tickets";
import { lvClass, lvText, tagClass, pctColor } from "@/utils/state";
import { TICKET_STATUS_ORDER, TICKET_STATUS_LABEL } from "@/types";
import type { Ticket, TicketStatus, TicketCreateRequest, PowerKnowledge } from "@/types"
import KnowledgePanels from "@/components/KnowledgePanels.vue";
import TicketFormModal from "@/components/business/TicketFormModal.vue";
import { useToast } from "@/hooks/useToast";
import { usePermission, type PermAction } from "@/hooks/usePermission";

const toast = useToast();
const { can, denyTip } = usePermission();
function authState(action: PermAction) {
  const ok = can(action);
  return { disabled: !ok, title: ok ? "" : denyTip(action) };
}

const store = useTicketsStore();
const { stats, tickets } = storeToRefs(store);
const ticketKb: PowerKnowledge = {
  thresholds: [
    { k: tl('闭环跟踪'), v: "告警→工单→问题→风险", note: "EOP 覆盖 62 类事件" },
    { k: "闭环率(自动关闭)", v: "71%", note: "SLA 跟踪 MTTA/MTTR" },
  ],
  arch: {
    components: ["告警中心", "事件工单(Tickets)", "问题根因", "风险中心(Risk)", "知识库/EOP"],
    design: "工单是运维闭环的纽带：一条告警生成工单，处置沉淀为问题，反复/高危升级为风险。",
    redundancy: "全生命周期 CRUD，状态可追踪。",
  },
  logic: [
    { title: tl('事件→问题→风险 双闭环'), steps: [
      { step: 1, text: tl('告警触发 → 生成事件工单'), ok: true },
      { step: 2, text: tl('工单处置沉淀为问题根因'), ok: true },
      { step: 3, text: tl('反复/高危问题升级为风险项并跟踪'), ok: true },
      { step: 4, text: tl('EOP 覆盖 62 类主要事件, 一键拉预案'), ok: true },
    ] },
  ],
  note: "事件工单中心是“运维闭环的纽带”：把瞬时告警转化为可追踪、可复盘的工作项，并向上沉淀为问题与风险。",
};

const STATUS_ORDER = TICKET_STATUS_ORDER;
const statusLabel = (s: TicketStatus) => TICKET_STATUS_LABEL[s];
const colColor = (s: TicketStatus) =>
  s === "open" ? "var(--amber)" : s === "doing" ? "var(--cyan)" : s === "pending" ? "var(--purple, #a78bfa)" : "var(--green)";

/* ---- 过滤 ---- */
const kw = ref("");
const fStatus = ref("");
const fLv = ref("");
const view = ref<"kanban" | "table">("kanban");

const filtered = computed(() => {
  const q = kw.value.toLowerCase();
  return tickets.value.filter((t) => {
    if (fStatus.value && t.state !== fStatus.value) return false;
    if (fLv.value && t.lv !== fLv.value) return false;
    if (q && !(`${t.id} ${t.title} ${t.owner} ${t.sys}`.toLowerCase().includes(q))) return false;
    return true;
  });
});

/* ---- 表单弹窗 ---- */
const formOpen = ref(false);
const editing = ref<Ticket | null>(null);
const formInitial = ref<Partial<TicketCreateRequest>>({});

function openCreate() {
  editing.value = null;
  formInitial.value = {};
  formOpen.value = true;
}
function openEdit(t: Ticket) {
  editing.value = t;
  formInitial.value = {
    title: t.title, sys: t.sys, lv: t.lv, owner: t.owner, sla: t.sla, description: t.description,
  };
  formOpen.value = true;
}
function closeForm() {
  formOpen.value = false;
  editing.value = null;
}
function onFormSubmit(data: TicketCreateRequest) {
  if (editing.value) {
    store.update(editing.value.id, data);
    toast.success(tl("已更新工单"));
  } else {
    store.create(data);
    toast.success(tl("已新建工单"));
  }
  closeForm();
}

/* ---- 详情 / 生命周期 ---- */
const detail = ref<Ticket | null>(null);
function openDetail(t: Ticket) {
  detail.value = store.getById(t.id) ?? t;
}
function advance(t: Ticket) {
  store.advance(t.id);
  if (detail.value) detail.value = store.getById(t.id) ?? null;
  const after = store.getById(t.id);
  if (after) toast.info(`${tl("已推进至")} ${statusLabel(after.state)}`);
}
function jumpState(t: Ticket, s: TicketStatus) {
  store.transition(t.id, { state: s, operator: "运维人员" });
  if (detail.value) detail.value = store.getById(t.id) ?? null;
  toast.info(`${tl("已流转至")} ${statusLabel(s)}`);
}

/* ---- 删除 ---- */
const toDelete = ref<Ticket | null>(null);
function askDelete(t: Ticket) { toDelete.value = t; }
function doDelete() {
  if (toDelete.value) {
    store.remove(toDelete.value.id);
    toast.success(tl("已删除工单"));
  }
  toDelete.value = null;
}

/* ---- 日志着色 ---- */
function logColor(a: string) {
  return a === "create" ? "b" : a === "close" ? "g" : a === "transition" ? "a" : "o";
}
function logText(l: { action: string; from?: TicketStatus; to?: TicketStatus }) {
  if (l.action === "create") return "创建工单";
  if (l.action === "close") return "关单闭环";
  if (l.action === "update") return "更新字段";
  if (l.action === "transition" && l.from && l.to) return `${statusLabel(l.from)} → ${statusLabel(l.to)}`;
  return l.action;
}
</script>

<style scoped>
.hdr-btn {
  margin-left: auto; padding: 6px 14px; border-radius: 7px; cursor: pointer;
  background: linear-gradient(135deg, #1a73e8, #22e3ff); color: #fff; border: none; font-size: 12px; font-weight: 600;
}
.kpi-card { min-height: 65px; }
.toolbar { display: flex; align-items: center; gap: 8px; padding: 10px 12px; margin-bottom: 12px; }
.flex1 { flex: 1; }
.ipt {
  background: var(--bg2); border: 1px solid var(--line); border-radius: 7px; color: var(--txt);
  padding: 6px 10px; font-size: 12px; outline: none;
}
.ipt:focus { border-color: var(--cyan); }
.seg { display: flex; border: 1px solid var(--line); border-radius: 7px; overflow: hidden; }
.seg button { background: var(--bg2); border: none; color: var(--txt2); padding: 6px 14px; font-size: 12px; cursor: pointer; }
.seg button.on { background: rgba(34,227,255,.14); color: var(--cyan); font-weight: 600; }
.seg.full { width: 100%; }
.seg.full button { flex: 1; }

/* 看板 */
.kanban { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.kcol { background: var(--bg2); border: 1px solid var(--line); border-radius: 10px; padding: 10px; min-height: 200px; }
.kh { display: flex; align-items: center; justify-content: space-between; font-size: 12.5px; font-weight: 700; margin-bottom: 8px; }
.kcard-i { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 10px; margin-bottom: 8px; cursor: pointer; transition: border-color .15s; }
.kcard-i:hover { border-color: rgba(34,227,255,.35); }
.kcard-i .km { font-size: 10.5px; color: var(--txt3); margin-top: 4px; }
.kbar { margin-top: 6px; }
.kacts { display: flex; gap: 4px; margin-top: 8px; }
.kbtn { font-size: 10.5px; padding: 3px 8px; border-radius: 5px; border: 1px solid var(--line); background: rgba(34,227,255,.1); color: var(--cyan); cursor: pointer; }
.kbtn.ghost { background: var(--bg2); color: var(--txt2); }
.kbtn.danger { background: rgba(255,77,94,.1); color: var(--red, #ff4d5e); border-color: rgba(255,77,94,.25); }
.kempty { text-align: center; font-size: 11px; padding: 12px 0; }

/* 表格操作 */
.act-btn { padding: 2px 8px; border-radius: 4px; border: 1px solid var(--line); font-size: 10px; cursor: pointer; background: rgba(34,227,255,.1); color: var(--cyan); }
.act-btn.ghost { background: var(--bg2); color: var(--txt2); }
.act-btn.danger { background: rgba(255,77,94,.1); color: var(--red, #ff4d5e); border-color: rgba(255,77,94,.25); }

/* 详情 */
.dv-row { display: flex; gap: 10px; font-size: 12.5px; padding: 5px 0; border-bottom: 1px solid rgba(255,255,255,.04); }
.dv-k { color: var(--txt3); width: 88px; flex-shrink: 0; }
.dv-v { color: var(--txt); }
.dv-desc { margin-top: 10px; font-size: 12.5px; color: var(--txt2); }
.dv-desc p { margin: 4px 0 0; white-space: pre-wrap; line-height: 1.5; }
.dv-section { margin: 14px 0 8px; font-size: 12px; font-weight: 700; color: var(--cyan); }
.loglist { display: flex; flex-direction: column; gap: 8px; max-height: 220px; overflow: auto; }
.logitem { display: flex; gap: 8px; align-items: flex-start; }
.ldot { width: 8px; height: 8px; border-radius: 50%; margin-top: 4px; background: var(--txt3); flex-shrink: 0; }
.ldot.g { background: var(--green); } .ldot.a { background: var(--amber); } .ldot.b { background: var(--cyan); } .ldot.o { background: var(--txt3); }
.ltxt { font-size: 12px; color: var(--txt); }
.lmeta { font-size: 10px; color: var(--txt3); margin-top: 2px; }
</style>
