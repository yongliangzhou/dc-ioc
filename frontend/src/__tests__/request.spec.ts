import { describe, it, expect, vi, beforeEach } from 'vitest'

// 隔离依赖: 不加载真实路由 (会级联加载全部视图) 与旧版 mock 数据
vi.mock('@/router', () => ({
  default: { currentRoute: { value: { path: '/overview' } }, push: vi.fn() },
}))
vi.mock('@/api/mockData', () => ({
  mockForUrl: vi.fn((url: string) => (url === '/api/known' ? { mocked: true } : undefined)),
}))

import request from '@/api/request'
import router from '@/router'
import { mockForUrl } from '@/api/mockData'

// axios 拦截器内部 handlers (axios v1 稳定结构)
interface AxiosHandler {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  fulfilled: (arg: any) => any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  rejected: (arg: any) => any
}
const reqHandler = (request.interceptors.request as unknown as { handlers: AxiosHandler[] }).handlers[0]
const resHandler = (request.interceptors.response as unknown as { handlers: AxiosHandler[] }).handlers[0]

beforeEach(() => {
  localStorage.clear()
  vi.clearAllMocks()
})

describe('请求拦截器', () => {
  it('localStorage 有 token 时附加 Authorization: Bearer', () => {
    localStorage.setItem('dc_ioc_token', 'abc123')
    const cfg = reqHandler.fulfilled({ headers: {} })
    expect(cfg.headers.Authorization).toBe('Bearer abc123')
  })

  it('无 token 时不附加 Authorization', () => {
    const cfg = reqHandler.fulfilled({ headers: {} })
    expect(cfg.headers.Authorization).toBeUndefined()
  })
})

describe('响应拦截器', () => {
  it('成功响应直接解包 res.data', () => {
    expect(resHandler.fulfilled({ data: { ok: 1 }, status: 200 })).toEqual({ ok: 1 })
  })

  it('401 且无 refresh token: 清凭据并跳转登录页', async () => {
    localStorage.setItem('dc_ioc_token', 'expired')
    localStorage.setItem('dc_ioc_user', JSON.stringify({ role: 'admin' }))
    const err = {
      config: { url: '/api/x', method: 'get', headers: {} },
      response: { status: 401, data: { detail: 'unauthorized' } },
    }
    await expect(resHandler.rejected(err)).rejects.toEqual({ detail: 'unauthorized' })
    expect(localStorage.getItem('dc_ioc_token')).toBeNull()
    expect(localStorage.getItem('dc_ioc_user')).toBeNull()
    expect((router as unknown as { push: (p: string) => void }).push).toHaveBeenCalledWith('/login')
  })

  it('后端不可达 (无 response) 的 GET 请求走本地 mock 兜底', async () => {
    const err = { config: { url: '/api/known', method: 'get' } } // 无 response => 网络错误
    await expect(resHandler.rejected(err)).resolves.toEqual({ mocked: true })
    expect(mockForUrl).toHaveBeenCalledWith('/api/known', err.config)
  })

  it('无兜底数据的 GET 网络错误仍然 reject', async () => {
    const err = { config: { url: '/api/unknown', method: 'get' } }
    await expect(resHandler.rejected(err)).rejects.toBe(err)
  })

  it('POST 请求不走 mock 兜底', async () => {
    const err = {
      config: { url: '/api/known', method: 'post' },
      response: { status: 503, data: 'down' },
    }
    await expect(resHandler.rejected(err)).rejects.toBe('down')
    expect(mockForUrl).not.toHaveBeenCalled()
  })
})
