<template>
  <teleport to="body">
    <!-- crit 级全屏遮罩，确保层级最高、不可被其他窗口遮挡 -->
    <div v-if="hasCrit" class="an-mask" @click.self="keepOpen">
      <div class="an-stack">
        <transition-group name="an">
          <div
            v-for="it in critItems"
            :key="it.id"
            class="an-card"
            :class="it.alarm.lv"
          >
            <AlarmCard :it="it" @close="dismiss(it.id)" @feedback="openFeedback(it)" @kb="gotoKb" />
          </div>
        </transition-group>
      </div>
    </div>

    <!-- 非 crit 告警：右上角堆叠浮层（同样最高层级） -->
    <div
      v-if="nonCritItems.length"
      class="an-float"
      :class="{ compressed: collapsed }"
    >
      <div class="an-float-head" @click="collapsed = !collapsed">
        <span class="an-bell">▲</span>
        <span>实时告警 ({{ nonCritItems.length }})</span>
        <button class="an-clear" @click.stop="clear">清空</button>
      </div>
      <transition-group v-show="!collapsed" name="an" tag="div" class="an-float-body">
        <div v-for="it in nonCritItems" :key="it.id" class="an-card" :class="it.alarm.lv">
          <AlarmCard :it="it" @close="dismiss(it.id)" @feedback="openFeedback(it)" @kb="gotoKb" />
        </div>
      </transition-group>
    </div>

    <!-- 处理反馈弹窗 -->
    <div v-if="feedbackItem" class="an-mask" @click.self="feedbackItem = null">
      <div class="an-feedback">
        <div class="an-fb-head">处理反馈 · 沉淀经验</div>
        <div class="an-fb-subj">{{ feedbackItem.alarm.sys }} — {{ feedbackItem.alarm.desc }}</div>
        <div class="an-fb-row">
          <span class="an-fb-label">处理结果</span>
          <div class="an-fb-tags">
            <button
              v-for="opt in resultOptions"
              :key="opt"
              class="an-fb-tag"
              :class="{ on: result === opt }"
              @click="result = opt"
            >{{ opt }}</button>
          </div>
        </div>
        <div class="an-fb-row col">
          <span class="an-fb-label">处理备注 / 经验沉淀</span>
          <textarea
            v-model="note"
            class="an-fb-text"
            rows="4"
            placeholder="记录根因确认、处置动作、后续优化建议…"
          />
        </div>
        <div class="an-fb-foot">
          <button class="an-btn ghost" @click="feedbackItem = null">取消</button>
          <button class="an-btn primary" :disabled="!result" @click="submitFeedback">
            {{ saving ? "提交中…" : "提交并关闭告警" }}
          </button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { useAlarmNotifier, type AlarmNotificationItem } from "@/engine/alarmNotifier";
import { useToast } from "@/hooks/useToast";
import { useAsyncTask } from "@/hooks/useAsyncTask";
import { realtimeLinkage } from "@/engine/realtimeLinkage";
import AlarmCard from "./AlarmCard.vue";

const router = useRouter();
const toast = useToast();
const notifier = useAlarmNotifier();
const { run: submitRun, loading: saving } = useAsyncTask(async () => {});

const items = computed(() => notifier.items);
const hasCrit = computed(() => items.value.some((i) => i.alarm.lv === "crit"));
const critItems = computed(() => items.value.filter((i) => i.alarm.lv === "crit"));
const nonCritItems = computed(() => items.value.filter((i) => i.alarm.lv !== "crit"));

const collapsed = ref(false);
const feedbackItem = ref<AlarmNotificationItem | null>(null);
const result = ref("");
const note = ref("");
const resultOptions = ["已处理修复", "误报", "转工单", "持续观察"];

function dismiss(id: string) {
  notifier.dismiss(id);
}
function clear() {
  notifier.clear();
}
// crit 遮罩点击不关闭（最高优先级，必须人工确认）
function keepOpen() {}

function openFeedback(it: AlarmNotificationItem) {
  feedbackItem.value = it;
  result.value = "";
  note.value = "";
}

