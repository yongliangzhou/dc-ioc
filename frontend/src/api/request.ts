import axios, { AxiosInstance } from 'axios'
import router from '@/router'
import { mockForUrl } from './mockData'

const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 15000,
})

// ---- 请求拦截: 自动附加 Bearer token ----
request.interceptors.request.use((config) => {
  const token = localStorage.getItem('dc_ioc_token')
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ---- 后端不可达兜底 / 401 自动刷新 ----
let isRefreshing = false
let refreshQueue: Array<(token: string) => void> = []

function tryLocalFallback(err: any): unknown {
  const cfg = err?.config
  if (!cfg || String(cfg.method).toLowerCase() !== 'get') return undefined
  const status = err?.response?.status
  const noResponse = !err?.response
  // 后端不可达: 无响应 / 5xx 网关错误 (Vite proxy 目标未启动时返回 500)
  const mockMode = import.meta.env.VITE_MOCK_AUTH === 'true'
  const serverDown = status === 500 || status === 502 || status === 503 || status === 504
  // Mock 模式下任何 GET 失败都允许兜底; 否则仅限网络错误/网关错误
  if (!mockMode && !noResponse && !serverDown) return undefined
  const url: string = cfg.url || ''
  const data = mockForUrl(url, cfg)
  if (data !== undefined) {
    console.warn(`[mock-fallback] 后端不可达, 兜底返回旧版模拟数据: ${url}`)
    return data
  }
  return undefined
}

request.interceptors.response.use(
  (res) => res.data,
  async (err) => {
    const originalRequest = err?.config

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
