import axios, {
  AxiosError,
  AxiosInstance,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'
import router from '@/router'
import { mockForUrl, mockWriteForUrl } from './mockData'

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    _retry?: boolean
    // 存储 FormData 中的 File 引用，写操作兜底 mock 时可读取
    __file?: File | undefined
    // 每个请求挂载的独立 AbortController，路由切换时统一中断
    _controller?: AbortController
  }
}

const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
})

// ---- GET 短时缓存 (仅幂等 GET 生效, 成功响应后才写缓存) ----
interface CacheEntry {
  data: unknown
  ts: number
}
const GET_CACHE_TTL = 5000
const getCache = new Map<string, CacheEntry>()

function cacheKeyOf(config: { url?: string; method?: string; params?: unknown }): string | null {
  if (String(config.method || 'get').toLowerCase() !== 'get') return null
  if (!config.url) return null
  const params = config.params ? JSON.stringify(config.params) : ''
  return `${config.url}?${params}`
}

// ---- 请求取消: 路由切换时中断未完成请求 ----
const pendingControllers = new Set<AbortController>()

/** 中断所有尚未完成的请求 (路由切换时调用) */
export function abortPendingRequests(): void {
  for (const c of pendingControllers) {
    try {
      c.abort()
    } catch {
      /* noop */
    }
  }
  pendingControllers.clear()
}