async function submitFeedback() {
  if (!feedbackItem.value || !result.value) return;
  const it = feedbackItem.value;
  try {
    // 闭环：确认并关单 + 保留处理记录
    realtimeLinkage.ack(it.alarm.id);
    realtimeLinkage.resolve(it.alarm.id);
    // 本地沉淀（可扩展为后端处理记录接口）
    try {
      localStorage.setItem(
        `alarm_feedback_${it.alarm.id}`,
        JSON.stringify({ result: result.value, note: note.value, ts: Date.now() })
      );
    } catch { /* ignore */ }
    toast.success("已记录处理反馈并关闭告警");
    feedbackItem.value = null;
    notifier.dismiss(it.id);
  } catch (e: any) {
    toast.error(e?.detail || e?.message || "提交失败");
  }
}

function gotoKb(query: string) {
  if (query) router.push({ path: "/ops/knowledge", query: { q: query } });
  else router.push({ path: "/ops/knowledge" });
}

defineExpose({ gotoKb });
</script>

<style scoped>
.an-mask {
  position: fixed;
  inset: 0;
  background: rgba(4, 9, 18, .55);
  backdrop-filter: blur(3px);
  z-index: 9999; /* 全局最高层级，不被任何窗口遮挡 */
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 8vh;
}
.an-stack { display: flex; flex-direction: column; gap: 14px; width: min(560px, 94vw); }
.an-float {
  position: fixed;
  top: 14px; right: 14px;
  z-index: 9999;
  width: min(420px, 92vw);
  display: flex; flex-direction: column; gap: 10px;
}
.an-float.compressed .an-float-body { display: none; }
.an-float-head {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px; cursor: pointer;
  background: linear-gradient(180deg, var(--panel), var(--bg2));
  border: 1px solid var(--line); border-radius: 10px;
  color: var(--txt); font-size: 12px; font-weight: 700;
}
.an-bell { color: var(--amber); }
.an-clear { margin-left: auto; background: none; border: none; color: var(--txt3); cursor: pointer; font-size: 11px; }
.an-float-body { display: flex; flex-direction: column; gap: 10px; }

.an-feedback {
  width: min(480px, 94vw);
  background: linear-gradient(180deg, var(--panel), var(--bg2));
  border: 1px solid var(--line); border-radius: 14px;
  box-shadow: 0 24px 70px rgba(0,0,0,.55);
  padding: 16px;
}
.an-fb-head { font-size: 15px; font-weight: 700; color: var(--txt); }
.an-fb-subj { font-size: 12px; color: var(--txt3); margin: 4px 0 12px; }
.an-fb-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.an-fb-row.col { flex-direction: column; align-items: stretch; }
.an-fb-label { font-size: 12px; color: var(--txt2); flex: none; width: 72px; }
.an-fb-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.an-fb-tag {
  padding: 5px 12px; border-radius: 7px; cursor: pointer;
  border: 1px solid var(--line); background: var(--bg2); color: var(--txt2); font-size: 12px;
}
.an-fb-tag.on { background: linear-gradient(90deg, var(--cyan), var(--blue)); color: #04121f; border-color: transparent; font-weight: 700; }
.an-fb-text {
  width: 100%; resize: vertical; border-radius: 8px;
  border: 1px solid var(--line); background: var(--bg2); color: var(--txt);
  padding: 8px 10px; font-size: 12px; line-height: 1.5;
}
.an-fb-foot { display: flex; justify-content: flex-end; gap: 10px; margin-top: 6px; }
.an-btn { padding: 7px 16px; border-radius: 8px; cursor: pointer; font-size: 12px; border: 1px solid var(--line); background: var(--bg2); color: var(--txt2); }
.an-btn.primary { background: linear-gradient(90deg, var(--cyan), var(--blue)); color: #04121f; border-color: transparent; font-weight: 700; }
.an-btn:disabled { opacity: .6; cursor: default; }

.an-enter-active, .an-leave-active { transition: all .25s ease; }
.an-enter-from { opacity: 0; transform: translateY(-10px) scale(.98); }
.an-leave-to { opacity: 0; transform: translateX(20px); }
</style>
