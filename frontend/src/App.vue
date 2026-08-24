<template>
  <router-view />
  <AlarmNotification />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/modules/auth'
import { initRealtimeBus, closeRealtimeBus } from '@/core/wsBus'
import { useTelemetryStore } from '@/stores/modules/telemetry'
import AlarmNotification from '@/components/business/AlarmNotification.vue'
import { requestNotificationPermission } from '@/engine/alarmNotifier'

const authStore = useAuthStore()
const telemetry = useTelemetryStore()

onMounted(async () => {
  if (authStore.token) {
    try {
      await authStore.fetchUser()
    } catch {
      authStore.logout()
    }
  }
  // 申请浏览器通知权限（弹窗 + 消息推送）
  requestNotificationPermission()
  // 启动全局实时总线 (WS -> Pinia store)
  await telemetry.fetchInitial()
  initRealtimeBus()
})

onUnmounted(() => {
  closeRealtimeBus()
})
</script>
