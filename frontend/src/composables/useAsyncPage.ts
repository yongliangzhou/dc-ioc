/**
 * useAsyncPage — 统一异步页面状态机
 *
 * 设计目标:
 * - 消灭全站 `catch(() => {})` 静默吞错: 任何失败都必须落到可视的 error 状态
 * - 状态互斥且完备: loading / error / empty / success 四态, 模板无需手写 if-else
 * - 竞态安全: 请求乱序返回时丢弃过期结果 (seq 守卫)
 * - 路由切换中断 (abortPendingRequests) 不算错误, 不闪错误态
 * - 防骨架闪烁: minLoadingMs 内不切换到完成态
 *
 * 用法:
 *   const page = useAsyncPage(() => getAlarms(), { isEmpty: (d) => !d.length })
 *   <AsyncSection v-bind="page" @retry="page.reload">
 *     <AlarmTable :rows="page.data.value" />
 *   </AsyncSection>
 *
 * 多源并发 (部分失败仍渲染, 顶部挂汇总横幅):
 *   const all = useAsyncPageAll({ overview: getDashboardOverview, alarms: getActiveAlarms })
 *   all.pages.overview.data / all.errorCount / all.failedKeys / all.reloadAll()
 */
import { ref, computed, onUnmounted, getCurrentInstance, type Ref } from 'vue'

/* ------------------------------------------------------------------ */
/* 错误归一化                                                           */
/* ------------------------------------------------------------------ */

/** 路由切换时 abortPendingRequests() 会中断请求, 这类错误不应呈现为错误态 */
export function isAbortError(e: unknown): boolean {
  if (!e || typeof e !== 'object') return false
  const err = e as { name?: string; code?: string; message?: string }
  return (
    err.name === 'CanceledError' ||
    err.name === 'AbortError' ||
    err.code === 'ERR_CANCELED' ||
    err.code === 'ECONNABORTED' ||
    /canceled|cancelled|aborted/i.test(err.message ?? '')
  )
}

const HTTP_MSG: Record<number, string> = {
  400: '请求参数有误',
  401: '登录已过期，请重新登录',
  403: '当前角色无访问权限',
  404: '接口不存在或资源已下线',
  408: '请求超时，请重试',
  422: '提交的数据未通过校验',
  429: '操作过于频繁，请稍后再试',
  500: '服务内部错误',
  502: '网关异常，后端服务可能未就绪',
  503: '服务暂时不可用',
  504: '服务响应超时',
}

/**
 * 把任意异常归一化为可展示的中文文案。
 * 返回空串表示"这是被主动中断的请求, 不需要呈现错误"。
 */
export function toErrorMessage(e: unknown, fallback = '加载失败'): string {
  if (isAbortError(e)) return ''
  if (!e) return fallback

  const err = e as {
    response?: { status?: number; data?: unknown }
    status?: number
    code?: string
    name?: string
    message?: unknown
    detail?: unknown
    msg?: unknown
  }
  // request.ts 对 HTTP 错误 reject 的是 err.response.data（FastAPI 直出 {detail/message/msg}），
  // axios 错误才是 { response: { data, status } } 形态，mock 兜底抛的也带 response.data。
  // 统一解析两种形态，避免把后端明确返回的文案误判成「网络异常或服务未启动」。
  const hasPayloadField =
    typeof err.detail !== 'undefined' ||
    typeof err.msg !== 'undefined' ||
    typeof err.message !== 'undefined'
  const data = (err.response?.data ?? (hasPayloadField ? err : undefined)) as
    { detail?: unknown; message?: unknown; msg?: unknown } | undefined

  // FastAPI 422: detail 为 [{loc:[...], msg}] 数组
  const detail = data?.detail
  if (Array.isArray(detail) && detail.length) {
    const first = detail[0]
    if (typeof first === 'string') return first
    if (first && typeof first === 'object') {
      const f = first as { loc?: unknown[]; msg?: string }
      const loc = Array.isArray(f.loc) ? String(f.loc.slice(-1)[0] ?? '') : ''
      const msg = f.msg ?? '参数校验未通过'
      return loc ? `${loc}: ${msg}` : msg
    }
  }
  if (typeof detail === 'string' && detail) return detail
  if (typeof data?.message === 'string' && data.message) return data.message
  if (typeof data?.msg === 'string' && data.msg) return data.msg

  const status = err.response?.status ?? err.status
  if (status && HTTP_MSG[status]) {
    return status >= 500 ? `${HTTP_MSG[status]}（${status}）` : HTTP_MSG[status]
  }

  // 无 response：可能是请求根本没发出去（断网 / 后端未启动），
  // 也可能是业务代码直接 throw new Error('文案') —— 后者优先展示原文。
  if (!err.response) {
    const m = err.message == null ? '' : String(err.message)
    const isNetworkLike =
      err.name === 'AxiosError' ||
      err.name === 'TypeError' ||
      err.name === 'TimeoutError' ||
      /network|timeout|timed out|fetch/i.test(m)
    if (m && !isNetworkLike) return m
    return '网络异常或服务未启动'
  }
  const m = err.message == null ? '' : String(err.message)
  return m || fallback
}

