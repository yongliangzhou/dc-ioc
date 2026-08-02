# DC-IOC Platform 16 模块 UI 重做 — TODO 清单

> 总体目标：按"界面展示建议"统一重做 16 个监控模块 + 驾驶舱 + 告警中心的前端 UI，建立统一组件库和交互规范。

---

## 📦 第一批：制冷系统 3 模块（示范批次）

> 目标：跑通"新 UI 组件库 + 统一交互 + 真实数据驱动 + 告警集成 + 驾驶舱联动"的完整范式

---

### 1.0 基础设施搭建（所有批次共用）

- [x] **1.0.1** 新建 `src/components/monitor/KpiCard.vue` — 统一 KPI 指标卡片
- [x] **1.0.2** 新建 `src/components/monitor/StatusBadge.vue` — 状态徽章（在线/离线/故障）
- [x] **1.0.3** 新建 `src/components/monitor/AlarmBadge.vue` — 告警等级徽章（紧急红/重要橙/提示蓝）
- [x] **1.0.4** 新建 `src/components/monitor/ProgressGauge.vue` — 环形进度仪表盘（SOC/负载率等）
- [x] **1.0.5** 新建 `src/components/monitor/DeviceCard.vue` — 设备卡片（含状态、参数、控制入口）
- [x] **1.0.6** 新建 `src/components/monitor/GroupCard.vue` — 分组卡片（折叠面板 + 子设备列表）
- [x] **1.0.7** 新建 `src/components/monitor/TrendChart.vue` — 统一趋势图（封装 ECharts + 主题 + 时间切换）
- [x] **1.0.8** 新建 `src/components/monitor/TimeRangePicker.vue` — 24h/7d/30d 时间范围切换器
- [x] **1.0.9** 新建 `src/components/monitor/DeviceTable.vue` — 设备参数表格（排序/筛选）
- [x] **1.0.10** 新建 `src/components/monitor/HeatmapView.vue` — 热力图容器
- [x] **1.0.11** 新建 `src/components/monitor/QuickControl.vue` — 远程控制按钮组
- [x] **1.0.12** 新建 `src/components/monitor/EmptyState.vue` — 空数据占位
- [x] **1.0.13** 新建 `src/components/monitor/SkeletonCard.vue` — 骨架屏
- [x] **1.0.14** 新建 `src/components/monitor/index.ts` — 统一导出
- [x] **1.0.15** 新建 `src/assets/echarts-theme.ts` — 统一 ECharts 深色主题（颜色板、轴样式、tooltip）
- [x] **1.0.16** 修复字段映射 — hvac.ts 类型定义和 mapXxx 均已正确，缺陷在旧版 HvacChiller.vue 中错误字段访问（code→id / loadPercent→load / temperatureIn→evapT 等），将在页面重写(1.1/1.2/1.3)时一并修复
- [x] **1.0.17** 修改侧边栏 `src/layouts/DefaultLayout.vue`：emoji 图标替换为 lucide 内联 SVG（36 个菜单项全部替换，新建 `NavIcon.vue` 组件）
- [x] **1.0.18** 编译验证：`npx vue-tsc --noEmit` 无类型错误 ✅

---

### 1.1 冷源系统页面重做

**文件**: `src/views/monitor/HvacChiller.vue`

- [x] **1.1.1** 系统组态图：SVG 绘制冷水机组↔冷却塔↔冷却泵↔冷冻泵↔板换连接图
- [x] **1.1.2** 关键参数仪表盘：冷冻水供/回水温、冷却水供/回水温、瞬时冷量、COP（KpiCard + ProgressGauge）
- [x] **1.1.3** 能效分析区：分时段供冷量 + 分时段能效 + 历史负荷曲线 + COP 曲线（多个 TrendChart + ECharts scatter）
- [x] **1.1.4** 能耗趋势区：高温箱/中温箱/负荷占比（柱状图 + 饼图）
- [x] **1.1.5** 故障告警：实时告警列表（getActiveAlarms 筛选 hvac 域，AlarmBadge + StatusBadge）
- [x] **1.1.6** 设备控制入口：组态图中节点可点击跳转，GroupCard 内嵌 QuickControl（启停/模式/温度设定）
- [x] **1.1.7** 数据接入：getChillerPlant() + getChillerTrends() + getActiveAlarms() + 30s 自动刷新
- [x] **1.1.8** 编译验证无类型错误 ✅ — vue-tsc exitCode 0

---

### 1.2 空调末端页面重做

**文件**: `src/views/monitor/HvacCrac.vue`

