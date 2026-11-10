import { describe, expect, it } from 'vitest'
import {
  emptyViewState,
  normalizeView,
  normalizeViewState,
  parseViews,
  removeView,
  renameView,
  upsertView,
  viewKind,
  viewStorageKey,
  MAX_VIEWS,
  type FilterView,
} from '../useViewPreferences'

const view = (id: string, name = `视图 ${id}`): FilterView => ({
  id,
  name,
  filters: { status: 'open', level: 2 },
  columns: [{ key: 'name', visible: true, order: 0 }],
})

describe('useViewPreferences 纯函数', () => {
  it('空状态与非法输入', () => {
    expect(emptyViewState()).toEqual({ views: [], defaultId: null })
    expect(normalizeViewState(null)).toEqual(emptyViewState())
    expect(normalizeViewState({ views: 'not-json' })).toEqual(emptyViewState())
    expect(normalizeView({ id: '', name: 'x' })).toBeNull()
    expect(normalizeView({ id: 'a', name: '   ' })).toBeNull()
  })

  it('后端 JSON 字符串与本地数组两种形态都能解析', () => {
    const arr = [view('a')]
    expect(parseViews(JSON.stringify(arr))).toEqual(arr)
    expect(parseViews(arr)).toEqual(arr)
    expect(parseViews('{{')).toEqual([])
    const state = normalizeViewState({ views: JSON.stringify(arr), defaultId: 'a' })
    expect(state.views).toHaveLength(1)
    expect(state.defaultId).toBe('a')
  })

  it('非法字段被丢弃, unknown / 超长不进入视图', () => {
    const state = normalizeViewState({
      views: [
        {
          id: 'ok',
          name: '正常',
          filters: { a: 'x', b: {}, c: 3, d: null },
          columns: [{ key: 'x' }],
        },
        { id: 'bad', name: '' },
        42,
      ],
      defaultId: 'missing',
    })
    expect(state.views).toHaveLength(1)
    expect(state.views[0].filters).toEqual({ a: 'x', c: 3 })
    expect(state.views[0].columns[0].visible).toBe(true)
    expect(state.defaultId).toBe('ok')
  })

  it('upsert 新增/覆盖, 超过上限丢弃最旧', () => {
    let state = upsertView(emptyViewState(), view('a'))
    expect(state.defaultId).toBe('a')
    state = upsertView(state, view('b'))
    expect(state.views.map((v) => v.id)).toEqual(['a', 'b'])
    state = upsertView(state, { ...view('a'), name: '改名' })
    expect(state.views).toHaveLength(2)
    expect(state.views[0].name).toBe('改名')
    for (let i = 0; i < MAX_VIEWS + 4; i++) state = upsertView(state, view(`x${i}`))
    expect(state.views).toHaveLength(MAX_VIEWS)
    expect(state.views.some((v) => v.id === 'a')).toBe(false)
  })

  it('remove 删除默认视图后自动指向第一个, rename 空名不改', () => {
    let state = upsertView(upsertView(emptyViewState(), view('a')), view('b'))
    state = removeView(state, 'a')
    expect(state.views.map((v) => v.id)).toEqual(['b'])
    expect(state.defaultId).toBe('b')
    expect(renameView(state, 'b', '   ').views[0].name).toBe('视图 b')
    expect(renameView(state, 'b', '新的名字').views[0].name).toBe('新的名字')
  })

  it('kind 在 String(64) 内, 超长仍唯一且 storageKey 无非法字符', () => {
    const short = viewKind('equipment', 'admin')
    expect(short).toBe('fv:admin:equipment')
    const longUser = 'u'.repeat(80)
    const longPage = 'p'.repeat(80)
    const a = viewKind(longPage, longUser)
    const b = viewKind(longPage, longUser + 'x')
    expect(a.length).toBeLessThanOrEqual(64)
    expect(a).not.toBe(b)
    expect(viewKind('a/b:c?', 'x y')).not.toMatch(/[/\s?]/)
    expect(viewStorageKey('equipment', 'admin')).toBe('dc_ioc_filter_views_fv_admin_equipment')
  })
})
