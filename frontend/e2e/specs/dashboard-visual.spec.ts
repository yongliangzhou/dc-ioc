import { test, expect, type Page } from '@playwright/test'
import { installApiMocks } from '../fixtures/mockApi'

/**
 * 阶段 2 视觉回归：4 个总览标杆页 × 2 主题 × 4 档视口 = 32 组。
 *
 * 检查项（docs/design/06_ROADMAP.md §3.2）：
 *  1. P0 指标行可见（.metric-card 首屏可见）
 *  2. 无横向滚动（documentElement 不溢出）
 *  3. 入口卡不重叠（.entry-card 两两矩形无交集）
 *  4. 亮色主题正文对比度 ≥ 4.5:1（WCAG AA）
 *
 * 与 smoke.spec.ts 一样不依赖后端：复用 fixtures/mockApi.ts 的 API 桩。
 */

const PAGES = [
  { name: 'Power', path: '/monitor/power' },
  { name: 'Network', path: '/monitor/net' },
  { name: 'Security', path: '/monitor/security' },
  { name: 'Hvac', path: '/monitor/hvac' },
] as const

const THEMES = ['dark', 'light'] as const

const VIEWPORTS = [
  { name: '375', width: 375, height: 812 },
  { name: '768', width: 768, height: 1024 },
  { name: '1024', width: 1024, height: 768 },
  { name: '1440', width: 1440, height: 900 },
] as const

function fakeJwt(): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(JSON.stringify({ sub: 'admin', exp: Math.floor(Date.now() / 1000) + 3600 }))
  return `${header}.${payload}.e2e-signature`
}

async function authenticate(page: Page): Promise<void> {
  await page.addInitScript(
    ({ token, user }) => {
      localStorage.setItem('dc_ioc_token', token)
      localStorage.setItem('dc_ioc_refresh', token)
      localStorage.setItem('dc_ioc_user', JSON.stringify(user))
      localStorage.setItem('dc_ioc_remember', '1')
    },
    { token: fakeJwt(), user: { username: 'admin', roles: ['admin'] } },
  )
}

async function applyTheme(page: Page, theme: 'dark' | 'light'): Promise<void> {
  await page.evaluate((value) => {
    document.documentElement.dataset.theme = value
    localStorage.setItem('dcioc-theme', value)
  }, theme)
}

interface Metrics {
  overflow: number
  overflowEls: string[]
  overlapping: boolean
  cardCount: number
  contrast: number
}

/** 在浏览器内一次性测量四项布局/可访问性指标，避免多次往返。 */
async function measure(page: Page): Promise<Metrics> {
  return page.evaluate(() => {
    const overflow = Math.max(
      0,
      document.documentElement.scrollWidth - document.documentElement.clientWidth,
    )
    const clientWidth = document.documentElement.clientWidth
    const overflowEls = Array.from(document.querySelectorAll('body *'))
      .filter((el) => el.getBoundingClientRect().right > clientWidth + 1)
      .slice(0, 6)
      .map((el) => {
        const cls =
          typeof el.className === 'string' ? el.className.trim().split(/\s+/).join('.') : ''
        return `${el.tagName.toLowerCase()}${cls ? '.' + cls : ''}@${Math.round(el.getBoundingClientRect().right)}`
      })

    const cards = Array.from(document.querySelectorAll('.entry-card')).map((el) =>
      el.getBoundingClientRect(),
    )
    let overlapping = false
    for (let i = 0; i < cards.length && !overlapping; i += 1) {
      for (let j = i + 1; j < cards.length; j += 1) {
        const a = cards[i]
        const b = cards[j]
        const w = Math.min(a.right, b.right) - Math.max(a.left, b.left)
        const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top)
        if (w > 1 && h > 1) {
          overlapping = true
          break
        }
      }
    }

    const parse = (value: string): [number, number, number] | null => {
      const hex = value.trim().match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i)
      if (hex) {
        const raw =
          hex[1].length === 3
            ? hex[1]
                .split('')
                .map((c) => c + c)
                .join('')
            : hex[1]
        return [
          parseInt(raw.slice(0, 2), 16),
          parseInt(raw.slice(2, 4), 16),
          parseInt(raw.slice(4, 6), 16),
        ]
      }
      const rgb = value.trim().match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/i)
      return rgb ? [Number(rgb[1]), Number(rgb[2]), Number(rgb[3])] : null
    }
    const luminance = (rgb: [number, number, number]): number => {
      const [r, g, b] = rgb.map((v) => {
        const s = v / 255
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4
      })
      return 0.2126 * r + 0.7152 * g + 0.0722 * b
    }

    const rootStyle = getComputedStyle(document.documentElement)
    const heading = document.querySelector('.view-head h1')
    const fg =
      parse(heading ? getComputedStyle(heading).color : '') ??
      parse(rootStyle.getPropertyValue('--txt-strong'))
    const bg =
      parse(rootStyle.getPropertyValue('--bg')) ??
      parse(getComputedStyle(document.body).backgroundColor)
    let contrast = 0
    if (fg && bg) {
      const l1 = luminance(fg)
      const l2 = luminance(bg)
      contrast = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05)
    }

    return { overflow, overflowEls, overlapping, cardCount: cards.length, contrast }
  })
}

