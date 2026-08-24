import { ref } from 'vue'

/** 后端错误响应结构 (AxiosError / axios response / FastAPI 422) */
interface ErrorLike {
  detail?: unknown
  message?: string
  response?: {
    data?: {
      detail?: unknown
      message?: string
    }
  }
}

/** FastAPI 422 校验错误单项 */
interface ErrorDetail {
  loc?: unknown
  msg?: string
}

/**
 * 统一异步任务包装：防重复点击 + loading 状态 + 错误提取。
 *
 * 用法：
 *   const { loading, run } = useAsyncTask(async (id: string) => { await api(id) });
 *   await run("x"); // loading 期间重复调用会自动忽略
 */
export function useAsyncTask<T extends (...args: never[]) => Promise<unknown>>(fn: T) {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function run(...args: Parameters<T>): Promise<Awaited<ReturnType<T>> | undefined> {
    if (loading.value) return undefined // 防重复点击
    loading.value = true
    error.value = null
    try {
      return (await fn(...args)) as unknown as Awaited<ReturnType<T>>
    } catch (e: unknown) {
      error.value = extractError(e)
      throw e
    } finally {
      loading.value = false
    }
  }

  return { loading, error, run }
}

/** 从 request.ts 抛出的错误对象中提取可读信息 */
export function extractError(e: unknown): string {
  if (!e) return '操作失败，请重试'
  // 后端校验错误数组 (FastAPI 422) 或字符串 detail
  const err = e as ErrorLike
  const detail = err.detail ?? err.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    return detail
      .map((d: ErrorDetail) => {
        const loc = Array.isArray(d.loc) ? (d.loc as unknown[]) : []
        const field = loc.slice(-1)[0] ?? ''
        return [field, d.msg].filter(Boolean).join(': ')
      })
      .join('；')
  }
  return err.message || err.response?.data?.message || '操作失败，请重试'
}
