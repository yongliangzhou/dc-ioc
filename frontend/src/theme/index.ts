import { ref, watch } from "vue";

/**
 * 全局主题 (dark / light)
 * - CSS: html[data-theme] 驱动 index.scss 中的 CSS 变量切换
 * - ECharts: useECharts / options.ts 依赖 themeMode 响应式重建
 * - 持久化: localStorage
 */
export type ThemeMode = "dark" | "light";

const STORAGE_KEY = "dcioc-theme";

function load(): ThemeMode {
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    if (v === "light" || v === "dark") return v;
  } catch { /* SSR/隐私模式忽略 */ }
  return "dark";
}

export const themeMode = ref<ThemeMode>(load());

export function applyTheme(mode: ThemeMode = themeMode.value): void {
  if (typeof document !== "undefined") {
    document.documentElement.dataset.theme = mode;
  }
}

export function toggleTheme(): void {
  themeMode.value = themeMode.value === "dark" ? "light" : "dark";
}

watch(themeMode, (m) => {
  applyTheme(m);
  try { localStorage.setItem(STORAGE_KEY, m); } catch { /* ignore */ }
});

// 模块加载即生效 (main.ts 引入)
applyTheme();