- [x] **1.2.1** KPI Row 1 × 4（设备总数/运行待机故障/漏水告警/室外参照温度）+ Row 2 × 4（送风/回风/供水/压差）
- [x] **1.2.2** 设备全景列表：DeviceTable（编号/包间/类型/状态/送风T/回风T/风机/风阀/水阀/功率/滤网/模式）
- [x] **1.2.3** 包间温度热力图：HeatmapView（包间×传感器类型：均温/热通道/冷通道/露点）
- [x] **1.2.4** 包间设备归集：GroupCard × N（KpiCard 环境传感器 8 项 + DeviceTable 精密空调 + DeviceTable 列间空调 + 新风/恒湿辅助 + 漏水检测 + QuickControl）
- [x] **1.2.5** 群控策略面板：恒湿机联控 + 正压送风 + 二次泵策略（3 栏展示）
- [x] **1.2.6** 趋势诊断分析：ΔT Integral/Filter ΔP Slope/SHR/SupplyVsCabinet(周期切换)/FanVsStatic/ValveVsΔT/Superheat（7 个 TrendChart）
- [x] **1.2.7** 远程控制：包间温度设定 QuickControl
- [x] **1.2.8** 数据接入：getCrac() + getCracTrends() + mapCracRoomGroups() + getActiveAlarms() + 30s 自动刷新
- [x] **1.2.9** 编译验证 ✅ — vue-tsc exitCode 0

---

### 1.3 液冷系统页面重做

**文件**: `src/views/monitor/HvacLiquid.vue`

- [x] **1.3.1** 系统概览 KPI（3 行 × 4）：系统模式/室外温湿/制冷能力+PUE / 一次侧4项/二次侧4项（12 张 KpiCard）
- [x] **1.3.2** 一次侧 CDU DeviceTable（14 列：进出温/换热效率/流量/压差/泵速泵功/阀门/漏检/运行时间）
- [x] **1.3.3** 二次侧 CDU DeviceTable + 冷板 GPU 节点 DeviceTable（GPU 温度列表）
- [x] **1.3.4** 分集水器双栏 DeviceTable（供水集管 × 回水集管，含温度/压力/流量/阀门）
- [x] **1.3.5** 漏水检测面板：漏水绳 DeviceTable + 漏水点 DeviceTable
- [x] **1.3.6** 冷却液品质 5 项 KpiCard（电导率/pH/缓蚀剂/乙二醇/颗粒）+ StatusBadge
- [x] **1.3.7** 排热系统 4 组 GroupCard：冷却塔风机 + 干冷器 + 排热水泵 + 余热回收（6 KpiCard）
- [x] **1.3.8** 群控策略 8 项卡片（设定点/乙二醇/电导率上限/漏水响应/冗余）+ 说明文案
- [x] **1.3.9** 趋势分析 4 个 TrendChart（温度/流量/ΔT/制冷+实际使用，数据来自 summary 内置 trend 数组）
- [x] **1.3.10** 数据接入：getLiquidCooling()（单次请求全量）+ getActiveAlarms() 过滤液冷相关 + 30s 刷新
- [x] **1.3.11** 编译验证 ✅ — vue-tsc exitCode 0

---

### 1.4 驾驶舱首页增强

**文件**: `src/views/overview/Index.vue`

- [x] **1.4.1** PUE KpiCard + TrendChart 30天 sparkline（30 点随机基准线）+24h trend 提示
- [x] **1.4.2** KPI Row 6 卡统一为 KpiCard：PUE+sparkline / IT负载(bar) / 总负载(trend) / 制冷负载(status) / 在线率(bar+status) / 告警(AlarmBadge×3)
- [x] **1.4.3** 四大业务域健康度卡片：SVG CSS ring 图(暖通/电力/安防消防/数智运维各 1 环) + StatusBadge + 在线率+告警数
- [x] **1.4.4** 告警总数卡片：3 级 AlarmBadge (critical/warning/info) + 点击跳转告警中心 + 活跃告警 feed 列表（最多 8 条）
- [x] **1.4.5** 制冷域 KPI 入口 4 卡：KpiCard(COP/SHR/PUE贡献/自然冷却时)，点击跳转对应 hvac 子页面，数据来自 getHvacOverview()
- [x] **1.4.6** 校区总览卡片：StatusBadge 状态 + PUE/在线率/IT负载/告警 4 项，来自 getCampusComparison()
- [x] **1.4.7** 关键趋势 3×TrendChart(PUE&WUE/负载三线/在线率&可用性)，48h 模拟数据，30s 自动刷新
- [x] **1.4.8** 编译验证 ✅ — vue-tsc exitCode 0

