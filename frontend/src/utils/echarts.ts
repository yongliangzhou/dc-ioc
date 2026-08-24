/**
 * ECharts 按需引入中心 (P-01)
 * 仅注册项目中实际使用的图表/组件, 避免 `import * as echarts` 全量打包。
 * 新增图表类型时: 在此处补 use([...]), 并确保 build 后逐页点验渲染。
 */
import * as echarts from 'echarts/core'
import {
  LineChart,
  BarChart,
  PieChart,
  GaugeChart,
  HeatmapChart,
  BoxplotChart,
  ScatterChart,
} from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  MarkLineComponent,
  VisualMapComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([
  LineChart,
  BarChart,
  PieChart,
  GaugeChart,
  HeatmapChart,
  BoxplotChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
  MarkLineComponent,
  VisualMapComponent,
  CanvasRenderer,
])

export default echarts
// 常用类型仅作类型标注, 编译期擦除, 不会增大产物体积
export type { EChartsType } from 'echarts/core'
export type {
  EChartsOption,
  YAXisComponentOption,
  SeriesOption,
  LineSeriesOption,
  DefaultLabelFormatterCallbackParams,
} from 'echarts'
