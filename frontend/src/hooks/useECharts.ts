import { onBeforeUnmount, onMounted, shallowRef, watch, type Ref } from 'vue'
import echarts, { type EChartsOption } from '@/utils/echarts'
import { themeMode } from '@/theme'

export type { EChartsOption }

/**
 * 通用 ECharts 组合式函数
 * - 初始化/更新图表
 * - ResizeObserver + window.resize 双重自适应
 * - 组件卸载自动 dispose, 防止内存泄漏
 *
 * @param elRef   图表容器 ref
 * @param option  图表配置 (响应式, 深度监听后自动 setOption)
 * @param opts    可选: theme / renderer / 是否监听 resize
 */
export function useECharts(
  elRef: Ref<HTMLElement | null>,
  option: Ref<EChartsOption | Record<string, unknown>>,
  opts: { theme?: string | object; renderer?: 'canvas' | 'svg'; autoResize?: boolean } = {},
) {
  const chart = shallowRef<echarts.ECharts | null>(null)
  const { theme, renderer = 'canvas', autoResize = true } = opts
  let ro: ResizeObserver | null = null
  let disposed = false

  // 图表就绪判定: 实例存在 且 DOM 仍挂载在文档中 (防止脱挂 DOM 触发 ECharts 内部 parentNode 空引用)
  const isReady = (): boolean =>
    !disposed && !!chart.value && !!elRef.value && elRef.value.isConnected

  const resize = () => {
    if (isReady()) {
      try {
        chart.value!.resize()
      } catch {
        /* 脱挂 DOM 静默跳过 */
      }
    }
  }

  const setOption = (opt: EChartsOption, notMerge = true) => {
    if (isReady()) {
      try {
        chart.value!.setOption(opt, { notMerge })
      } catch {
        /* 脱挂 DOM 静默跳过 */
      }
    }
  }

  // 未显式传 theme 时跟随全局主题: 暗色用 ECharts 内置 'dark' 主题, 亮色用默认主题。
  // options.ts 生成的配置均带 backgroundColor:'transparent', 不会出现 'dark' 主题的深色底。
  const resolveTheme = (): string | object | undefined =>
    theme ?? (themeMode.value === 'dark' ? 'dark' : undefined)

  const initChart = () => {
    if (!elRef.value || disposed) return
    try {
      chart.value = echarts.init(elRef.value, resolveTheme(), { renderer })
      // 仅在配置非空时初始化渲染 (避免空 {} 触发 ECharts 异常)
      if (option.value && Object.keys(option.value).length) {
        chart.value.setOption(option.value, { notMerge: true })
      }
    } catch {
      // DOM 暂不可用或尺寸为 0 时跳过, 等待下次 setOption/resize
      chart.value = null
    }
  }

  // 全局主题切换 -> 以新主题重建实例 (echarts 主题只能 init 时指定)
  watch(themeMode, () => {
    if (disposed || theme) return // 显式指定 theme 的图表不跟随
    const inst = chart.value
    chart.value = null
    if (inst) {
      try {
        inst.dispose()
      } catch {
        /* ignore */
      }
    }
    initChart()
  })

  onMounted(() => {
    if (!elRef.value || disposed) return
    initChart()
    if (!chart.value) return

    if (autoResize) {
      // 容器尺寸变化 (布局/侧栏伸缩) 自适应
      if (typeof ResizeObserver !== 'undefined') {
        ro = new ResizeObserver(() => resize())
        ro.observe(elRef.value)
      }
      window.addEventListener('resize', resize)
    }
  })

  // 配置变化 -> 增量更新 (已卸载/脱挂 DOM 时静默跳过)
  watch(
    option,
    (val) => {
      if (val && Object.keys(val).length) setOption(val)
    },
    { deep: true },
  )

  onBeforeUnmount(() => {
    disposed = true
    ro?.disconnect()
    ro = null
    window.removeEventListener('resize', resize)
    // 关键修复: 在 dispose 之前先 clear() 取消挂起的渲染帧, 并将 dispose 推迟到下一个
    // requestAnimationFrame 执行。这样 zrender 内部当前已在途的动画帧会先于 dispose 跑完
    // (此时 _dom 仍有效), 避免 "chart.getDom().getBoundingClientRect()" 在 _dom 被置空后
    // 对 null 访问而抛错 (该错误会级联导致 vue-router 卸载清理时 "reading 'component'" 异常)。
    const inst = chart.value
    chart.value = null
    if (inst) {
      // 同步 clear(): 此刻 DOM 仍在挂载, 可安全取消挂起的渲染/动画帧,
      // 避免 zrender 内部在途 RAF 后续访问已置空的 _dom。
      try {
        inst.clear()
      } catch {
        /* ignore */
      }
      // dispose 推迟到下一帧, 确保前面的渲染帧先跑完再释放实例。
      requestAnimationFrame(() => {
        try {
          inst.dispose()
        } catch {
          /* ignore */
        }
      })
    }
  })

  return { chart, setOption, resize }
}
