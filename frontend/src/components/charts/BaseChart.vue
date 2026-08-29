<template>
  <div ref="el" class="base-chart" :class="{ clickable }" :style="{ height, width }"></div>
</template>

<script setup lang="ts">
import { ref, toRef, watch } from 'vue'
import { useECharts, type EChartsOption } from '@/hooks/useECharts'

const props = withDefaults(
  defineProps<{
    option: EChartsOption | Record<string, unknown>
    height?: string
    width?: string
    theme?: string | object
    /** 开启数据点点击（默认关闭，不影响既有用法） */
    clickable?: boolean
  }>(),
  { height: '260px', width: '100%', clickable: false },
)

export interface ChartPointClick {
  seriesName: string
  seriesIndex: number
  /** 数据点在 x 轴上的下标 */
  dataIndex: number
  /** x 轴类目值（饼图为扇区名） */
  name: string
  value: number
}

const emit = defineEmits<{
  /** 仅在 clickable=true 时触发 */
  pointClick: [payload: ChartPointClick]
}>()

const el = ref<HTMLElement | null>(null)
const { chart, resize } = useECharts(el, toRef(props, 'option'), { theme: props.theme })

/**
 * 绑定数据点点击（opt-in）。
 * 主题切换时 useECharts 会重建实例，故用 watch 重新绑定，避免事件丢失。
 */
watch(
  chart,
  (c, prev) => {
    if (prev) prev.off('click')
    if (!c || !props.clickable) return
    c.on('click', (raw: unknown) => {
      const p = raw as {
        seriesName?: string
        seriesIndex?: number
        dataIndex?: number
        name?: string
        value?: number | string
      }
      emit('pointClick', {
        seriesName: p.seriesName ?? '',
        seriesIndex: p.seriesIndex ?? 0,
        dataIndex: p.dataIndex ?? 0,
        name: String(p.name ?? ''),
        value: Number(p.value ?? 0),
      })
    })
  },
  { immediate: true },
)

defineExpose({ chart, resize })
</script>

<style scoped>
.base-chart {
  display: block;
}
.clickable {
  cursor: pointer;
}
</style>