---

### 1.5 告警中心增强

**文件**: `src/views/ops/Alarms.vue`

- [x] **1.5.1** 来源系统标签列：9 种彩色标签（冷源/空调/液冷/配电/消防/安防/网络/暖通/其他），带发光圆点+半透明边框，智能关键词匹配
- [x] **1.5.2** 统一使用 AlarmBadge 渲染告警等级（crit→critical, warn→warning, info→info），StatusBadge 渲染告警状态
- [x] **1.5.3** 关联设备快捷跳转列：根据来源系统匹配路由（冷源→/monitor/hvac/chiller 等），支持 deviceId 参数，点击触发 router.push
- [x] **1.5.4** Alarms.vue 新增 handleGoDevice 路由分发器（7 种系统→路由映射），@goDevice 事件绑定
- [x] **1.5.5** 编译验证 ✅ — vue-tsc exitCode 0

---

### 第一批验收标准

- [ ] 冷源系统：组态图可交互，KPI 卡片正常，7 个趋势图有数据
- [ ] 空调末端：设备列表可排序，热力图正确，群控面板可操作
- [ ] 液冷系统：SVG 流程图正确，GPU 温度矩阵正常
- [ ] 驾驶舱首页：4 大指标卡片正常，制冷域可下钻
- [ ] 告警中心：四等级告警接入，来源标签正确，关联设备可跳转
- [ ] 30s 自动刷新 + 手动刷新正常
- [ ] 侧边栏图标统一（lucide-icons 替代 emoji）
- [ ] 全部页面无 TypeScript 类型错误

---

## 📦 第二批：网络系统 4 模块

> 前置条件：第一批通过验收，统一组件库已稳定

---

### 2.1 核心交换机页面重做

**文件**: `src/views/monitor/NetworkSwitches.vue`

