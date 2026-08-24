import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'
import { useAuthStore } from '@/stores/modules/auth'
import { usePermission } from '@/hooks/usePermission'

describe('usePermission', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('admin 仅管理员可执行', () => {
    const auth = useAuthStore()
    auth.user = { roles: ['admin'] } as never
    auth.isAdmin = true
    auth.isLoggedIn = true
    const { can } = usePermission()
    expect(can('admin')).toBe(true)
    expect(can('write')).toBe(true)
  })

  it('访客 viewer 无 write/admin 权限', () => {
    const auth = useAuthStore()
    auth.user = { roles: ['viewer'] } as never
    auth.isAdmin = false
    auth.isLoggedIn = true
    const { can, denyTip } = usePermission()
    expect(can('admin')).toBe(false)
    expect(can('write')).toBe(false)
    expect(denyTip('write')).toBe('当前账号无操作权限')
  })

  it('未登录时 admin 提示登录', () => {
    const auth = useAuthStore()
    auth.user = null
    auth.isAdmin = false
    auth.isLoggedIn = false
    const { can, denyTip } = usePermission()
    expect(can('admin')).toBe(false)
    expect(denyTip('admin')).toBe('请先登录')
  })

  it('普通运维可 write 但不可 admin', () => {
    const auth = useAuthStore()
    auth.user = { roles: ['operator'] } as never
    auth.isAdmin = false
    auth.isLoggedIn = true
    const { can, denyTip } = usePermission()
    expect(can('write')).toBe(true)
    expect(can('admin')).toBe(false)
    expect(denyTip('admin')).toBe('需要管理员权限')
  })
})
