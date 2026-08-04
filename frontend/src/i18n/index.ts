import { createI18n } from 'vue-i18n'

const LOCALE_KEY = 'dc-ioc-locale'

/**
 * 语言包懒加载表: 动态 import 让 Vite 把各 JSON 切成独立 chunk,
 * 主包不再内联 zh-CN(54KB) + en-US(57KB), 仅按需加载当前语言。
 */
const loaders: Record<string, () => Promise<{ default: Record<string, unknown> }>> = {
  'zh-CN': () => import('./locales/zh-CN.json'),
  'en-US': () => import('./locales/en-US.json'),
}

function getSavedLocale(): string {
  try {
    const v = localStorage.getItem(LOCALE_KEY) ?? 'zh-CN'
    return v in loaders ? v : 'zh-CN'
  } catch {
    return 'zh-CN'
  }
}

export function setLocale(locale: string) {
  try {
    localStorage.setItem(LOCALE_KEY, locale)
  } catch {
    /* 忽略 */
  }
}

export const supportedLocales = [
  { code: 'zh-CN', label: '中文' },
  { code: 'en-US', label: 'English' },
] as const

const i18n = createI18n({
  legacy: false,
  locale: getSavedLocale(),
  fallbackLocale: 'zh-CN',
  messages: {}, // 语言包全部懒加载, 见 loadLocaleMessages
  missingWarn: false,
  fallbackWarn: false,
})

const _loaded = new Set<string>()

/** 按需加载语言包并注册到 i18n (幂等)。 */
export async function loadLocaleMessages(code: string): Promise<void> {
  if (_loaded.has(code) || !loaders[code]) return
  const mod = await loaders[code]()
  i18n.global.setLocaleMessage(code, mod.default as never)
  _loaded.add(code)
}

/** 切换语言: 先确保目标语言包 (及 zh-CN 兜底) 已加载, 再切换并持久化。 */
export async function switchLocale(code: string): Promise<void> {
  if (!loaders[code]) return
  await loadLocaleMessages(code)
  if (code !== 'zh-CN') {
    // en-US 覆盖不全时 fallback 到 zh-CN, 同为懒加载 chunk
    await loadLocaleMessages('zh-CN').catch(() => {
      /* 兜底缺失可容忍 */
    })
  }
  ;(i18n.global.locale as unknown as { value: string }).value = code
  setLocale(code)
}

/** 应用启动: 加载初始语言包 (main.ts 应 await 后再挂载, 避免闪 key)。 */
export async function setupI18nMessages(): Promise<void> {
  await switchLocale(getSavedLocale())
}

export default i18n
