<template>
  <header class="topbar">
    <div class="logo">
      DC·IOC 智能运营中心<small>DATA CENTER INTELLIGENT OPERATIONS CENTER</small>
    </div>
    <div class="global-kpis">
      <div class="gkpi">
        <div class="v" style="color: var(--cyan)">{{ ov?.pue?.toFixed(3) ?? '-' }}</div>
        <div class="l">PUE 实时</div>
      </div>
      <div class="gkpi">
        <div class="v">{{ ov?.it_load_mw ?? '-' }}<small> MW</small></div>
        <div class="l">IT 负载</div>
      </div>
      <div class="gkpi">
        <div class="v" style="color: var(--green)">
          {{ ov?.online_rate ?? '-' }}<small>%</small>
        </div>
        <div class="l">设备在线率</div>
      </div>
      <div class="gkpi">
        <div class="v" :style="{ color: ov?.today_alarms ? 'var(--amber)' : 'var(--green)' }">
          {{ ov?.today_alarms ?? '-' }}
        </div>
        <div class="l">今日告警</div>
      </div>
      <div class="gkpi">
        <div class="v">15.2<small> ℃</small></div>
        <div class="l">冷冻水供水</div>
      </div>
    </div>
    <div class="tools">
      <LanguageSwitcher />
      <button
        class="tbtn"
        :title="themeMode === 'dark' ? '切换浅色模式' : '切换深色模式'"
        :aria-label="themeMode === 'dark' ? '切换浅色模式' : '切换深色模式'"
        @click="toggleTheme"
      >
        <svg
          v-if="themeMode === 'dark'"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2" />
          <path d="M12 20v2" />
          <path d="m4.93 4.93 1.41 1.41" />
          <path d="m17.66 17.66 1.41 1.41" />
          <path d="M2 12h2" />
          <path d="M20 12h2" />
          <path d="m6.34 17.66-1.41 1.41" />
          <path d="m19.07 4.93-1.41 1.41" />
        </svg>
        <svg
          v-else
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
        </svg>
      </button>
      <button class="tbtn" title="全屏" aria-label="切换全屏" @click="toggleFull">⤢</button>
    </div>
    <div class="runmode"><span class="dot g"></span>主用1+备用1 自动模式</div>
    <div class="clock">
      <div class="t">{{ time }}</div>
      <div class="d">{{ date }}</div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { getDashboardOverview } from '@/api'
import type { DashboardOverview } from '@/types'
import LanguageSwitcher from '@/components/common/LanguageSwitcher.vue'
import { themeMode, toggleTheme } from '@/theme'

/* 顶栏数据 + 时钟: 独立成组件, 避免其高频更新驱动 <router-view> 所在布局重渲染,
   从而在懒加载路由组件就绪前打断卸载、触发 vue-router "reading 'component'" 竞态。 */
const ov = ref<DashboardOverview | null>(null)
const time = ref('--:--:--')
const date = ref('')
let t1 = 0,
  t2 = 0

function tickClock() {
  const d = new Date()
  time.value = d.toLocaleTimeString('zh-CN', { hour12: false })
  date.value = d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
}

async function load() {
  try {
    ov.value = await getDashboardOverview()
  } catch {
    /* 忽略: 后端不可达时沿用旧值 */
  }
}

function toggleFull() {
  if (!document.fullscreenElement) document.documentElement.requestFullscreen?.()
  else document.exitFullscreen?.()
}

onMounted(() => {
  tickClock()
  load()
  t1 = window.setInterval(tickClock, 1000)
  t2 = window.setInterval(load, Number(import.meta.env.VITE_REFRESH_INTERVAL ?? 3000))
})

onBeforeUnmount(() => {
  clearInterval(t1)
  clearInterval(t2)
})
</script>
