import { ref } from "vue";

/**
 * 统一异步任务包装：防重复点击 + loading 状态 + 错误提取。
 *
 * 用法：
 *   const { loading, run } = useAsyncTask(async (id: string) => { await api(id) });
 *   await run("x"); // loading 期间重复调用会自动忽略
 */
export function useAsyncTask<T extends (...args: any[]) => Promise<any>>(fn: T) {
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function run(...args: Parameters<T>): Promise<Awaited<ReturnType<T>> | undefined> {
    if (loading.value) return undefined; // 防重复点击
    loading.value = true;
    error.value = null;
    try {
      return await fn(...args);
    } catch (e: any) {
      error.value = extractError(e);
      throw e;
    } finally {
      loading.value = false;
    }
  }

  return { loading, error, run };
}

/** 从 request.ts 抛出的错误对象中提取可读信息 */
export function extractError(e: any): string {
  if (!e) return "操作失败，请重试";
  // 后端校验错误数组 (FastAPI 422) 或字符串 detail
  const detail = e?.detail ?? e?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d: any) => {
        const field = d?.loc?.slice(-1)?.[0] ?? "";
        return [field, d?.msg].filter(Boolean).join(": ");
      })
      .join("；");
  }
  return e?.message || e?.response?.data?.message || "操作失败，请重试";
}