/**
 * 模拟数据分级标记。
 *
 * 一批页面存在「真接口无有效返回 → 回退到本地 mockSummary()」的兜底逻辑。
 * 兜底本身可以接受（后端没起来时页面仍可演示），
 * 但**必须让用户看见当前是假的**——否则运维会把"市政电源 1#"当成真实遥测。
 *
 * 更危险的是第二档 `partial`：后端返回了真实设备，页面却把接口表 / 热力图 /
 * 协议分布等字段用 mockData() 补齐，甚至给真实设备挂上 Math.random() 的读数。
 * 这种「真假混排」用户完全无法分辨，必须显式点名哪些是假的。
 *
 * 用法:
 *   const { level, markReal, markPartial, markFull } = useMockLevel()
 *   // 数据全部来自真接口 → markReal()
 *   // 真设备 + 部分模拟字段 → markPartial('接口表 / 吞吐趋势由本地生成')
 *   // 整页都是模拟 → markFull()
 *   模板: <MockDataBanner :level="level" />
 *
 * 正确范本见 monitor/SecurityCctv.vue / SecurityAcs.vue（仅做了 full 一档）。
 */
export type MockLevel = 'none' | 'partial' | 'full'

export function useMockFlag(init: MockLevel = 'none') {
  const level = ref<MockLevel>(init)
  const reason = ref('')
  return {
    level,
    reason,
    isMock: computed(() => level.value !== 'none'),
    markReal: () => {
      level.value = 'none'
      reason.value = ''
    },
    markPartial: (why = '') => {
      level.value = 'partial'
      reason.value = why
    },
    markFull: (why = '') => {
      level.value = 'full'
      reason.value = why
    },
    /** 兼容旧调用: 等价于 markFull */
    markMock: (why = '') => {
      level.value = 'full'
      reason.value = why
    },
  }
}

/* ------------------------------------------------------------------ */
/* 单源                                                                */
/* ------------------------------------------------------------------ */

export interface UseAsyncPageOptions<T> {
  /** onMounted 时自动加载, 默认 true */
  autoLoad?: boolean
  /** 初始数据, 失败且 keepDataOnError=false 时回滚到此值 */
  initial?: T
  /** 自定义空态判定, 默认: 数组判空 / null 判空 */
  isEmpty?: (data: T) => boolean
  /** 最短 loading 时长 (ms), 防骨架闪烁, 默认 180 */
  minLoadingMs?: number
  /** 失败时是否保留上一次成功的数据 (轮询场景推荐 true, 避免列表闪空) */
  keepDataOnError?: boolean
  onError?: (message: string, raw: unknown) => void
  onSuccess?: (data: T) => void
}

export interface AsyncPageResult<T> {
  data: Ref<T>
  loading: Ref<boolean>
  /** 归一化后的中文错误文案, 空串表示无错误 */
  error: Ref<string>
  rawError: Ref<unknown>
  /** 已完成过至少一次成功请求 */
  loaded: Ref<boolean>
  /** 是否处于"已有错误后再次尝试"的状态 */
  retrying: Ref<boolean>
  /** loading || retrying */
  busy: Ref<boolean>
  empty: Ref<boolean>
  reload: () => Promise<void>
  setData: (value: T) => void
  clearError: () => void
}

