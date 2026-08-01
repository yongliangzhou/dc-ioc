<template>
  <div v-if="error" class="eb-fallback">
    <div class="eb-card">
      <div class="eb-icon">⚠</div>
      <div class="eb-title">页面渲染出错</div>
      <div class="eb-desc">该面板发生了运行时错误，已被安全隔离，其他功能不受影响。</div>
      <pre v-if="detail" class="eb-detail">{{ detail }}</pre>
      <div class="eb-actions">
        <button class="eb-btn primary" @click="reset">重试</button>
        <button class="eb-btn" @click="goHome">返回驾驶舱</button>
      </div>
    </div>
  </div>
  <!-- display:contents 包装层: 不影响布局, 仅用于 key 强制重建子树 -->
  <div v-else :key="renderKey" class="eb-slot"><slot /></div>
</template>

<script setup lang="ts">
/**
 * 全局错误边界 — 包裹路由视图, 单面板崩溃不白屏。
 *
 * - onErrorCaptured 捕获子组件树内任何渲染/生命周期/事件处理错误
 * - 返回 false 阻止错误继续向上冒泡导致整个应用崩溃
 * - "重试" 通过递增 renderKey 强制重建子树; 路由切换时自动复位
 */
import { onErrorCaptured, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const error = ref<Error | null>(null);
const detail = ref("");
const renderKey = ref(0);

const route = useRoute();
const router = useRouter();

onErrorCaptured((err, _instance, info) => {
  error.value = err instanceof Error ? err : new Error(String(err));
  detail.value = `${error.value.message}\n[hook] ${info}`;
  // eslint-disable-next-line no-console
  console.error("[ErrorBoundary] 已捕获子树错误:", err, "info:", info);
  return false; // 阻止冒泡, 避免整页白屏
});

function reset() {
  error.value = null;
  detail.value = "";
  renderKey.value++;
}

function goHome() {
  reset();
  router.push("/overview");
}

// 路由切换自动复位错误状态
watch(() => route.fullPath, () => {
  if (error.value) reset();
});
</script>

<style scoped>
.eb-slot { display: contents; }
.eb-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 24px;
}
.eb-card {
  max-width: 560px;
  width: 100%;
  text-align: center;
  padding: 36px 32px;
  border-radius: 12px;
  background: var(--panel, rgba(255, 255, 255, 0.04));
  border: 1px solid var(--line, rgba(255, 255, 255, 0.12));
}
.eb-icon { font-size: 40px; margin-bottom: 12px; color: #ffb020; }
.eb-title { font-size: 18px; font-weight: 600; color: var(--txt, #e6edf3); margin-bottom: 8px; }
.eb-desc { font-size: 13px; color: var(--txt2, #8892b0); margin-bottom: 14px; }
.eb-detail {
  text-align: left;
  font-size: 11px;
  line-height: 1.5;
  color: #e57373;
  background: rgba(229, 57, 53, 0.08);
  border: 1px solid rgba(229, 57, 53, 0.25);
  border-radius: 8px;
  padding: 10px 12px;
  margin: 0 0 16px;
  max-height: 140px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.eb-actions { display: flex; gap: 10px; justify-content: center; }
.eb-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--line, rgba(255, 255, 255, 0.15));
  color: var(--txt2, #8892b0);
  transition: all 0.2s;
}
.eb-btn:hover { color: var(--txt, #e6edf3); border-color: rgba(255, 255, 255, 0.3); }
.eb-btn.primary {
  background: rgba(66, 165, 245, 0.15);
  border-color: rgba(66, 165, 245, 0.4);
  color: #42a5f5;
}
.eb-btn.primary:hover { background: rgba(66, 165, 245, 0.25); }
</style>
