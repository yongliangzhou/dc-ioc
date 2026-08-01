<template>
  <div class="card scroll-x">
    <table>
      <thead><tr><th style="width:70px">{{ tl('级别') }}</th><th style="width:70px">{{ tl('系统') }}</th><th>{{ tl('告警内容') }}</th><th style="width:120px">{{ tl('触发时间') }}</th><th style="width:70px">{{ tl('状态') }}</th><th style="width:80px">{{ tl('责任人') }}</th><th style="width:120px">{{ tl('操作') }}</th></tr></thead>
      <tbody>
        <tr v-for="(x, i) in alarms" :key="i" :class="{ 'row-crit': x.lv === 'crit', 'row-warn': x.lv === 'warn' }">
          <td><span class="tag" :class="lvClass(x.lv)">{{ lvText(x.lv) }}</span></td>
          <td><span class="sys-badge">{{ x.sys }}</span></td>
          <td class="desc-cell">{{ x.desc }}</td>
          <td class="mono" style="font-size:11px">{{ x.ts }}</td>
          <td><span class="tag" :class="tagClass(x.state)">{{ x.state }}</span></td>
          <td>{{ x.owner ?? '—' }}</td>
          <td>
            <div class="flex gap4">
              <button class="act-btn runbook" @click="$emit('runbook', x)">{{ tl('预案') }}</button>
              <button v-if="x.state === '待确认'" class="act-btn ack" @click="$emit('ack', x)">{{ tl('确认') }}</button>
              <button v-if="x.state !== '已关闭'" class="act-btn ticket" @click="$emit('ticket', x)">{{ tl('转工单') }}</button>
              <button v-if="x.state !== '已关闭'" class="act-btn resolve" @click="$emit('resolve', x)">{{ tl('关单') }}</button>
              <button v-if="x.state === '已关闭'" class="act-btn done" disabled>{{ tl('已处理') }}</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <div class="muted" style="text-align:center;padding:20px" v-if="!alarms.length">{{ tl('当前无活动告警') }}</div>
  </div>
</template>

<script setup lang="ts">import { useI18n } from "vue-i18n";
const { t: tl } = useI18n();
import type { Alarm } from "@/types";import { lvClass, lvText, tagClass } from "@/utils/state";

defineProps<{ alarms: Alarm[] }>();
defineEmits<{
  (e: "ack", x: Alarm): void;
  (e: "resolve", x: Alarm): void;
  (e: "runbook", x: Alarm): void;
  (e: "ticket", x: Alarm): void;
}>();
</script>

<style scoped>
.sys-badge { font-size: 10.5px; color: var(--cyan); font-weight: 600; }
.row-crit { background: linear-gradient(90deg, rgba(255,77,94,.06), transparent); }
.row-warn { background: linear-gradient(90deg, rgba(255,176,32,.04), transparent); }
.desc-cell { max-width: 280px; }
.act-btn {
  padding: 2px 8px; border-radius: 4px; border: 1px solid var(--line);
  font-size: 10px; cursor: pointer; background: var(--bg2); color: var(--txt2);
  transition: all .15s;
}
.act-btn.ack { border-color: var(--cyan); color: var(--cyan); }
.act-btn.ack:hover { background: rgba(34,227,255,.1); }
.act-btn.ticket { border-color: var(--purple, #a78bfa); color: var(--purple, #a78bfa); }
.act-btn.ticket:hover { background: rgba(167,139,250,.12); }
.act-btn.runbook { border-color: var(--green, #2bd47a); color: var(--green, #2bd47a); }
.act-btn.runbook:hover { background: rgba(43,212,122,.1); }
.act-btn.resolve { border-color: var(--green); color: var(--green); }
.act-btn.resolve:hover { background: rgba(43,212,122,.1); }
.act-btn.done { border-color: rgba(255,255,255,.1); color: var(--txt3); cursor: default; }
</style>