test.beforeEach(async ({ page }) => {
  await installApiMocks(page)
  await authenticate(page)
})

for (const target of PAGES) {
  test(`${target.name} 标杆页: 2 主题 × 4 视口视觉回归`, async ({ page }) => {
    // 8 组 goto + 测量累计远超 Playwright 默认 30s 测试超时，需按用例放大
    test.setTimeout(180_000)
    for (const theme of THEMES) {
      for (const viewport of VIEWPORTS) {
        await page.setViewportSize({ width: viewport.width, height: viewport.height })
        await page.goto(target.path, { waitUntil: 'domcontentloaded' })
        await applyTheme(page, theme)
        // 并发跑全套时 Vite 首次按需编译多个路由模块，给足 20s 窗口
        await expect(page.locator('.view-head h1')).toBeVisible({ timeout: 20_000 })
        await expect(page.locator('.metric-card').first()).toBeVisible({ timeout: 20_000 })

        const m = await measure(page)
        const label = `${target.name} / ${theme} / ${viewport.name}`
        expect(
          m.overflow,
          `${label}: 横向滚动 ${m.overflow}px, 溢出元素 ${m.overflowEls.join(' | ') || 'none'}`,
        ).toBeLessThanOrEqual(1)
        expect(m.overlapping, `${label}: 入口卡重叠`).toBe(false)
        expect(m.cardCount, `${label}: 入口卡数量`).toBeGreaterThan(0)
        if (theme === 'light') {
          expect(
            m.contrast,
            `${label}: 亮色正文对比度 ${m.contrast.toFixed(2)}`,
          ).toBeGreaterThanOrEqual(4.5)
        }
        // 标杆页截图（阶段 2 出口人工确认用）：CAPTURE=1 时才写文件，CI 不产生产物
        if (viewport.name === '1440' && process.env.CAPTURE === '1') {
          await page.screenshot({
            path: `visual-baseline/${target.name.toLowerCase()}-${theme}-1440.png`,
            fullPage: true,
          })
        }
        if (theme === 'dark' && viewport.name === '1440') {
          // 阶段 2 验收: 任意两张入口卡的指标组合不相同
          const combos = await page.evaluate(() =>
            Array.from(document.querySelectorAll('.entry-card')).map((card) =>
              Array.from(card.querySelectorAll('.kvs .k'))
                .map((k) => k.textContent?.trim() ?? '')
                .join('|'),
            ),
          )
          expect(
            new Set(combos).size,
            `${target.name}: 入口卡指标组合重复 ${combos.join(' / ')}`,
          ).toBe(combos.length)
        }
      }
    }
  })
}
