<template>
  <div class="ar-page">
    <div class="ar-head">
      <div class="ar-title">{{ tl("告警规则引擎") }}</div>
      <div class="ar-engine">
        {{ tl("引擎状态") }}: {{ tl("已启用") }} <b>{{ engine.enabled }}</b> / {{ tl("共") }} <b>{{ engine.total }}</b> {{ tl("条") }}
        <button class="btn-sm" @click="loadAll">{{ tl("刷新") }}</button>
      </div>
      <button class="btn-sm primary" v-bind="authState('write')" @click="openCreate">{{ tl("新建规则") }}</button>
    </div>

    <div class="ar-table">
      <table>
        <thead>
          <tr>
            <th>{{ tl("类别") }}</th>
            <th>{{ tl("测点") }}</th>
            <th>{{ tl("规则编码") }}</th>
            <th>{{ tl("预警区间") }}</th>
            <th>{{ tl("严重区间") }}</th>
            <th>{{ tl("单位") }}</th>
            <th>{{ tl("状态") }}</th>
            <th>{{ tl("操作") }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in rules" :key="r.id">
            <td>{{ r.category }}</td>
            <td class="mono">{{ r.metric }}</td>
            <td class="mono small">{{ r.ruleCode || "—" }}</td>
            <td class="mono">{{ band(r.warnLo, r.warnHi) }}</td>
            <td class="mono">{{ band(r.critLo, r.critHi) }}</td>
            <td>{{ r.unit || "—" }}</td>
            <td>
              <button class="pill" :class="r.enabled ? 'g' : 'a'" v-bind="authState('write')" :disabled="busy['t'+r.id]" @click="toggle(r)">
                {{ r.enabled ? tl("已启用") : tl("已禁用") }}
              </button>
            </td>
            <td class="ops">
              <button class="link" v-bind="authState('write')" @click="openEdit(r)">{{ tl("编辑") }}</button>
              <button class="link" v-bind="authState('write')" :disabled="busy['s'+r.id]" @click="silence(r)">{{ tl("静默30m") }}</button>
              <button class="link danger" v-bind="authState('write')" @click="remove(r)">{{ tl("删除") }}</button>
            </td>
          </tr>
          <tr v-if="!rules.length">
            <td colspan="8" class="empty">{{ tl("暂无可用的告警规则") }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="editing" class="drawer-mask" @click.self="editing = false">
      <div class="drawer">
        <div class="drawer-head">
          <span>{{ form.id ? tl("编辑规则") : tl("新建规则") }}</span>
          <button class="x" @click="editing = false">✕</button>
        </div>
        <div class="form">
          <label>
            {{ tl("类别") }}
            <div class="hint">{{ tl("如 power / hvac / security") }}</div>
            <input v-model.trim="form.category" class="ipt" :placeholder="tl('category')" />
          </label>
          <label>
            {{ tl("测点名") }}
            <input v-model.trim="form.metric" class="ipt" :placeholder="tl('metric')" />
          </label>
          <div class="row">
            <label>{{ tl("预警下限") }}<input v-model.number="form.warnLo" class="ipt" type="number" /></label>
            <label>{{ tl("预警上限") }}<input v-model.number="form.warnHi" class="ipt" type="number" /></label>
          </div>
          <div class="row">
            <label>{{ tl("严重下限") }}<input v-model.number="form.critLo" class="ipt" type="number" /></label>
            <label>{{ tl("严重上限") }}<input v-model.number="form.critHi" class="ipt" type="number" /></label>
          </div>
          <label>
            {{ tl("单位") }}
            <input v-model.trim="form.unit" class="ipt" :placeholder="'℃ / % / kPa'" />
          </label>
          <label class="chk"><input type="checkbox" v-model="form.enabled" /> {{ tl("启用该规则") }}</label>
          <div v-if="err" class="err">{{ err }}</div>
          <div class="drawer-foot">
            <button class="btn-sm" @click="editing = false">{{ tl("取消") }}</button>
            <button class="btn-sm primary" :disabled="saving" @click="save">
              {{ saving ? tl("保存中…") : tl("保存") }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import type { AlarmRuleDef, AlarmRuleStatus } from "@/types";
import {
  getAlarmRules,
  createAlarmRule,
  updateAlarmRule,
  deleteAlarmRule,
  toggleAlarmRule,
  silenceAlarmRule,
} from "@/api";
import { useToast } from "@/hooks/useToast";
import { useConfirm } from "@/hooks/useConfirm";
import { usePermission, type PermAction } from "@/hooks/usePermission";

const { t: tl } = useI18n();
const toast = useToast();
const { can, denyTip } = usePermission();

function authState(action: PermAction) {
  const ok = can(action);
  return { disabled: !ok, title: ok ? "" : denyTip(action) };
}

const rules = ref<AlarmRuleDef[]>([]);
const editing = ref(false);
const saving = ref(false);
const err = ref("");
// 行内动作 loading 防护（防止重复点击）
const busy = ref<Record<string, boolean>>({});

// 引擎态由规则列表本地计算 (后端无 /state 端点)
const engine = computed(() => ({
  total: rules.value.length,
  enabled: rules.value.filter((r) => r.enabled).length,
}));

function blank(): Partial<AlarmRuleDef> {
  return {
    category: "",
    metric: "",
    warnLo: null,
    warnHi: null,
    critLo: null,
    critHi: null,
    unit: "",
    enabled: true,
  };
}
const form = ref<Partial<AlarmRuleDef>>(blank());

function band(lo: number | null | undefined, hi: number | null | undefined): string {
  if (lo == null && hi == null) return "—";
  const f = (v: typeof lo) => (v == null ? "∞" : String(v));
  return `${f(lo)} ~ ${f(hi)}`;
}

async function loadAll() {
  const list = await getAlarmRules();
  rules.value = Array.isArray(list) ? list : [];
}

function openCreate() {
  form.value = blank();
  err.value = "";
  editing.value = true;
}
function openEdit(r: AlarmRuleDef) {
  form.value = { ...r };
  err.value = "";
  editing.value = true;
}

async function save() {
  err.value = "";
  const f = form.value;
  if (!f.category || !f.metric) {
    err.value = tl("类别与测点名为必填");
    return;
  }
  saving.value = true;
  try {
    const payload: Partial<AlarmRuleDef> = {
      category: f.category,
      metric: f.metric,
      warnLo: f.warnLo ?? null,
      warnHi: f.warnHi ?? null,
      critLo: f.critLo ?? null,
      critHi: f.critHi ?? null,
      unit: f.unit || undefined,
      enabled: f.enabled ?? true,
    };
    if (f.id != null) await updateAlarmRule(String(f.id), payload);
    else await createAlarmRule(payload);
    editing.value = false;
    await loadAll();
  } catch (e: any) {
    err.value = e?.response?.data?.message || tl("保存失败");
  } finally {
    saving.value = false;
  }
}

async function toggle(r: AlarmRuleDef) {
  if (busy.value["t" + r.id]) return;
  const next: AlarmRuleStatus = r.enabled ? "disabled" : "enabled";
  const prev = r.status;
  const prevEnabled = r.enabled;
  r.enabled = !r.enabled;
  r.status = next;
  busy.value["t" + r.id] = true;
  try {
    await toggleAlarmRule(String(r.id), next);
    toast.success(r.enabled ? tl("已启用规则") : tl("已禁用规则"));
  } catch (e: any) {
    r.enabled = prevEnabled;
    r.status = prev;
    toast.error(e?.detail || e?.response?.data?.detail || e?.response?.data?.message || e?.message || tl("操作失败"));
  } finally {
    busy.value["t" + r.id] = false;
  }
}

async function silence(r: AlarmRuleDef) {
  if (busy.value["s" + r.id]) return;
  busy.value["s" + r.id] = true;
  try {
    await silenceAlarmRule(String(r.id), 30);
    await loadAll();
    toast.success(tl("已静默 30 分钟"));
  } catch (e: any) {
    toast.error(e?.detail || e?.response?.data?.detail || e?.response?.data?.message || e?.message || tl("静默失败"));
  } finally {
    busy.value["s" + r.id] = false;
  }
}

async function remove(r: AlarmRuleDef) {
  const ok = await useConfirm({
    title: tl("删除告警规则"),
    message: `${tl("确认删除规则")} ${r.ruleCode || r.metric}?`,
    detail: tl("删除后该测点将不再触发此规则告警。"),
    danger: true,
    confirmText: tl("删除"),
    onConfirm: async () => { await deleteAlarmRule(String(r.id)); },
  });
  if (ok) {
    rules.value = rules.value.filter((x) => x.id !== r.id);
    toast.success(tl("已删除规则"));
  }
}

onMounted(loadAll);
</script>

<style scoped>
.ar-page { padding: 16px 20px; max-width: 1180px; margin: 0 auto; }
.ar-head { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.ar-title { font-size: 18px; font-weight: 700; }
.ar-engine { font-size: 12px; color: var(--txt3); display: flex; align-items: center; gap: 6px; margin-right: auto; }
.ar-engine b { color: var(--txt); }
.ar-table { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }
.ar-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ar-table th, .ar-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); }
.ar-table th { background: var(--bg2); color: var(--txt2); font-weight: 600; }
.ar-table tr:last-child td { border-bottom: none; }
.mono { font-family: ui-monospace, Menlo, Consolas, monospace; }
.small { font-size: 11px; color: var(--txt3); }
.empty { text-align: center; color: var(--txt3); padding: 28px; }
.pill { padding: 3px 10px; border-radius: 6px; border: 1px solid var(--line); font-size: 11px; cursor: pointer; background: var(--bg2); color: var(--txt2); }
.pill.g { background: rgba(43, 212, 122, .12); border-color: var(--green); color: var(--green); }
.pill.a { background: rgba(255, 176, 32, .08); border-color: rgba(255, 176, 32, .3); color: var(--amber); }
.ops { display: flex; gap: 8px; }
.link { background: none; border: none; color: var(--cyan); cursor: pointer; font-size: 12px; padding: 0; }
.link.danger { color: var(--red); }
.btn-sm { padding: 5px 12px; border-radius: 7px; border: 1px solid var(--line); background: var(--bg2); color: var(--txt2); cursor: pointer; font-size: 12px; }
.btn-sm.primary { background: var(--cyan); color: #04121a; border-color: var(--cyan); font-weight: 600; }
.btn-sm:disabled { opacity: .6; cursor: default; }

.drawer-mask { position: fixed; inset: 0; background: rgba(0, 0, 0, .45); display: flex; justify-content: flex-end; z-index: 40; }
.drawer { width: 420px; max-width: 92vw; background: var(--panel); height: 100%; padding: 18px; overflow: auto; box-shadow: -8px 0 24px rgba(0, 0, 0, .3); }
.drawer-head { display: flex; justify-content: space-between; align-items: center; font-size: 15px; font-weight: 700; margin-bottom: 14px; }
.x { background: none; border: none; color: var(--txt3); font-size: 16px; cursor: pointer; }
.form { display: flex; flex-direction: column; gap: 12px; }
.form label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--txt2); }
.form .hint { font-size: 10px; color: var(--txt3); }
.row { display: flex; gap: 10px; }
.row label { flex: 1; }
.ipt { background: var(--bg2); border: 1px solid var(--line); border-radius: 7px; padding: 7px 9px; color: var(--txt); font-size: 13px; }
.chk { flex-direction: row; align-items: center; gap: 6px; }
.err { color: var(--red); font-size: 12px; }
.drawer-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }
</style>
