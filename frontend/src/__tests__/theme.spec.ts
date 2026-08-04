import { describe, it, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'

// jsdom 无 canvas: mock echarts 避免 zrender 异步渲染帧抛未处理异常
vi.mock('echarts', () => ({
  init: vi.fn(() => ({
    setOption: vi.fn(),
    resize: vi.fn(),
    dispose: vi.fn(),
    clear: vi.fn(),
  })),
  registerTheme: vi.fn(),
}))
import { themeMode, toggleTheme, applyTheme } from '@/theme'
import { chartVars, lineOption } from '@/components/charts/options'
import BaseChart from '@/components/charts/BaseChart.vue'

beforeEach(() => {
  themeMode.value = 'dark'
  applyTheme()
})

describe('主题切换', () => {
  it('toggleTheme 切换 dark/light 并同步 html[data-theme] 与 localStorage', async () => {
    expect(document.documentElement.dataset.theme).toBe('dark')
    toggleTheme()
    await nextTick()
    expect(themeMode.value).toBe('light')
    expect(document.documentElement.dataset.theme).toBe('light')
    expect(localStorage.getItem('dcioc-theme')).toBe('light')
  })

  it('chartVars 随主题返回不同取色', () => {
    const dark = chartVars()
    toggleTheme()
    const light = chartVars()
    expect(dark.axisLabel).not.toBe(light.axisLabel)
    expect(dark.tooltipBg).not.toBe(light.tooltipBg)
  })

  it('lineOption 输出使用当前主题调色板', () => {
    const darkOpt = lineOption(['a'], [{ name: 's', data: [1] }]) as any
    toggleTheme()
    const lightOpt = lineOption(['a'], [{ name: 's', data: [1] }]) as any
    expect(darkOpt.color).not.toEqual(lightOpt.color)
    expect(darkOpt.backgroundColor).toBe('transparent')
  })
})

describe('BaseChart 组件 (@vue/test-utils)', () => {
  it('jsdom 下挂载不抛错并渲染容器 (echarts init 失败被安全兜底)', () => {
    const wrapper = mount(BaseChart, {
      props: { option: lineOption(['a', 'b'], [{ name: 's', data: [1, 2] }]), height: '120px' },
    })
    const el = wrapper.find('.base-chart')
    expect(el.exists()).toBe(true)
    expect(el.attributes('style')).toContain('height: 120px')
    wrapper.unmount() // 卸载亦不抛错
  })
})
