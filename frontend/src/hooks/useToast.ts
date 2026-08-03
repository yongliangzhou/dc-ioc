import { reactive } from "vue";

export type ToastType = "success" | "error" | "info" | "warning";

export interface ToastItem {
  id: number;
  type: ToastType;
  message: string;
}

// 全局单例状态，由 Toast.vue 渲染
const state = reactive<{ items: ToastItem[] }>({ items: [] });
let seq = 0;

function push(type: ToastType, message: string, duration = 3200) {
  const id = ++seq;
  state.items.push({ id, type, message });
  if (duration > 0) {
    window.setTimeout(() => remove(id), duration);
  }
  return id;
}

export function remove(id: number) {
  const i = state.items.findIndex((t) => t.id === id);
  if (i >= 0) state.items.splice(i, 1);
}

export function useToast() {
  return {
    items: state.items,
    success: (m: string, d?: number) => push("success", m, d),
    error: (m: string, d?: number) => push("error", m, d),
    info: (m: string, d?: number) => push("info", m, d),
    warning: (m: string, d?: number) => push("warning", m, d),
    remove,
  };
}
