import request from '@/api/request'

/** 阶段四 · 前端插件清单消费层。
 *
 * 后端 `GET /api/plugins/manifest` 为唯一注册源; 接口不可达时回退内置清单,
 * 保证导航在任何情况下都不会变空 (ADR-0005 的离线兜底约束)。
 */
export interface PluginItem {
  id: string
  group: string
  path: string
  icon: string
  i18nKey: string
  requiredRoles: string[]
  enabled: boolean
}

export interface NavItemLike {
  path: string
  title: string
  ico: string
}
export interface NavGroupLike {
  id: string
  title: string
  items: NavItemLike[]
}

/** 与后端 BUILTIN_PLUGINS 保持一致 (后端不可达时使用)。 */
export const FALLBACK_MANIFEST: PluginItem[] = [
  {
    id: 'cmdb-ci-relations',
    group: 'asset',
    path: '/ops/ci-relations',
    icon: 'Cable',
    i18nKey: 'nav.ciRelations',
    requiredRoles: ['admin', 'operator'],
    enabled: true,
  },
  {
    id: 'ipam',
    group: 'asset',
    path: '/ops/ipam',
    icon: 'Globe',
    i18nKey: 'nav.ipam',
    requiredRoles: ['admin', 'operator'],
    enabled: true,
  },
  {
    id: 'asset-business',
    group: 'asset',
    path: '/ops/asset-business',
    icon: 'ClipboardList',
    i18nKey: 'nav.assetBusiness',
    requiredRoles: ['admin', 'operator'],
    enabled: true,
  },
  {
    id: 'discovery',
    group: 'platform',
    path: '/ops/discovery',
    icon: 'Radio',
    i18nKey: 'nav.discovery',
    requiredRoles: ['admin', 'operator'],
    enabled: true,
  },
  {
    id: 'custom-fields',
    group: 'platform',
    path: '/ops/custom-fields',
    icon: 'Settings2',
    i18nKey: 'nav.customFields',
    requiredRoles: ['admin', 'operator'],
    enabled: true,
  },
]

export async function fetchPluginManifest(): Promise<PluginItem[]> {
  try {
    const r = await request.get<{ plugins?: PluginItem[] }>('/api/plugins/manifest')
    const list = r.data?.plugins
    if (!Array.isArray(list)) return FALLBACK_MANIFEST
    return list.filter((p) => p.enabled !== false)
  } catch (err) {
    console.warn('[plugins] 清单接口不可达, 回退内置清单:', err)
    return FALLBACK_MANIFEST
  }
}

/** 把插件项按 group 合并进静态导航; 同 path 静态优先 (去重, 防止死链按钮)。 */
export function mergePluginNav<T extends NavGroupLike>(
  groups: T[],
  plugins: PluginItem[],
  translate: (key: string) => string,
): T[] {
  const byGroup = new Map<string, PluginItem[]>()
  for (const p of plugins) {
    if (!p.enabled || !p.path || !p.group) continue
    const list = byGroup.get(p.group) || []
    list.push(p)
    byGroup.set(p.group, list)
  }
  return groups.map((g) => {
    const extras = byGroup.get(g.id) || []
    if (!extras.length) return g
    const existing = new Set(g.items.map((i) => i.path))
    const added: NavItemLike[] = extras
      .filter((p) => !existing.has(p.path))
      .map((p) => ({ path: p.path, title: translate(p.i18nKey), ico: p.icon }))
    return { ...g, items: [...g.items, ...added] } as T
  })
}
