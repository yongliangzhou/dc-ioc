<template>
  <div class="card">
    <div class="card-head">
      <span class="lv" :class="it.alarm.lv">{{ lvText }}</span>
      <div class="title">
        <div class="sys">{{ it.alarm.sys }}</div>
        <div class="desc">{{ it.alarm.desc }}</div>
      </div>
      <div class="time">{{ timeText }}</div>
      <button class="close" @click="$emit('close')">×</button>
    </div>

    <div class="scn">
      <div class="scn-tabs">
        <button :class="{ on: tab === 'cause' }" @click="tab = 'cause'">根因分析</button>
        <button :class="{ on: tab === 'steps' }" @click="tab = 'steps'">排查步骤</button>
        <button :class="{ on: tab === 'fix' }" @click="tab = 'fix'">修复方案</button>
      </div>

      <div class="scn-body">
        <p v-if="tab === 'cause'" class="cause">{{ it.scenario.rootCause }}</p>
        <ol v-else-if="tab === 'steps'" class="steps">
          <li v-for="(s, i) in it.scenario.steps" :key="i">{{ s }}</li>
        </ol>
        <p v-else class="fix">{{ it.scenario.fix }}</p>
      </div>

      <div class="scn-foot">
        <button class="kb" @click="gotoKb">
          一键跳转知识库{{ it.scenario.kbQuery ? "：相关文档" : "" }}
        </button>
        <button class="fb" @click="$emit('feedback', it)">处理反馈</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import type { AlarmNotificationItem } from "@/engine/alarmNotifier";

const props = defineProps<{ it: AlarmNotificationItem }>();
defineEmits<{
  (e: "close"): void;
  (e: "feedback", it: AlarmNotificationItem): void;
  (e: "kb", query: string): void;
}>();

const tab = ref<"cause" | "steps" | "fix">("cause");

const lvText = computed(() =>
  props.it.alarm.lv === "crit" ? "严重" : props.it.alarm.lv === "warn" ? "预警" : "提示"
);
const timeText = computed(() => {
  const d = new Date(props.it.ts);
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
});

function gotoKb() {
  emit("kb", props.it.scenario.kbQuery);
}
</script>

<style scoped>
.card {
  background: linear-gradient(180deg, var(--panel), var(--bg2));
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: 0 18px 50px rgba(0,0,0,.5);
  overflow: hidden;
}
.card-head { display: flex; align-items: flex-start; gap: 10px; padding: 12px 14px; border-bottom: 1px solid var(--line); }
.lv { flex: none; padding: 3px 9px; border-radius: 6px; font-size: 11px; font-weight: 800; }
.lv.crit { background: rgba(242,63,63,.18); color: var(--red); border: 1px solid rgba(242,63,63,.5); }
.lv.warn { background: rgba(255,176,32,.16); color: var(--amber); border: 1px solid rgba(255,176,32,.5); }
.lv.info { background: rgba(34,211,238,.14); color: var(--cyan); border: 1px solid rgba(34,211,238,.5); }
.title { flex: 1; min-width: 0; }
.sys { font-size: 13px; font-weight: 700; color: var(--txt); }
.desc { font-size: 12px; color: var(--txt3); margin-top: 2px; line-height: 1.4; }
.time { flex: none; font-size: 11px; color: var(--txt3); font-variant-numeric: tabular-nums; }
.close { flex: none; background: none; border: none; color: var(--txt3); font-size: 18px; cursor: pointer; line-height: 1; }

.scn { padding: 12px 14px; }
.scn-tabs { display: flex; gap: 6px; margin-bottom: 10px; }
.scn-tabs button {
  padding: 5px 11px; border-radius: 7px; cursor: pointer; font-size: 12px;
  border: 1px solid var(--line); background: var(--bg2); color: var(--txt2);
}
.scn-tabs button.on { background: rgba(34,211,238,.14); color: var(--cyan); border-color: rgba(34,211,238,.5); }
.scn-body { font-size: 12px; line-height: 1.6; color: var(--txt2); min-height: 64px; }
.cause { color: var(--amber); }
.fix { color: var(--green); }
.steps { margin: 0; padding-left: 18px; }
.steps li { margin-bottom: 4px; }
.scn-foot { display: flex; gap: 10px; margin-top: 12px; }
.kb, .fb {
  flex: 1; padding: 7px 0; border-radius: 8px; cursor: pointer; font-size: 12px; font-weight: 600;
  border: 1px solid var(--line); background: var(--bg2); color: var(--txt2);
}
.kb { background: linear-gradient(90deg, var(--cyan), var(--blue)); color: #04121f; border-color: transparent; }
.fb:hover { color: var(--cyan); border-color: rgba(34,211,238,.5); }
</style>