export function useAsyncPage<T>(
  fetcher: () => Promise<T>,
  options: UseAsyncPageOptions<T> = {},
): AsyncPageResult<T> {
  const {
    autoLoad = true,
    initial = undefined as unknown as T,
    isEmpty,
    minLoadingMs = 180,
    keepDataOnError = true,
    onError,
    onSuccess,
  } = options

  const data = ref(initial) as Ref<T>
  const loading = ref(false)
  const error = ref('')
  const rawError = ref<unknown>(null)
  const loaded = ref(false)
  const retrying = ref(false)

  // 组件卸载后不再写状态 (composable 也可能在组件外被调用, 故先探测实例)
  let alive = true
  if (getCurrentInstance()) {
    onUnmounted(() => {
      alive = false
    })
  }

  // 竞态守卫: 只有最后一次发起的请求可以写状态
  let seq = 0

  async function run(asRetry: boolean) {
    if (!alive) return
    const my = ++seq
    const startedAt = Date.now()

    if (asRetry) retrying.value = true
    else loading.value = true
    error.value = ''
    rawError.value = null

    try {
      const res = await fetcher()
      if (!alive || my !== seq) return
      data.value = res
      loaded.value = true
      error.value = ''
      rawError.value = null
      onSuccess?.(res)
    } catch (e) {
      if (!alive || my !== seq) return
      const msg = toErrorMessage(e)
      // 主动中断的请求: 静默丢弃, 不呈现错误
      if (!msg) {
        loading.value = false
        retrying.value = false
        return
      }
      rawError.value = e
      error.value = msg
      if (!keepDataOnError) data.value = initial
      onError?.(msg, e)
    } finally {
      if (alive && my === seq) {
        const wait = Math.max(0, minLoadingMs - (Date.now() - startedAt))
        if (wait > 0) await new Promise((r) => setTimeout(r, wait))
        if (alive && my === seq) {
          loading.value = false
          retrying.value = false
        }
      }
    }
  }

  /** 已有错误时按"重试"呈现 (按钮转圈), 否则按"首次加载"呈现 (骨架) */
  function reload() {
    return run(!!error.value)
  }

  function setData(value: T) {
    data.value = value
    loaded.value = true
  }

  function clearError() {
    error.value = ''
    rawError.value = null
  }

  const empty = computed(() => {
    if (loading.value || retrying.value) return false
    if (error.value) return false
    if (!loaded.value) return false
    if (isEmpty) return isEmpty(data.value)
    const d = data.value as unknown
    if (Array.isArray(d)) return d.length === 0
    return d === null || d === undefined
  })

  const busy = computed(() => loading.value || retrying.value)

  if (autoLoad && getCurrentInstance()) {
    // 延迟到挂载后执行, 与 onMounted 语义一致
    Promise.resolve().then(() => run(false))
  }

  return {
    data,
    loading,
    error,
    rawError,
    loaded,
    retrying,
    busy,
    empty,
    reload,
    setData,
    clearError,
  }
}

/* ------------------------------------------------------------------ */
/* 多源并发                                                            */
/* ------------------------------------------------------------------ */

export type FetcherMap = Record<string, () => Promise<unknown>>

export interface UseAsyncPageAllOptions {
  autoLoad?: boolean
  minLoadingMs?: number
  onError?: (key: string, message: string, raw: unknown) => void
}

export interface AsyncPageAllResult<T extends FetcherMap> {
  pages: { [K in keyof T]: AsyncPageResult<Awaited<ReturnType<T[K]>>> }
  /** 是否至少有一个源失败 */
  anyError: Ref<boolean>
  /** 失败的源数量 */
  errorCount: Ref<number>
  /** 失败的源 key 列表 */
  failedKeys: Ref<string[]>
  anyLoading: Ref<boolean>
  allLoading: Ref<boolean>
  reloadAll: () => Promise<void>
  /** 仅重试失败的源 */
  reloadFailed: () => Promise<void>
}

/**
 * 并发管理多个数据源, 单个源失败不影响其它源渲染,
 * 但会把失败暴露给调用方 (顶部横幅), 不允许静默降级。
 */
export function useAsyncPageAll<T extends FetcherMap>(
  fetchers: T,
  options: UseAsyncPageAllOptions = {},
): AsyncPageAllResult<T> {
  const { autoLoad = true, minLoadingMs = 180, onError } = options

  const pages = {} as { [K in keyof T]: AsyncPageResult<Awaited<ReturnType<T[K]>>> }
  for (const key of Object.keys(fetchers) as Array<keyof T>) {
    pages[key] = useAsyncPage(fetchers[key], {
      autoLoad,
      minLoadingMs,
      onError: (message, raw) => onError?.(String(key), message, raw),
    }) as unknown as AsyncPageResult<Awaited<ReturnType<T[keyof T]>>>
  }

  const keys = Object.keys(fetchers)
  const list = computed(() => keys.map((k) => pages[k as keyof T] as AsyncPageResult<unknown>))

  const failedKeys = computed(() =>
    keys.filter((k) => !!(pages[k as keyof T] as AsyncPageResult<unknown>).error.value),
  )
  const errorCount = computed(() => failedKeys.value.length)
  const anyError = computed(() => errorCount.value > 0)
  const anyLoading = computed(() => list.value.some((p) => p.busy.value))
  const allLoading = computed(() => list.value.every((p) => p.busy.value))

  async function reloadAll() {
    await Promise.all(list.value.map((p) => p.reload()))
  }

  async function reloadFailed() {
    await Promise.all(
      failedKeys.value.map((k) => (pages[k as keyof T] as AsyncPageResult<unknown>).reload()),
    )
  }

  return {
    pages,
    anyError,
    errorCount,
    failedKeys,
    anyLoading,
    allLoading,
    reloadAll,
    reloadFailed,
  }
}