// ---- 请求拦截: 自动附加 Bearer token + 提取 File (for import mock) + 挂 AbortController ----
request.interceptors.request.use((config) => {
  // GET 短时缓存命中: 在发起真实请求前短路返回, 减少重复后端调用
  const key = cacheKeyOf(config)
  if (key) {
    const hit = getCache.get(key)
    if (hit && Date.now() - hit.ts < GET_CACHE_TTL) {
      return Promise.resolve({
        data: hit.data,
        status: 200,
        statusText: 'cached',
        headers: {},
        config,
      } as AxiosResponse)
    }
  }

  const token = localStorage.getItem('dc_ioc_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // FormData 中若有 file 字段，引用存到 __file 以便写操作 mock 时读取
  if (config.data instanceof FormData) {
    const f = config.data.get('file')
    if (f instanceof File) config.__file = f
  }
  // 为每个请求挂载独立的 AbortController，支持路由切换时统一中断
  const controller = new AbortController()
  config.signal = controller.signal
  pendingControllers.add(controller)
  config._controller = controller
  return config
})

// 响应完成后从待取消集合中移除对应 controller
function releaseController(config: InternalAxiosRequestConfig | undefined): void {
  const c = (config as InternalAxiosRequestConfig & { _controller?: AbortController })?._controller
  if (c) pendingControllers.delete(c)
}

// ---- 后端不可达兜底 / 401 自动刷新 ----
let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

/** 极简 toast（避免与 useToast 双向循环依赖） */
function flashError(message: string) {
  try {
    const id = 'global-err-toast-' + Date.now()
    let el = document.getElementById('dc-toast-root')
    if (!el) {
      el = document.createElement('div')
      el.id = 'dc-toast-root'
      el.style.cssText =
        'position:fixed;top:24px;right:24px;z-index:99999;display:flex;flex-direction:column;gap:8px;pointer-events:none;'
      document.body.appendChild(el)
    }
    const item = document.createElement('div')
    item.id = id
    item.textContent = message
    item.style.cssText =
      'background:rgba(248,113,113,0.95);color:#fff;padding:10px 16px;border-radius:8px;font-size:13px;box-shadow:0 4px 16px rgba(0,0,0,0.25);pointer-events:auto;max-width:360px;line-height:1.5;'
    el.appendChild(item)
    setTimeout(() => {
      const t = document.getElementById(id)
      if (t && el.contains(t)) el.removeChild(t)
    }, 4200)
  } catch {
    /* noop */
  }
}

function isWriteMethod(method: string | undefined) {
  const m = String(method || '').toLowerCase()
  return m === 'post' || m === 'put' || m === 'delete' || m === 'patch'
}

function tryLocalFallback(err: AxiosError): unknown {
  const cfg = err?.config as InternalAxiosRequestConfig | undefined
  if (!cfg) return undefined
  const status = err?.response?.status
  const noResponse = !err?.response
  const mockMode = import.meta.env.VITE_MOCK_AUTH === 'true'
  const serverDown = status === 500 || status === 502 || status === 503 || status === 504
  // 关键修复: 后端路由未实现时通常返回 404 (Not Found) 或 405 (Method Not Allowed)
  // 这些情况也允许走 mock 兜底 (演示环境 / 后端尚未开发完 CRUD)
  const routeNotImplemented = status === 404 || status === 405
  // Mock 模式下任何失败都允许兜底; 否则: 网络错误 / 网关错误 / 路由未实现 -> 兜底
  if (!mockMode && !noResponse && !serverDown && !routeNotImplemented) return undefined

  const url: string = cfg.url || ''
  const method = String(cfg.method || 'get').toLowerCase()

  // GET -> 读 mock
  if (!isWriteMethod(method)) {
    const data = mockForUrl(url, cfg)
    if (data !== undefined) {
      console.warn(`[mock-fallback] 后端不可达, 兜底返回旧版模拟数据: ${method.toUpperCase()} ${url}`)
      return data
    }
    return undefined
  }

  // POST/PUT/DELETE/PATCH -> 写 mock (操作内存 STORE)
  const payload = cfg.data
  let decoded: unknown = payload
  if (typeof payload === 'string' && payload) {
    try {
      decoded = JSON.parse(payload)
    } catch {
      decoded = payload
    }
  }
  // 关键修复1: 从 FormData 中提取上传的 File 对象 + category/tags/description 等字段，
  //          供知识库导入 / 文件上传等 mock 兜底读取
  const extra: {
    params?: Record<string, unknown>
    __file?: File
    __formData?: FormData
  } = { params: cfg.params as Record<string, unknown> | undefined }
  if (decoded instanceof FormData) {
    const fileEntry = decoded.get('file')
    if (fileEntry instanceof File) extra.__file = fileEntry
    extra.__formData = decoded
  }
  const wrote = mockWriteForUrl(method, url, decoded, extra)
  if (wrote !== undefined) {
    console.warn(
      `[mock-fallback-write] 后端不可达, 写操作已落到前端内存: ${method.toUpperCase()} ${url}`,
    )
    return wrote
  }

  // 没命中任何 mock，给用户弹全局错误提示，避免"点了没反应"
  const hint =
    status === 401
      ? '登录状态已失效，请重新登录'
      : noResponse || serverDown
        ? '后端服务未启动或网络不通，已自动进入演示模式（本次未命中）'
        : `请求失败 (HTTP ${status ?? 'ERR'})`
  flashError(`${hint}: ${method.toUpperCase()} ${url}`)
  return undefined
}

request.interceptors.response.use(
  (res) => {
    releaseController(res.config)
    // 写 GET 缓存 (成功响应后才写入)
    const key = cacheKeyOf(res.config)
    if (key && res.status >= 200 && res.status < 300) {
      getCache.set(key, { data: res.data, ts: Date.now() })
    }
    return res.data
  },
  async (err: AxiosError) => {
    const originalRequest = err?.config
    releaseController(originalRequest)

    // 网络层错误 (无响应) 且为幂等 GET 时, 重试 1 次 (间隔 300ms)
    const isNetworkError = !err?.response && axios.isAxiosError(err)
    const isRetryableGet = String(originalRequest?.method || 'get').toLowerCase() === 'get'
    if (
      isNetworkError &&
      isRetryableGet &&
      originalRequest &&
      !(originalRequest as typeof originalRequest & { _netRetry?: boolean })._netRetry
    ) {
      ;(originalRequest as typeof originalRequest & { _netRetry?: boolean })._netRetry = true
      await new Promise((r) => setTimeout(r, 300))
      try {
        const retryResp = await request(originalRequest)
        return retryResp
      } catch (retryErr) {
        // 重试仍失败 → 落到下方兜底逻辑
        err = retryErr as AxiosError
      }
    }

    // 401 且未重试过 → 尝试刷新 token
    if (err?.response?.status === 401 && originalRequest && !originalRequest._retry) {
      const refreshToken = localStorage.getItem('dc_ioc_refresh')
      if (!refreshToken) {
        // 无 refresh token → 跳转登录页
        localStorage.removeItem('dc_ioc_token')
        localStorage.removeItem('dc_ioc_user')
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
        return Promise.reject(err.response?.data ?? err)
      }

      if (isRefreshing) {
        return new Promise((resolve) => {
          refreshQueue.push((newToken: string) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            resolve(request(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        // 使用不带拦截器的临时实例避免死循环
        const resp = await axios.post(`${import.meta.env.VITE_API_BASE_URL}/api/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const newToken = resp.data.access_token
        const newRefreshToken = resp.data.refresh_token
        localStorage.setItem('dc_ioc_token', newToken)
        localStorage.setItem('dc_ioc_refresh', newRefreshToken)
        localStorage.setItem('dc_ioc_user', JSON.stringify(resp.data.user))

        refreshQueue.forEach((cb) => cb(newToken))
        refreshQueue = []

        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return request(originalRequest)
      } catch {
        refreshQueue = []
        localStorage.removeItem('dc_ioc_token')
        localStorage.removeItem('dc_ioc_refresh')
        localStorage.removeItem('dc_ioc_user')
        if (router.currentRoute.value.path !== '/login') {
          router.push('/login')
        }
        return Promise.reject(err.response?.data ?? err)
      } finally {
        isRefreshing = false
      }
    }

    // 后端不可达兜底
    const fallback = tryLocalFallback(err)
    if (fallback !== undefined) return Promise.resolve(fallback)
    return Promise.reject(err.response?.data ?? err)
  },
)

export default request

// orval mutator — 适配生成代码的 fetch client 调用模式
export const customRequest = <T>(config: {
  url: string
  method: string
  params?: unknown
  data?: unknown
  headers?: Record<string, string>
}): Promise<T> => {
  return request({
    url: config.url,
    method: config.method,
    params: config.params,
    data: config.data,
    headers: config.headers,
  }) as Promise<T>
}
