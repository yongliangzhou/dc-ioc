import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import request from '@/api/request'
import type { UserInfo, TokenResponse } from '@/types'

const TOKEN_KEY = 'dc_ioc_token'
const REFRESH_KEY = 'dc_ioc_refresh'
const USER_KEY = 'dc_ioc_user'
export const REMEMBER_KEY = 'dc_ioc_remember'
/** “记住我”：登录框取消勾选时，本次会话在每次整页加载后都要求重新登录 */
export function isRemembered(): boolean {
  return localStorage.getItem(REMEMBER_KEY) !== '0'
}

const MOCK_AUTH = import.meta.env.VITE_MOCK_AUTH === 'true'
const MOCK_TOKEN = 'mock-ioc-token-demo-frontend-only'
const MOCK_USER: UserInfo = {
  id: 1,
  username: 'admin',
  display_name: '系统管理员 (Mock模式)',
  department: '运维部',
  is_superuser: true,
  roles: ['admin'],
  permissions: ['*'],
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string>(localStorage.getItem(TOKEN_KEY) || '')
  const refreshToken = ref<string>(localStorage.getItem(REFRESH_KEY) || '')
  const user = ref<UserInfo | null>(loadUser())

  const isLoggedIn = ref(!!token.value)
  const isAdmin = ref(user.value?.is_superuser || user.value?.roles?.includes('admin') || false)

  // 同步更新
  watch(token, (v) => {
    isLoggedIn.value = !!v
  })
  watch(user, (u) => {
    isAdmin.value = !!(u?.is_superuser || u?.roles?.includes('admin'))
  })

  function loadUser(): UserInfo | null {
    try {
      const raw = localStorage.getItem(USER_KEY)
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  }

  function saveUser(u: UserInfo) {
    user.value = u
    localStorage.setItem(USER_KEY, JSON.stringify(u))
  }

  async function login(username: string, password: string, remember = true) {
    localStorage.setItem(REMEMBER_KEY, remember ? '1' : '0')
    // Mock 认证模式: 跳过真实后端，直接注入虚拟 token
    if (MOCK_AUTH) {
      console.warn('[mock-auth] 已启用 Mock 认证模式，登录绕过后端 API')
      token.value = MOCK_TOKEN
      refreshToken.value = MOCK_TOKEN
      localStorage.setItem(TOKEN_KEY, MOCK_TOKEN)
      localStorage.setItem(REFRESH_KEY, MOCK_TOKEN)
      saveUser(MOCK_USER)
      return
    }
    const res: TokenResponse = await request.post('/api/auth/login', { username, password })
    token.value = res.access_token
    refreshToken.value = res.refresh_token
    localStorage.setItem(TOKEN_KEY, res.access_token)
    localStorage.setItem(REFRESH_KEY, res.refresh_token)
    saveUser(res.user)
  }

  async function fetchUser() {
    if (MOCK_AUTH) {
      saveUser(MOCK_USER)
      return
    }
    try {
      const u: UserInfo = await request.get('/api/auth/me')
      saveUser(u)
    } catch {
      logout()
    }
  }

  async function tryRefresh(): Promise<boolean> {
    if (!refreshToken.value) return false
    if (MOCK_AUTH) return true
    try {
      const res: TokenResponse = await request.post('/api/auth/refresh', {
        refresh_token: refreshToken.value,
      })
      token.value = res.access_token
      refreshToken.value = res.refresh_token
      localStorage.setItem(TOKEN_KEY, res.access_token)
      localStorage.setItem(REFRESH_KEY, res.refresh_token)
      saveUser(res.user)
      return true
    } catch {
      logout()
      return false
    }
  }

  function logout() {
    token.value = ''
    refreshToken.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(REFRESH_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, refreshToken, user, isLoggedIn, isAdmin, login, fetchUser, tryRefresh, logout }
})
