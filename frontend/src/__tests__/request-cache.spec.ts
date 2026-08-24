import { beforeEach, describe, expect, it, vi } from 'vitest'

// 隔离路由 (避免级联加载视图)
vi.mock('@/router', () => ({
  default: { currentRoute: { value: { path: '/x' } }, push: vi.fn() },
}))

import request from '@/api/request'

// 用 axios adapter 注入假响应并计数, 验证 GET 缓存命中后不重复发请求
function installAdapter() {
  let calls = 0
  const adapter = async () => {
    calls += 1
    return {
      data: { n: calls },
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    } as never
  }
  ;(request.defaults as { adapter?: unknown }).adapter = adapter
  return () => calls
}

describe('request: GET 缓存', () => {
  beforeEach(() => {
    localStorage.clear()
    // 清空已写入的 GET 缓存 (模块级 Map 不跨用例重置, 此处无法访问; 用不同 URL 规避)
  })

  it('相同 GET 在 TTL 内命中缓存, 不重复请求', async () => {
    const getCalls = installAdapter()
    const url = `/api/cache-${Date.now()}` // 唯一 URL 避免跨用例缓存干扰
    const r1 = await request.get(url)
    const r2 = await request.get(url)
    expect(r1.data.n).toBe(1)
    expect(r2.data.n).toBe(1) // 命中缓存, 返回同一份
    expect(getCalls()).toBe(1) // adapter 只调一次
  })

  it('不同参数视为不同缓存键', async () => {
    const getCalls = installAdapter()
    await request.get('/api/p', { params: { a: 1 } })
    await request.get('/api/p', { params: { a: 2 } })
    expect(getCalls()).toBe(2)
  })

  it('POST 不进入 GET 缓存', async () => {
    const getCalls = installAdapter()
    await request.post('/api/p', { x: 1 })
    await request.post('/api/p', { x: 1 })
    expect(getCalls()).toBe(2)
  })
})