- [x] **2.1.1** SVG Spine-Leaf 拓扑：Spine-01/02 + Leaf-01/02 + Access-01 自动布局，连线粗细∝利用率(30~90%)，颜色分级(绿<55%→橙<85%→红)
- [x] **2.1.2** 新建 PortPanel.vue：48 端口 24×2 网格，点击展开详情 card，speed indicator(25G青/10G紫)
- [x] **2.1.3** 设备面板图：UP绿(#22c55e)/DOWN灰(#374151)/告警橙(#f59e0b)+pulse 动效，hover scale，选中 cyan ring
- [x] **2.1.4** 端口流量表 10 列：端口/状态(StatusBadge)/速率/入出利用率/实时流量/错包/丢包/收发光
- [x] **2.1.5** 系统资源仪表 KpiCard×4：CPU(32%)/内存(46%)/交换机总数(5台)/端口可用率(94%)
- [x] **2.1.6** 链路聚合面板 5 条 trunk：正常/降级状态，成员列表 + 利用率进度条
- [x] **2.1.7** 链路质量探测 Ping面板：Leaf/Access 各侧 RTT/抖动/丢包，StatusBadge，含 lossy 告警示例
- [x] **2.1.8** mock fallback：API 空 → 5 台 demo 交换机(Spine×2+Leaf×2+Access×1) + 240 端口
- [x] **2.1.9** 编译验证 ✅ — vue-tsc exitCode 0

---

### 2.2 路由器页面重做

**文件**: `src/views/monitor/NetworkRouters.vue`

- [ ] **2.2.1** 设备状态仪表盘（KpiCard × 4：CPU/内存/状态/温度）
- [ ] **2.2.2** 接口流量表格 + 趋势折线图（TrendChart）
- [ ] **2.2.3** 路由协议状态面板：BGP/OSPF 邻居状态
- [ ] **2.2.4** 会话统计仪表（并发连接数/新建速率）
- [ ] **2.2.5** 编译验证 + 预览验证

---

### 2.3 防火墙页面重做

**文件**: `src/views/monitor/NetworkFirewalls.vue`

- [ ] **2.3.1** 安全仪表盘：攻击类型分布饼图 + 阻断次数趋势图
- [ ] **2.3.2** 策略命中排行表
- [ ] **2.3.3** 并发连接数/新建速率 KPI 卡片
- [ ] **2.3.4** 系统资源利用（CPU/内存/磁盘）
- [ ] **2.3.5** 编译验证 + 预览验证

---

### 2.4 无线网络页面重做

**文件**: `src/views/monitor/NetworkWireless.vue`

- [ ] **2.4.1** AP 分布热力图：HeatmapView 渲染信号强度
- [ ] **2.4.2** AP 列表：DeviceTable（名称/状态/关联终端数/信道/流量）
- [ ] **2.4.3** 终端统计面板：总数 + 类型分布饼图
- [ ] **2.4.4** 信道干扰可视化
- [ ] **2.4.5** 编译验证 + 预览验证

---

### 第二批验收标准

- [ ] 交换机：Spine-Leaf 拓扑图正确渲染，端口面板交互正常
- [ ] 路由器：BGP/OSPF 邻居状态面板正常
- [ ] 防火墙：攻击类型分布图有数据，策略命中有排行
- [ ] 无线：信号热力图颜色梯度正确
- [ ] 全部无 TypeScript 类型错误

---

## 📦 第三批：供配电 4 模块 + 电池监控 1 模块

> 前置条件：第二批通过验收

---

### 3.1 10KV 中压配电页面重做

**文件**: `src/views/monitor/PowerHv.vue`

- [ ] **3.1.1** 电气一次系统图：SVG 绘制 10KV 配电一次图（2路进线 → 母线 → 各馈线回路）
- [ ] **3.1.2** 断路器/刀闸可交互节点：颜色=分合状态，点击查看详情
- [ ] **3.1.3** 进线监测 KPI：电压/电流/功率/功率因数/频率/电能（KpiCard × 6）
- [ ] **3.1.4** 电能质量：谐波柱状图 + 功率因数趋势（TrendChart）
- [ ] **3.1.5** 实时告警列表：过压/欠压/过流（AlarmBadge）
- [ ] **3.1.6** 历史事件查询表：保护动作/跳闸事件
- [ ] **3.1.7** 编译验证 + 预览验证

---

### 3.2 0.4KV 低压配电页面重做

**文件**: `src/views/monitor/PowerLv.vue`

- [ ] **3.2.1** 低压一次系统图 SVG + 备自投状态图（进线/母联/柴发进线开关动态监视）
- [ ] **3.2.2** 回路电参量表：DeviceTable（三相电压/电流/有功/无功/功率因数/频率）
- [ ] **3.2.3** 备自投切换状态可视化面板
- [ ] **3.2.4** 24h 相电流趋势曲线（TrendChart）
- [ ] **3.2.5** 电能统计报表
- [ ] **3.2.6** 编译验证 + 预览验证

---

### 3.3 柴发并机系统页面重做

**文件**: `src/views/monitor/PowerGenset.vue`

- [ ] **3.3.1** 并机系统拓扑图：多台柴油机组并联 + 并机母线 SVG
- [ ] **3.3.2** 机组状态面板：DeviceCard × N（运行/停机/故障/检修）
- [ ] **3.3.3** 并机参数面板：并联状态/负载分配比例/有功无功
- [ ] **3.3.4** 发电机参数 + 发动机参数（水温/油压/油位）（KpiCard）
- [ ] **3.3.5** 远程启停控制：QuickControl（启停/并机解列）
- [ ] **3.3.6** 编译验证 + 预览验证

---

### 3.4 燃油监控系统页面重做

**文件**: `src/views/monitor/PowerFuel.vue`

- [ ] **3.4.1** 油罐示意图：SVG 油罐 + 液位动画
- [ ] **3.4.2** 日/周/月燃油消耗趋势图（TrendChart）
- [ ] **3.4.3** 低油量预警面板
- [ ] **3.4.4** 续航时间预测仪表（ProgressGauge）
- [ ] **3.4.5** 补给记录表
- [ ] **3.4.6** 编译验证 + 预览验证

---

### 3.5 电池监控系统页面重做

**文件**: `src/views/monitor/PowerBattery.vue`

- [ ] **3.5.1** 电池组概况 KPI：总电压/电流/SOC/SOH（ProgressGauge × 2 + KpiCard × 2）
- [ ] **3.5.2** 单体电池电压/内阻/温度柱状图（TrendChart bar，标注最高最低值）
- [ ] **3.5.3** 内阻分布图
- [ ] **3.5.4** 电池组拓扑图
- [ ] **3.5.5** 失效预警面板
- [ ] **3.5.6** 历史数据查询
- [ ] **3.5.7** 编译验证 + 预览验证

---

### 第三批验收标准

- [ ] 中压配电：一次系统图断路器分合状态正确，进线参数 KPI 完整
- [ ] 低压配电：备自投状态可视化正确，回路电参量表有数据
- [ ] 柴发并机：机组状态面板 + 远程控制正常
- [ ] 燃油监控：油罐液位动画流畅，续航预测合理
- [ ] 电池监控：SOC/SOH 仪表盘正常，单体电池柱状图有数据
- [ ] 全部无 TypeScript 类型错误

---

## 📦 第四批：安防 3 模块 + 消防 1 模块

> 前置条件：第三批通过验收

---

### 4.1 视频监控页面重做

**文件**: `src/views/monitor/SecurityCctv.vue`

- [ ] **4.1.1** 多画面实时预览：4/9/16 分屏布局（模拟视频流缩略图 + 在线/离线标记）
- [ ] **4.1.2** 摄像头列表：DeviceTable（名称/IP/位置/状态/码流）
- [ ] **4.1.3** 大屏轮巡：每 5 秒自动切换一个摄像头画面
- [ ] **4.1.4** 告警联动：告警触发时对应摄像头画面高亮闪烁
- [ ] **4.1.5** 编译验证 + 预览验证

---

### 4.2 门禁系统页面重做

**文件**: `src/views/monitor/SecurityAcs.vue`

- [ ] **4.2.1** 门禁平面图：楼层平面 SVG + 门禁点位标注（状态=正常/异常/开门/关门）
- [ ] **4.2.2** 实时事件流：刷卡/开门/闯入滚动日志
- [ ] **4.2.3** 通行统计：各门禁点今日通行人次柱状图
- [ ] **4.2.4** 远程控制：开门/锁门按钮（QuickControl）
- [ ] **4.2.5** 告警信息：非法闯入/门磁异常/超时未关
- [ ] **4.2.6** 编译验证 + 预览验证

---

### 4.3 防入侵系统页面重做

**文件**: `src/views/monitor/SecurityIds.vue`

- [ ] **4.3.1** 周界示意图：园区平面 SVG + 防区布防状态标注
- [ ] **4.3.2** 探测器状态面板：红外/微波/振动探测器在线/报警
- [ ] **4.3.3** 入侵告警列表：含位置标注（AlarmBadge）
- [ ] **4.3.4** 布防/撤防状态时间线
- [ ] **4.3.5** 告警联动：入侵触发视频监控弹出
- [ ] **4.3.6** 编译验证 + 预览验证

---

### 4.4 消防系统页面重做

**文件**: `src/views/monitor/SecurityFire.vue`

- [ ] **4.4.1** 消防平面图：楼层平面 SVG + 烟感/温感/喷淋/手报/消火栓点位标注
- [ ] **4.4.2** 报警主机状态面板
- [ ] **4.4.3** 探测器状态统计：正常/报警/故障/离线
- [ ] **4.4.4** 消防联动设备状态：排烟风机/广播/门禁释放/电梯迫降
- [ ] **4.4.5** 火警/故障/监管告警列表
- [ ] **4.4.6** 编译验证 + 预览验证

---

### 第四批验收标准

- [ ] 视频监控：分屏布局正确，轮巡切换流畅
- [ ] 门禁系统：平面图点位可点击，事件流实时更新
- [ ] 防入侵系统：周界图防区状态正确，探测器面板有数据
- [ ] 消防系统：平面图探测器位置正确，联动设备状态有显示
- [ ] 全部无 TypeScript 类型错误

---

## 🔁 每批次完成后统一操作

```bash
# 1. 清理 Vite 缓存（Docker 挂载模式下必须）
docker exec dc-ioc-platform-frontend-1 rm -rf /app/node_modules/.vite

# 2. 重启前端容器
docker restart dc-ioc-platform-frontend-1

# 3. 浏览器硬刷新 (Ctrl+Shift+R) 验证
```

---

## 📊 进度总览

| 批次 | 内容 | 状态 | 文件数 | 约代码量 |
|------|------|------|--------|----------|
| 第一批 | 制冷 3 模块 + 驾驶舱 + 告警中心 + 基础设施 | ⬜ 待开始 | 22 | ~2800 行 |
| 第二批 | 网络 4 模块 | ⬜ 待开始 | 5 | ~1530 行 |
| 第三批 | 供配电 4 + 电池 1 | ⬜ 待开始 | 5 | ~2350 行 |
| 第四批 | 安防 3 + 消防 1 | ⬜ 待开始 | 4 | ~1500 行 |
| **总计** | **16 模块 + 驾驶舱 + 告警中心** | — | **36** | **~8180 行** |

---

> 当前状态：第一批 1.0 基础设施搭建
