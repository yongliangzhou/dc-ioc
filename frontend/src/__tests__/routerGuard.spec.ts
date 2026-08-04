import { describe, it, expect, vi, beforeEach } from 'vitest'
import { authGuard, isTokenValid } from '@/router'

/** 构造仅含 payload 的假 JWT (守卫只解码 payload.exp) */
function fakeJwt(payload: Record<string, unknown>): string {
  const b64 = btoa(JSON.stringify(payload))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '')
  return `head.${b64}.sig`
}

const futureExp = Math.floor(Date.now() / 1000) + 3600
const pastExp = Math.floor(Date.now() / 1000) - 3600

function login(roles: string[] | string, exp = futureExp) {
  localStorage.setItem('dc_ioc_token', fakeJwt({ exp }))
  const user = Array.isArray(roles) ? { roles } : { role: roles }
  localStorage.setItem('dc_ioc_user', JSON.stringify(user))
}

const to = (path: string, meta: Record<string, unknown> = {}) => ({ path, meta })

beforeEach(() => localStorage.clear())

describe('isTokenValid', () => {
  it('空 token / 非法格式 无效', () => {
    expect(isTokenValid(null)).toBe(false)
    expect(isTokenValid('not-a-jwt')).toBe(false)
  })
  it('未过期有效, 已过期无效', () => {
    expect(isTokenValid(fakeJwt({ exp: futureExp }))).toBe(true)
    expect(isTokenValid(fakeJwt({ exp: pastExp }))).toBe(false)
  })
})

describe('authGuard / 登录态', () => {
  it('未登录访问业务页 -> 重定向 /login', () => {
    const next = vi.fn()
    authGuard(to('/overview'), null, next)
    expect(next).toHaveBeenCalledWith('/login')
  })

  it('token 过期视为未登录并清除凭据', () => {
    login('admin', pastExp)
    const next = vi.fn()
    authGuard(to('/ops/alarms'), null, next)
    expect(next).toHaveBeenCalledWith('/login')
    expect(localStorage.getItem('dc_ioc_token')).toBeNull()
  })

  it('已登录访问 /login -> 跳驾驶舱', () => {
    login('viewer')
    const next = vi.fn()
    authGuard(to('/login'), null, next)
    expect(next).toHaveBeenCalledWith('/overview')
  })

  it('未登录访问 /login 放行', () => {
    const next = vi.fn()
    authGuard(to('/login'), null, next)
    expect(next).toHaveBeenCalledWith()
  })

  it('noAuth 路由未登录也放行', () => {
    const next = vi.fn()
    authGuard(to('/public', { noAuth: true }), null, next)
    expect(next).toHaveBeenCalledWith()
  })
})

describe('authGuard / RBAC', () => {
  const adminOnly = { requiredRoles: ['admin', 'operator'] }

  it('viewer 访问受限路由 -> 重定向驾驶舱', () => {
    login('viewer')
    const next = vi.fn()
    authGuard(to('/ops/tickets', adminOnly), null, next)
    expect(next).toHaveBeenCalledWith('/overview')
  })

  it('operator 访问受限路由放行 (roles 数组)', () => {
    login(['operator'])
    const next = vi.fn()
    authGuard(to('/ops/tickets', adminOnly), null, next)
    expect(next).toHaveBeenCalledWith()
  })

  it('admin 访问受限路由放行 (单 role 字段)', () => {
    login('admin')
    const next = vi.fn()
    authGuard(to('/admin/audit', adminOnly), null, next)
    expect(next).toHaveBeenCalledWith()
  })

  it('无角色要求的路由任何登录用户可访问', () => {
    login('viewer')
    const next = vi.fn()
    authGuard(to('/overview'), null, next)
    expect(next).toHaveBeenCalledWith()
  })
})
