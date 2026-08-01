<template>
  <teleport to="body">
    <div class="modal-mask" v-if="open" @click.self="$emit('close')">
      <div class="modal" style="width:min(760px,96vw)">
        <div class="modal-head">
          <div>
            <div class="modal-title">{{ mode === "edit" ? `编辑设备 · ${editForm.device_id}` : "添加设备 · 基于物模型" }}</div>
            <div class="muted" style="font-size:11px;margin-top:3px">
              {{ mode === "edit" ? `修改设备信息 · PUT /api/external/devices/${editForm.device_id}` : "经契约端点 POST /api/external/device/register 注册 (先注册, 采集器方可上报)" }}
            </div>
          </div>
          <button class="btn-sm" @click="$emit('close')">{{ tl('关闭') }} ✕</button>
        </div>

        <div class="modal-body">
          <!-- 模式切换 (仅添加) -->
          <div class="tabs" v-if="mode === 'add'">
            <button :class="['tab', addMode === 'single' && 'on']" @click="addMode = 'single'">{{ tl('单个添加') }}</button>
            <button :class="['tab', addMode === 'batch' && 'on']" @click="addMode = 'batch'">{{ tl('批量添加') }}</button>
          </div>

          <!-- 物模型选择 (添加) -->
          <div class="form-row" v-if="mode === 'add'">
            <label>{{ tl('物模型') }}</label>
            <select v-model="form.modelKey" class="ipt" @change="applyModel">
              <option value="">{{ tl('自定义') }} ({{ tl('手动填写全部字段') }})</option>
              <option v-for="m in THING_MODELS" :key="m.key" :value="m.key">
                {{ m.name }}{{ tl('（') }}{{ m.category }} / {{ m.protocol }}{{ tl('）') }}
              </option>
            </select>
            <span class="muted" v-if="currentModel">
              {{ tl('测点模板') }}: {{ currentModel.metrics.map((x) => x.name).join("、") }}
            </span>
          </div>

          <!-- 单个添加 -->
          <template v-if="mode === 'add' && addMode === 'single'">
            <div class="grid2">
              <div class="form-row"><label>{{ tl('设备') }} ID *</label><input v-model.trim="form.device_id" class="ipt" :placeholder="tl('如 CHILLER-01')" /><span class="hint">{{ tl('字母') }}/{{ tl('数字开头') }}，2-64{{ tl('字符') }}，{{ tl('允许') }} ._:- </span></div>
              <div class="form-row"><label>{{ tl('名称') }}</label><input v-model.trim="form.name" class="ipt" :placeholder="tl('展示名称')" /><span class="hint">{{ tl('最长') }} 128 {{ tl('字符') }}</span></div>
              <div class="form-row"><label>IP *</label><input v-model.trim="form.ip" class="ipt" placeholder="10.20.1.11 或主机名" /><span class="hint">{{ tl('合法') }} IPv4/IPv6 {{ tl('地址或主机名') }}</span></div>
              <div class="form-row"><label>{{ tl('序列号') }} SN *</label><input v-model.trim="form.sn" class="ipt" placeholder="SN..." /><span class="hint">{{ tl('最长') }} 128 {{ tl('字符') }}</span></div>
              <div class="form-row"><label>{{ tl('型号') }} *</label><input v-model.trim="form.model" class="ipt" /><span class="hint">{{ tl('最长') }} 128 {{ tl('字符') }}</span></div>
              <div class="form-row"><label>{{ tl('厂商') }}</label><input v-model.trim="form.vendor" class="ipt" /><span class="hint">{{ tl('最长') }} 64 {{ tl('字符') }}</span></div>
              <div class="form-row"><label>{{ tl('业务域') }}</label><input v-model.trim="form.domain" class="ipt" placeholder="hvac_source" /></div>
              <div class="form-row"><label>{{ tl('类别') }}</label><input v-model.trim="form.category" class="ipt" placeholder="chiller" /></div>
              <div class="form-row"><label>{{ tl('位置') }}</label><input v-model.trim="form.location" class="ipt" placeholder="R01" /></div>
              <div class="form-row"><label>{{ tl('协议') }}</label><input v-model.trim="form.protocol" class="ipt" placeholder="modbus/snmp" /></div>
            </div>
            <div class="form-row"><label>{{ tl('标签') }} ({{ tl('逗号分隔') }})</label><input v-model.trim="form.tags" class="ipt" placeholder="cooling,hvac" /></div>
          </template>

          <!-- 批量添加 -->
          <template v-else-if="mode === 'add' && addMode === 'batch'">
            <div class="grid2">
              <div class="form-row"><label>ID 前缀 *</label><input v-model.trim="batch.prefix" class="ipt" placeholder="MOCK-CHILLER-" /></div>
              <div class="form-row"><label>起始序号</label><input v-model.number="batch.start" class="ipt" type="number" min="1" /></div>
              <div class="form-row"><label>数量 *</label><input v-model.number="batch.count" class="ipt" type="number" min="1" max="200" /></div>
              <div class="form-row"><label>IP 网段前缀 *</label><input v-model.trim="batch.ipPrefix" class="ipt" placeholder="10.30.0." /></div>
              <div class="form-row"><label>IP 起始</label><input v-model.number="batch.ipStart" class="ipt" type="number" min="1" /></div>
              <div class="form-row"><label>型号</label><input v-model.trim="form.model" class="ipt" /></div>
              <div class="form-row"><label>厂商</label><input v-model.trim="form.vendor" class="ipt" /></div>
              <div class="form-row"><label>业务域</label><input v-model.trim="form.domain" class="ipt" placeholder="hvac_source" /></div>
              <div class="form-row"><label>类别</label><input v-model.trim="form.category" class="ipt" placeholder="chiller" /></div>
              <div class="form-row"><label>位置 (留空按 R01~R03 轮转)</label><input v-model.trim="form.location" class="ipt" placeholder="R01" /></div>
              <div class="form-row"><label>协议</label><input v-model.trim="form.protocol" class="ipt" placeholder="modbus/snmp" /></div>
            </div>
            <div class="form-row"><label>标签 (逗号分隔)</label><input v-model.trim="form.tags" class="ipt" placeholder="cooling,hvac" /></div>

            <div v-if="batchPreview.length" class="preview">
              <div class="muted" style="margin:10px 0 6px">将生成 {{ batchPreview.length }} 台 (预览前 50 台)：</div>
              <table>
                <thead><tr><th>设备 ID</th><th>IP</th><th>SN</th></tr></thead>
                <tbody>
                  <tr v-for="(d, i) in batchPreview.slice(0, 50)" :key="i">
                    <td class="mono">{{ d.device_id }}</td><td class="mono">{{ d.ip }}</td><td class="mono">{{ d.sn }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </template>

          <!-- 编辑 -->
          <template v-else-if="mode === 'edit'">
            <div class="grid2">
              <div class="form-row"><label>设备 ID</label><input disabled :value="editForm.device_id" class="ipt" /></div>
              <div class="form-row"><label>名称</label><input v-model.trim="editForm.name" class="ipt" /></div>
              <div class="form-row"><label>IP *</label><input v-model.trim="editForm.ip" class="ipt" /></div>
              <div class="form-row"><label>序列号 SN *</label><input v-model.trim="editForm.sn" class="ipt" /></div>
              <div class="form-row"><label>型号 *</label><input v-model.trim="editForm.model" class="ipt" /></div>
              <div class="form-row"><label>厂商</label><input v-model.trim="editForm.vendor" class="ipt" /></div>
              <div class="form-row"><label>业务域</label><input v-model.trim="editForm.domain" class="ipt" /></div>
              <div class="form-row"><label>类别</label><input v-model.trim="editForm.category" class="ipt" /></div>
              <div class="form-row"><label>位置</label><input v-model.trim="editForm.location" class="ipt" /></div>
              <div class="form-row"><label>协议</label><input v-model.trim="editForm.protocol" class="ipt" /></div>
            </div>
            <div class="form-row"><label>标签 (逗号分隔)</label><input v-model.trim="editForm.tags" class="ipt" /></div>
            <div v-if="editThingModel" class="thing-model-info">
              <div class="section-title" style="margin-top:14px">传感器 / 测点模板 ({{ editThingModel.category_label }})</div>
              <table><thead><tr><th>测点名称</th><th>语义</th><th>单位</th></tr></thead>
                <tbody><tr v-for="m in editThingModel.metrics" :key="m.metric_name"><td class="mono">{{ m.metric_name }}</td><td>{{ m.description }}</td><td>{{ m.unit || '—' }}</td></tr></tbody>
              </table>
              <span class="muted" style="font-size:10px">以上为 {{ editThingModel.category }} 类别的标准测点模板，实际上报的测点由采集器决定</span>
            </div>
          </template>

          <div v-if="error" class="result warn">{{ error }}</div>
          <div v-else-if="result" class="result" :class="result.fail > 0 ? 'warn' : 'ok'">
            注册完成 — 成功 {{ result.ok }} · 重复 {{ result.dup }} · 失败 {{ result.fail }}
          </div>
          <div v-else-if="okMsg" class="result ok" style="margin-top:12px">{{ okMsg }}</div>
        </div>

        <div class="modal-foot">
          <span class="muted" style="font-size:11px">
            {{ mode === "edit" ? "传感器模板来源于物模型" : "批量注册将按物模型并发调用契约端点" }}
          </span>
          <div class="flex gap8">
            <button class="btn-sm" @click="$emit('close')">取消</button>
            <button class="btn-sm primary" :disabled="submitting" @click="onSubmit">
              {{ submitting ? "提交中…" : mode === "edit" ? "保存修改" : "提交注册" }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">import { useI18n } from "vue-i18n";
const { t: tl } = useI18n();
import { computed, reactive, ref, watch } from "vue";
import { THING_MODELS } from "@/constants/thingModels";
import type { ExternalDevice, ExternalDeviceView, ThingModelDef } from "@/types";

const props = defineProps<{
  open: boolean;
  mode: "add" | "edit";
  device?: ExternalDeviceView | null;
  submitting?: boolean;
  result?: { ok: number; dup: number; fail: number } | null;
  error?: string;
  okMsg?: string;
}>();

const emit = defineEmits<{
  (e: "close"): void;
  (e: "submit-single", payload: ExternalDevice): void;
  (e: "submit-batch", payloads: ExternalDevice[]): void;
  (e: "submit-edit", deviceId: string, payload: Record<string, any>): void;
}>();

const addMode = ref<"single" | "batch">("single");
const form = reactive({
  modelKey: "", device_id: "", name: "", ip: "", sn: "", model: "", vendor: "",
  domain: "", category: "", location: "", protocol: "", tags: "",
});
const batch = reactive({ prefix: "MOCK-CHILLER-", start: 1, count: 5, ipPrefix: "10.30.0.", ipStart: 1 });
const editForm = reactive({
  device_id: "", name: "", ip: "", sn: "", model: "", vendor: "", domain: "", category: "", location: "", protocol: "", tags: "",
});

const currentModel = computed(() => THING_MODELS.find((m) => m.key === form.modelKey) || null);
const editThingModel = computed<ThingModelDef | null>(() => {
  if (props.mode !== "edit" || !editForm.category) return null;
  const m = THING_MODELS.find((t) => t.category === editForm.category);
  return m ? { ...m, category_label: m.category } as unknown as ThingModelDef : null;
});

const batchPreview = computed(() => {
  if (props.mode !== "add" || addMode.value !== "batch") return [];
  const n = Math.max(1, Math.min(200, Number(batch.count) || 0));
  const start = Math.max(1, Number(batch.start) || 1);
  const ipStart = Math.max(1, Number(batch.ipStart) || 1);
  const pad = String(start + n - 1).length;
  const out: { device_id: string; ip: string; sn: string }[] = [];
  for (let i = 0; i < n; i++) {
    const seq = start + i;
    out.push({
      device_id: `${batch.prefix}${String(seq).padStart(pad, "0")}`,
      ip: `${batch.ipPrefix}${ipStart + i}`,
      sn: `${form.model || "DEV"}-${String(seq).padStart(4, "0")}`,
    });
  }
  return out;
});

function applyModel() {
  const m = currentModel.value;
  if (m) {
    form.model = m.model; form.vendor = m.vendor; form.domain = m.domain;
    form.category = m.category; form.protocol = m.protocol; form.tags = m.tags.join(",");
    if (addMode.value === "batch") {
      if (!batch.prefix) batch.prefix = `MOCK-${m.category.toUpperCase()}-`;
      if (!batch.ipPrefix) batch.ipPrefix = "10.30.0.";
    }
  }
}

function parseTags(): string[] | undefined {
  const tags = form.tags.split(",").map((t) => t.trim()).filter(Boolean);
  return tags.length ? tags : undefined;
}

function resetForms() {
  addMode.value = "single";
  form.modelKey = "chiller"; form.device_id = ""; form.name = ""; form.ip = ""; form.sn = "";
  form.model = ""; form.vendor = ""; form.domain = ""; form.category = ""; form.location = ""; form.protocol = ""; form.tags = "";
  batch.prefix = "MOCK-CHILLER-"; batch.start = 1; batch.count = 5; batch.ipPrefix = "10.30.0."; batch.ipStart = 1;
  applyModel();
  if (props.device) {
    editForm.device_id = props.device.device_id;
    editForm.name = props.device.name || "";
    editForm.ip = props.device.ip; editForm.sn = props.device.sn; editForm.model = props.device.model;
    editForm.vendor = props.device.vendor || ""; editForm.domain = props.device.domain || "";
    editForm.category = props.device.category || ""; editForm.location = props.device.location || "";
    editForm.protocol = props.device.protocol || ""; editForm.tags = (props.device.tags || []).join(",");
  }
}

watch(() => [props.open, props.mode, props.device], () => { if (props.open) resetForms(); }, { immediate: true });

function onSubmit() {
  if (props.mode === "edit") {
    if (!editForm.ip || !editForm.sn || !editForm.model) {
      emit("close");
      return;
    }
    const tags = editForm.tags.split(",").map((t) => t.trim()).filter(Boolean);
    emit("submit-edit", editForm.device_id, {
      ip: editForm.ip || undefined, sn: editForm.sn || undefined, model: editForm.model || undefined,
      name: editForm.name || undefined, vendor: editForm.vendor || undefined, domain: editForm.domain || undefined,
      category: editForm.category || undefined, location: editForm.location || undefined, protocol: editForm.protocol || undefined,
      tags: tags.length ? tags : undefined,
    });
    return;
  }
  if (addMode.value === "single") {
    if (!form.device_id || !form.ip || !form.sn || !form.model) return;
    emit("submit-single", {
      device_id: form.device_id, ip: form.ip, sn: form.sn, model: form.model,
      name: form.name || undefined, vendor: form.vendor || undefined, domain: form.domain || undefined,
      category: form.category || undefined, location: form.location || undefined, protocol: form.protocol || undefined,
      tags: parseTags(),
    });
  } else {
    if (!batch.prefix || !batch.ipPrefix || !(Number(batch.count) > 0)) return;
    const payloads: ExternalDevice[] = batchPreview.value.map((p, i) => {
      const seq = Number(batch.start) + i;
      return {
        device_id: p.device_id, ip: p.ip, sn: p.sn, model: form.model,
        name: `${currentModel.value?.name ?? form.model}-${seq}`,
        vendor: form.vendor || undefined, domain: form.domain || undefined,
        category: form.category || undefined, location: form.location || `R${(i % 3) + 1}`,
        protocol: form.protocol || undefined, tags: parseTags(),
      };
    });
    emit("submit-batch", payloads);
  }
}
</script>

<style scoped>
.modal-mask { position: fixed; inset: 0; background: rgba(6, 11, 20, .6); backdrop-filter: blur(2px); display: flex; align-items: center; justify-content: center; padding: 6vh 16px; z-index: 1000; animation: modalFade .15s ease; }
.modal { width: min(760px, 96vw); max-height: 86vh; display: flex; flex-direction: column; background: linear-gradient(180deg, var(--panel), var(--bg2)); border: 1px solid var(--line); border-radius: 14px; box-shadow: 0 20px 60px rgba(0, 0, 0, .5); overflow: hidden; }
.modal-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; padding: 14px 16px; border-bottom: 1px solid var(--line); }
.modal-title { font-size: 15px; font-weight: 700; }
.modal-body { padding: 6px 16px 14px; overflow: auto; }
.modal-foot { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-top: 1px solid var(--line); }
@keyframes modalFade { from { opacity: 0; } to { opacity: 1; } }
.btn-sm.primary { background: linear-gradient(90deg, var(--cyan), var(--blue)); color: #04121f; border-color: transparent; font-weight: 700; }
.btn-sm.primary:disabled { opacity: .6; cursor: default; }
.tabs { display: flex; gap: 8px; margin-bottom: 14px; }
.tab { background: var(--bg2); border: 1px solid var(--line); color: var(--txt2); padding: 6px 14px; border-radius: 8px; cursor: pointer; font-size: 12px; }
.tab.on { color: var(--txt); border-color: var(--cyan); background: rgba(34, 227, 255, .08); }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; }
.form-row { display: flex; flex-direction: column; gap: 4px; margin-top: 10px; }
.form-row label { font-size: 11px; color: var(--txt2); }
.form-row .muted { font-size: 11px; }
.form-row .hint { font-size: 10px; color: var(--txt2); opacity: 0.7; }
select.ipt { appearance: none; cursor: pointer; }
.preview { max-height: 220px; overflow: auto; border: 1px solid var(--line); border-radius: 8px; padding: 2px 6px; margin-top: 4px; }
.result { margin-top: 12px; padding: 8px 12px; border-radius: 8px; font-size: 12px; }
.result.ok { background: rgba(43, 212, 122, .1); color: var(--green); border: 1px solid rgba(43, 212, 122, .3); }
.result.warn { background: rgba(255, 176, 32, .1); color: var(--amber); border: 1px solid rgba(255, 176, 32, .3); }
.thing-model-info { margin-top: 8px; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; }
.thing-model-info table { width: 100%; }
.thing-model-info th { font-size: 11px; color: var(--txt2); padding: 4px 6px; }
.thing-model-info td { font-size: 12px; padding: 3px 6px; }
</style>
