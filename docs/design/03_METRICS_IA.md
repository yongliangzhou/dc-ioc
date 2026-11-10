# 03 · 关键设备与监控指标字典、展示优先级与页面结构细化

> **文档集**：[DCIM 全平台诊断与视觉规范](./README.md) · **版本** v1.1 · **核查日期** 2026-11-10
> **本轮只交付文档，不修改任何运行文件。**

## 1. 目的、事实源与「不臆造」原则

本文回答「改什么内容、按什么层级展示」。所有指标名、单位、阈值均来自**当前代码实际渲染的模板与判断表达式**，不引入代码中不存在的遥测点。

| 事实源 | 位置 | 作用 |
| --- | --- | --- |
| 页面模板与阈值表达式 | `frontend/src/views/monitor/**`、 `views/energy/EnergyDashboard.vue`、`views/ops/CapacityWhatIf.vue` | 指标名、单位、现状阈值 |
| API 模块 | `frontend/src/api/{power,hvac,monitor,security,index}.ts` | 前端实际调用的端点 |
| 接口契约 | `frontend/openapi.json`（29 个 DCIM 相关端点） | 端点是否真实存在 |
| 兜底与可信度 | `frontend/src/api/request.ts:125-139,164-169`、`mockData.ts`、`composables/useAsyncPage.ts:138-164`（`useMockFlag` 三档）、`components/common/{DataBadge,MockDataBanner}.vue` | 示例数据标记规则 |
| 刷新与采集周期 | `.env.development` / `.env.example`、`frontend/src/views/**` 各页 `setInterval`、`backend/app/collectors/mock_collector.py:29` | 现状实测（§5.2） |

**四条硬约束**（v1.1 按用户对待确认项的答复核实后修订）：

1. **机柜制冷字段：契约中不存在，需代码轮补齐**。只读核实结论：`backend/app/models/cabinet.py:15-29` 的 `Cabinet` 只有 `u_total / u_used / rated_power_kw / current_power_kw / status` 等字段，**没有** `cooling_capability`（制冷方式）与 `cooling_capacity_kw`（机柜额定制冷容量）；`cooling_capacity_mw` 是**园区级**字段（`backend/app/models/idc.py:24`），`capacity_kw` 是「机柜额定**功率** kW」（`schemas/idc.py:25`），均不能替代。`frontend/openapi.json` 的 `/api/cabinets*` 4 个端点（`:602,624,655,686`）响应 schema 为 `type: object`，同样无该字段。用户确认「字段要在契约中存在」→ 后续代码轮需新增模型字段 + Pydantic schema + Alembic 迁移 + `openapi.json` 同步；**这是 [06](./06_ROADMAP.md) §6「不新增后端字段」不变量的用户确认例外**，见该文 §7 决策 1。本轮仍不造展示数据，也不改契约。
2. **刷新频率现状已核实，不得把建议值当现状**。`frontend/src/composables/useAsyncPage.ts` 全文 404 行**不含任何轮询**（只有 `minLoadingMs=180` 防骨架闪烁与 `keepDataOnError=true`）；但轮询**真实存在于页面层且分散**：`VITE_REFRESH_INTERVAL=3000`（`.env.development` / `.env.example`）、页面硬编码 5s / 15s / 30s / 可配置 10s 混合。完整实测表见本文 §5.2；下表「建议刷新」仅为后续统一策略的**设计建议**，不是现状。
3. **容量四层数据源已核实存在**。`backend/app/services/capacity_energy.py:345-365` 的 `capacity()` 返回 **dims 五维**：`机柜空间(U) / 电力容量(MW) / 制冷容量(MW) / 承重容量(%) / 网络端口(口)`；`capacity_whatif.py:6-7,23-29` 与 `openapi.json:2465`（summary「当前五维容量」）佐证。因此用户确认的**四层图层（温度 / 电力 / 空间 / 承重）全部可落地**，此前「空间/承重待接入」的判断有误，已在 v1.1 更正。注意承重维度是 `dev_count / RACK_TOTAL × LOAD_CAPACITY_PCT` 的**估算值**（`capacity_energy.py:359`），必须显式标注「估算」。
4. **示例数据必须显式标记**。`request.ts` 的 404/405/网络错误兜底予以保留，但任何走兜底的区块都要有 `DataBadge` / `MockDataBanner`；`useAsyncPage.ts:138-164` 已提供 `useMockFlag` 的 `none / partial / full` 三档语义（见 §5.1）；项目约定「绝不静默降级」。

## 2. 设备分类与关键指标字典

> 表内「证据」列为 `文件:行号`；路径简写：`V/` = `frontend/src/views/`，`A/` = `frontend/src/api/`。
> 「端点」列取 `A/*.ts` 中实际调用的路径；总览页为**前端 `Promise.all` 聚合**（`A/power.ts:1148-1150`、`A/hvac.ts:1230-1231`、`A/security.ts:470-471`），无独立后端聚合端点（`D4`）。

### 2.1 电力域（6 类设备）

| 设备类 | 关键指标（现状标签） | 单位 | 现状阈值与证据 | 端点 |
| --- | --- | --- | --- | --- |
| 中压 HV | 线电压 / 电流 / 有功功率 / 功率因数 / 频率 / 电度 / 谐波电压含有率 THD；三相 Ua/Ub/Uc、Ia/Ib/Ic、P、Q、PF、f、E 共 14 列 | kV / A / MW / — / Hz / kWh / % | 无统一阈值表；`V/monitor/PowerHv.vue:181-233`、`:253-266`、`:337`、`:477`、`:506` | `/api/power/hv`（`A/power.ts:1101,1105`） |
| 低压 LV | 设备总数 / 在线率 / 低压总有功 / 平均负载率 / THD-U 均值 / 防雷报警 / 泄漏电流；18 列表头含 Ua/Ub/Uc、Ia/Ib/Ic、Hz、P、Q、PF、kWh、THD-U/I、负载率 | 台 / % / kW / % / % / 路 / mA | 同页无统一阈值；`V/monitor/PowerLv.vue:192-240`、`:351-368`、`:566` | `/api/power/lv`（`:1113,1117`） |
| 柴发 | 机组数量 / 在线机组 / 总输出功率 / **平均负载率** / 并机母线 / 控制模式 / 转速 / 水温 / 油压 / 电池；并机 ΔU、Δf、相位差 | 台 / 台 / kW / % / — / — / rpm / ℃ / — / V | `avgLoad >= 80 → warning`（`PowerGenset.vue:58`）；`autoMode.includes('自动')`（`:75`）；`:28-75`、`:257-267`、`:320-322` | `/api/power/genset`（`:1121,1126`） |
| 燃油 | 储油总量 / 主油罐均位 / 日用箱均位 / 运行油泵 / 管道压力 / 活跃告警 / **满载续航 / 半载续航 / 日用箱续航** / 容量 / 液位 / 存油 / 油温 | L / % / % / 台 / MPa / 项 / h、h、% / L、% 、L、℃ | 压力 `>0.5 → warning`（`:74`）；满载 `<8 danger / <12 warning`（`:414`）；半载 `<24 warning`（`:428`）；日用箱 `<4 danger / <8 warning`（`:442`）；`criticalCount>0 → danger`（`:83`） | `/api/power/fuel`（`:1131,1135`） |
| 电池 / UPS | 系统总电压 / 总电流 / **平均 SOC / 平均 SOH / 后备时间 / 最差组 SOH** / 单体电压、内阻、温度 / 内阻分布 | V / A / % / % / min / % / V、mΩ、℃ | 电压 `<200 → danger`（`:55`）；电流 `>200A → warning`（`:62`）；SOC `<80 → warning`（`:72`）；SOH `<90 → warning`（`:81`）；后备 `<10 danger / <15 warning`（`:120`）；最差组 SOH `<90`（`:131`） | `/api/power/battery`（`:1139,1144`） |
| 配电链路 | KPI 行 / 拓扑 / 节点详情 / 历史趋势 | — | 无阈值；`V/monitor/PowerLinkage.vue:45,77,106,139` | 复用 `A/power.ts` 聚合 |

**入口卡应展示的 3 个判别性指标**（替代当前「平均负载率/平均电压」五卡同构）：

| 设备 | P0 首指标 | P1 次指标 | P1 三指标 | 依据 |
| --- | --- | --- | --- | --- |
| HV | 母线电压偏差 | 有功功率 / 负载率 | 保护动作数 | `PowerHv.vue:181-233` |
| LV | 平均负载率 | THD-U | 防雷报警路数 | `PowerLv.vue:210-240` |
| 柴发 | 平均负载率（80% 阈值） | 在线机组 / 总数 | 自动模式占比 | `PowerGenset.vue:28-75` |
| 燃油 | **满载续航 h** | 主油罐均位 % | 管道压力 MPa | `PowerFuel.vue:412-442` |
| 电池 | **后备时间 min** | 平均 SOC % | 最差组 SOH % | `PowerBattery.vue:66-131` |

### 2.2 暖通与液冷域（5 类）

| 设备类 | 关键指标 | 单位 | 现状阈值与证据 | 端点 |
| --- | --- | --- | --- | --- |
| 冷源 / 冷机 | 运行模式 / 冷冻供水温度（含设定值）/ 冷冻回水温度 / 室外温度 + 湿球 + RH / 部分负载率 PLR / 制冷总量 / 系统流量 / 在线率 | — / ℃ / ℃ / ℃、℃、% / % / MW / m³/h / % | `plrColor` 由 PLR 计算（`HvacChiller.vue:88-89`）；`groupStatus()`（`:171,222,273`）；`:52-105` | `/api/hvac/chiller-plant`（`A/hvac.ts:1221`）、趋势 `:1380`、控制 `:1269` |
| 末端 CRAC | 设备总数 / 运行·待机·故障 / **漏水告警** / 平均送风·回风·供水温度 / 平均室内外压差 / 机房组 7 指标（冷热通道温湿度、露点、压差）/ 回风温度设定 | 台 / 台 / 处 / ℃ / Pa / ℃、%、Pa / ℃ | `leakAlarm > 0 → danger`（`HvacCrac.vue:47`）；`StatusBadge`（`:252,259,270`）；`:29-79`、`:176-227`、`:279,284` | `/api/hvac/crac`（`:1224`）、趋势 `:1550` |
| 液冷 CDU | 一次侧供/回水温度、流量、压力；二次侧供/回水温度、流量；**温差 ΔT**；电导率 / pH / 缓蚀剂 / 乙二醇浓度 / 颗粒计数；回收率 / 回收·回流温度 / 流量；年减排 CO₂ / 年节能；PUE 贡献 / 自然冷却时长 | ℃ / m³/h / bar / ℃ / — / μS/cm / — / ppm / % / 个/mL / % / ℃ / m³/h / 吨 / 万元 / — / h | `\|ΔT\| > 8 → warning`（`HvacLiquid.vue:136`）；`coolantQuality.status`（`:225`）；`:38-59`、`:75-136`、`:232-263`、`:317-357` | `/api/hvac/liquid-cooling`（`:1227`） |
| 制冷链路 | 制冷链路可视化 / 循环 / 特性 | — | 无阈值；`V/monitor/HvacLinkage.vue:51` | `A/hvac.ts:86-87`（页内） |
| 温度云图 | 机房 / 通道 / 机柜进风温度三层下钻 | ℃ | 无阈值；`V/monitor/ThermalCloud.vue:61,84,114` | `A/hvac.ts`；`DataBadge:52` |

**入口卡差异化指标（现状 `HvacDashboard.vue:51-109` 已是正面参照，保留并规范化）**：冷源 = 平均负载率 + 进/出水温度；CRAC = 送/回风温度 + 湿度 + 风机转速；液冷 = 平均流量 + CDU 进/出水温。

### 2.3 网络域（4 类）

| 设备类 | 关键指标 | 单位 | 现状阈值与证据 | 端点 |
| --- | --- | --- | --- | --- |
| 交换机 | 平均 CPU / 平均内存 / 交换机总数 / 端口可用率；端口速率、入/出利用率、实时流量、错包率、丢包率、收光/发光（10 列） | % / % / 台 / % | CPU/内存 `>80 danger / >60 warning`（`NetworkSwitches.vue:19,28`）；端口可用率 `<95 → warning`（`:45`）；`cpu_pct` 直接映射 `#ef4444/#f59e0b`（`:95`）；`:14-45`、`:276-285` | `/api/network/overview`（`A/monitor.ts:540,754-772`，5 个函数复用同一端点） |
| 路由器 | 平均 CPU / 内存 / 台数 / 平均温度 / 吞吐趋势 / 并发连接数 / 新建会话速率 / BGP·OSPF 状态 | % / % / 台 / °C / — | 无统一阈值；`NetworkRouters.vue:25-53`、`:62`、`:127`、`:151`、`:166` | 同上 |
| 防火墙 | 并发连接数 / 新建会话速率 / 安全策略数 / VPN 隧道数 / CPU·内存·磁盘 / 攻击类型分布 / 威胁阻断趋势 / 策略命中排行 | — / cps / 条 / 条 / % / — | 无统一阈值；`NetworkFirewalls.vue:25,33,47,56-74,119` | 同上 |
| 无线 AP | AP 总数 / 在线率 / 接入用户 / 平均信号强度 / 信道利用率与干扰 / 信号热力图 | 台 / % / 人 / dBm / % | 在线率 `<90 → warning`（`NetworkWireless.vue:81`）；`:23,32,69-103` | 同上 |

> 契约端点 `/api/network/bandwidth`、`/api/network/ping`（`frontend/openapi.json:2295,2339`）**前端 0 引用**（问题 `D3`）。后续若要展示带宽/时延曲线，先做「是否接线」评估，不在本轮文档里假定数据已存在。

### 2.4 安防域（4 类）

| 设备类 | 关键指标 | 单位 | 现状阈值与证据 | 端点 |
| --- | --- | --- | --- | --- |
| 视频 CCTV | 摄像机总数 / 在线率 / **NVR 存储天数** / 今日事件 / AI 算法类数 / 码率 / 分区·状态筛选 | 路 / % / 天 / 条 / 类 / — | 「要求 ≥ N 天」（`SecurityCctv.vue:44`，N 未在模板中显式给出；按 [06](./06_ROADMAP.md) §7 决策 6 **待业务确认后登记**，界面暂只展示实测天数）；`:28-52`、`:82`、`:101-111` | `/api/security/cctv`（`A/security.ts:443,446`） |
| 门禁 ACS | 门禁总数 / 在线率 / 今日刷卡 / 拒绝·异常次数 / 门禁平面图 | 樘 / % / 次 / 次 / — | 无阈值；`SecurityAcs.vue:18-30`、`:95` | `/api/security/acs`（`:450,453`） |
| 周界 IDS | 周界防区 / 布防率 / 室内探测器 / 周界告警 / 周界示意图 | 区 / % / 个 / 起 / — | 无阈值；`SecurityIds.vue:22-43`、`:112` | `/api/security/ids`（`:457,460`） |
| 消防 | 探测点位 / 主机遇警率 / 气体灭火区 / 应急照明 / 消防平面图 | 点 / % / 区 / — / — | 无阈值；`SecurityFire.vue:22-43`、`:134` | `/api/security/fire`（`:464,467`） |

**四类入口卡不应统一为「今日事件/今日告警」**：建议 CCTV = 在线率 + NVR 存储天数 + 今日事件；ACS = 拒绝/异常次数 + 在线率 + 今日刷卡；IDS = 布防率 + 周界告警 + 探测器数；消防 = 主机遇警率 + 气体灭火区状态 + 应急照明状态。

### 2.5 资产、容量与能耗

| 域 | 关键指标 | 单位 | 现状阈值与证据 | 端点 / 来源 |
| --- | --- | --- | --- | --- |
| 设备台账 | 设备总量 / 在线率 / 运行小时 / 域·类别筛选 / 分页 | 台 / % / h | 无阈值；`V/ops/Equipment.vue:12-37`、`:149,259`、`:179-184` | `/api/equipment*`（`openapi.json:871,893,924`） |
| 机柜与 U 位 | 机柜列表 / U 位占用 / 冲突检测 / **额定功率 kW** | 台 / U / kW | 无阈值；`V/ops/Cabinets.vue:12-25`、`:109`、`V/ops/UPosition.vue:335-345`；模型字段 `backend/app/models/cabinet.py:25-29`（`u_total/u_used/rated_power_kw/current_power_kw/status`） | `/api/cabinets`（`openapi.json:602,624,655,686`） |
| 容量 What-If | 机柜数 / 单柜功率 / 预测月数 / **容量五维** / 现容量·余量 / **达到 85% / 100% 的月份** / 建议 | 台 / kW / 月 / U·MW·%·口 | 85% / 100% 两档（`CapacityWhatIf.vue:155,161`；后端 `capacity_whatif.py:31-32`）；`form.cabinets` `:48`、`kwPerCabinet` `:58`、`monthsHorizon` `:68`；`:135,142`；`dims[].id` 为中文的说明 `:191` | `/api/ops/capacity`（`openapi.json:2405`）、`/api/ops/capacity/what-if`（`:2427`）、`/api/ops/capacity/what-if/baseline`（`:2449`）；`getCapacityWhatIfBaseline` / `postCapacityWhatIf`（`A/index.ts`，页 `:198`） |
| 容量五维 dims | `机柜空间` U / `电力容量` MW / `制冷容量` MW / `承重容量` % / `网络端口` 口 | U / MW / MW / % / 口 | 承重为按设备数占比的**估算**（`capacity_energy.py:359`），非实测称重；`capacity_whatif.py:23-29` 定义每新增一柜的增量（42U / 2 上联口 / IT 功率 ×1.25 制冷系数） | `capacity_energy.py:345-365`；`capacity_whatif.py:6-7` |
| 能耗 | **当前 PUE** / 当日总能耗 / IT 设备能耗 / 制冷能耗 / 7 日 PUE 趋势 / 7 日能耗分解 / 未来 24h 负载预测 / 可降功率 / 综合节能率 / 估算节能 | — / kWh / kWh / kWh / — / — / kW / kW / % / kW、% | PUE `>1.6 crit / >1.4 warn`（`EnergyDashboard.vue:47`）；`:42-66`、`:99-111`、`:120-141`、`:152-192`、`:213`、`:240-250`、`:429-451`（图表色 `#22e3ff/#3b82f6` 硬编码）、`:589`（`🎯` emoji 图标） | `V/energy/EnergyDashboard.vue` 内 `useAsyncPage`；CSV 导出复用 `export.ts`（`:561-579`） |
| 健康度 | 设备健康度评分 / 报告 | 分 | 无阈值；`V/monitor/HealthDashboard.vue:4` | `A/health.ts`（页 `:115`） |

### 2.6 四层容量图层的数据来源映射（用户确认：图层切换做四层）

借鉴 [01 范式 B](./01_BENCHMARK.md) 的 openDCIM 容量叠加层。四层**共用一个 `LayerSwitch` 交互契约**，图层切换不改变空间坐标系（机房 → 通道 → 机柜），只更换着色维度与图例。第五维 `网络端口` 按用户确认**不进图层**，仍留在 What-If 结果区。

| 图层 | 着色指标 | 数据来源 | 可信度标记 | 展示优先级 |
| --- | --- | --- | --- | --- |
| 温度 | 机房 / 通道 / 机柜进风温度 | `V/monitor/ThermalCloud.vue:61,84,114` 三层下钻（`A/hvac.ts`） | 已有 `DataBadge:52` | P1 |
| 电力 | 「电力容量」MW 余量 + 单柜 `current_power_kw / rated_power_kw` | `capacity_energy.py:357` 五维 + `/api/ops/capacity`（`openapi.json:2405`）+ `PowerHv/Lv` 遥测 | 真接口 → 无标记；兜底 → `MockDataBanner` | **P0**（越限即风险） |
| 空间 | 「机柜空间」U 占用 + U 位立面图 | `capacity_energy.py:356` + `/api/cabinets/{id}/u-position`（`openapi.json:655`） | 真接口 | P1 |
| 承重 | 「承重容量」% 估算 | `capacity_energy.py:359,361`（按设备数占比估算） | **必须标注「估算 · 非实测称重」**，不得当作实测值 | P2 |

**交互约束**：四层共用同一图例位置与阈值线样式（[04](./04_VISUAL_SPEC.md) §7）；切换时 ECharts / SVG 只 `setOption` 更新着色，**不重建实例**；任何一层走 `request.ts` 兜底时按 §5.1 显式标记。承重层因是估算值，禁止用 `--red` 直接呈现为「超限故障」，只能用 `--amber` + 「估算」文字。

---

## 3. 展示优先级定义（P0 / P1 / P2）

| 级别 | 定义 | 判定规则 | 视觉权重（详见 [04](./04_VISUAL_SPEC.md) §4） | 位置 |
| --- | --- | --- | --- | --- |
| **P0** | **需要立即动作**：安全/供电中断风险、越限、未处理告警、续航/后备时间不足 | 有明确阈值且当前越限，或值为「故障/告警/离线/中断」 | 24px 等宽数值 + 状态条 + 图标 + 文字标签；占页首第一屏 | 四块结构的第 ② 块 |
| **P1** | **需要判断**：设备域健康主指标、容量余量、在线率、PUE、负载率 | 有阈值但未越限，或需横向对比 | 16–20px 数值 + 单位 + 环比/阈值线 | 第 ② 块次行 + 第 ③ 块入口卡 |
| **P2** | **需要查证**：明细遥测、历史趋势、水质/成分、审计记录、扩展属性 | 非实时决策所需 | 13px 正文/表格，默认折叠或置于下方 | 第 ④ 块与「更多指标」区 |

**P0 判定必须可配置**：阈值统一放 `metricsCatalog.ts`，不允许模板三元表达式再写数值（现状反例：`NetworkSwitches.vue:95`、`PowerFuel.vue:414`、`EnergyDashboard.vue:47`）。

### 3.1 按角色的优先级覆盖

| 角色 | 首屏 P0 | 常用 P1 | 允许隐藏 | 本平台已有入口 |
| --- | --- | --- | --- | --- |
| 值班监控 | 未处理告警 / 故障设备 / 供电与后备时间 / 漏水告警 | 各域在线率、PUE、负载率 | 资产台账明细、审计日志 | `V/overview/Index.vue`、`V/ops/Alarms.vue` |
| 设施运维 | 越限指标与其所属设备 / 链路影响 | 冷机 PLR、CDU ΔT、SOC/SOH、AP 在线率 | 财务/年节能、供应商 | `V/monitor/*Dashboard.vue` + 详情页 |
| 容量 / 规划 | 达到 85%/100% 容量的月份 / 瓶颈维度 | 机柜数、单柜功率、U 位占用 | 实时秒级遥测 | `V/ops/CapacityWhatIf.vue`、`V/ops/UPosition.vue` |
| 管理 / 报表 | PUE、总能耗、节能收益、园区对比 | 在线率趋势、健康度评分 | 单体设备明细 | `V/energy/EnergyDashboard.vue`、`V/ops/DataCenterCompare.vue` |
| 审计 / 合规 | 操作审计、行级变更、导出 | 权限变更记录 | 监控图表 | `V/admin/AuditLogs.vue`、`V/admin/RowAudit.vue` |

> 角色视图**不新增路由**：通过 `useDashboardLayout.ts` 的区块显隐与筛选视图（[01 范式 C](./01_BENCHMARK.md)）实现，避免触发 `check_nav_routes.py --strict`（71 路由 / 0 死链 / 0 孤儿）。

## 4. 分组方式

### 4.1 四种分组维度及适用场景

| 维度 | 规则 | 适用 | 反例（现状） |
| --- | --- | --- | --- |
| 按设备域 | 暖通 / 电力 / 液冷 / 网络 / 安防 / 资产 / 能耗，每域固定 3 个判别性指标 | 总览页入口卡、驾驶舱区块 | `PowerDashboard.vue:52-121` 五个不同设备共用两个指标 |
| 按优先级 | P0 异常 → P1 健康 → P2 明细 | 所有详情页首屏 | `HvacLiquid.vue` 23 张卡同屏平铺无主次 |
| 按任务 | 监控 / 处置 / 规划 / 审计，对应不同角色首屏 | 导航分组与角色视图 | 现状导航按功能平铺，无「当前任务」上下文 |
| 按时间 | 实时（当前值 + 状态）/ 近期（趋势与阈值线）/ 历史（表格与导出） | 图表与表格区 | 趋势图与明细表混排，阈值线缺失 |

### 4.2 标杆页统一四块结构（阶段 2 落地）

```
① 页头 PageHead
   页面主标题(h1) · 数据源可信度标记(DataBadge) · 刷新时间 · 时间范围选择器
② P0 关键指标行
   「未处理告警 / 故障设备 / 越限指标 / 供电或后备时间风险」≤4 张 MetricCard
   统计类（设备总数、在线率）降为 P1，置于次行或合并为摘要文案
③ 子系统入口卡区（按设备域分组，每卡 3 个差异化指标）
   卡片可点击：cursor:pointer + 150-300ms 过渡 + 可见 focus
④ 趋势与告警联动区
   BaseChart(统一阈值虚线 + 图例 + 空态) + 告警列表 + 跳转工单入口
```

驾驶舱 `V/overview/Index.vue:6` 沿用现有六区块可配置布局（`composables/useDashboardLayout.ts`），**只统一卡片与图表外观、不改变区块配置契约**。

### 4.3 四个总览页的改造对照

| 页 | 现状（问题） | 目标（字段均取自现有接口） |
| --- | --- | --- |
| `PowerDashboard.vue` | 5 卡 × 「平均负载率 / 平均电压」`：`:60-119` | HV 电压偏差·负载率·保护动作；LV 负载率·THD-U·防雷报警；柴发 负载率·在线机组·自动模式；燃油 **满载续航**·油罐均位·管压；电池 **后备时间**·SOC·最差组 SOH |
| `NetworkDashboard.vue` | 4 卡 × 「平均延迟 / 带宽利用率」`:63-113` | 交换机 CPU·端口可用率·错包率；路由 CPU·温度·BGP 状态；防火墙 并发连接·新建会话·阻断趋势；无线 在线率·平均信号 dBm·信道干扰 |
| `SecurityDashboard.vue` | 4 卡 × 「今日事件 / 今日告警」`:60-110` | CCTV 在线率·NVR 存储天数·今日事件；ACS 拒绝/异常·在线率·今日刷卡；IDS 布防率·周界告警·探测器数；消防 遇警率·气体灭火区·应急照明 |
| `HvacDashboard.vue` | **已差异化** `:51-109`，保留 | 只补页头可信度标记、P0 行与异步四态统一（修 `:143-152` 手写错误态） |

---

## 5. 数据来源、可信度与刷新频率规范

### 5.1 可信度三档与展示组件

`frontend/src/composables/useAsyncPage.ts:138-164` 已定义 `useMockFlag` 的 `MockLevel = 'none' | 'partial' | 'full'`，注释 `:119-136` 明确警告 `partial`（真设备 + 部分模拟字段，甚至给真实设备挂 `Math.random()` 读数）是**最危险的「真假混排」**，必须点名哪些是假的。规范以此为准：

| 档位 | 语义 | 来源 | 展示组件与位置 | 文案规范 |
| --- | --- | --- | --- | --- |
| `none` | 全部真实数据 | 后端端点成功返回 | 无需标记，页头显示**最后刷新时间** | `最后更新 HH:mm:ss` |
| `partial` | 真设备 + 部分模拟字段 | 页面自带 `mockData()` 补齐接口表/趋势等 | **页头 `DataBadge` + 区块 `MockDataBanner`，并写明哪些字段是模拟的** | `部分字段为示例数据：接口表 / 吞吐趋势` |
| `full` | 整页模拟 | `request.ts:134` `mockForUrl` 兜底 | 同上，文案更明确 | `示例数据 · 未连接采集服务`（zh）/ `Sample data`（en） |
| 无数据 | 成功但集合为空 / 请求失败 | — | `AsyncSection` 的 empty / error 态，`ErrorRetry` 提供重试 | 空态与错误态**文案与 DOM 必须区分**（修 `HvacChiller.vue:925-926` 把错误当空态） |

现状 25 个页面已用 `MockDataBanner`/`DataBadge`（`V/monitor/PowerHv.vue:9`、`V/overview/Index.vue:62,138,257,276,368,373`、`V/energy/EnergyDashboard.vue:143,272` 等），但 4 个网络页自带本地 `mockData()` 且提示方式不一（`V/monitor/NetworkSwitches.vue:386,576,738`），需收敛到上表三档。正确范本见 `V/monitor/SecurityCctv.vue` / `SecurityAcs.vue`（仅 `full` 一档，`useAsyncPage.ts:136` 已注明）。

### 5.2 刷新频率：现状实测（v1.1 核实）与统一策略建议

> **v1.1 更正**：v1.0 曾写「刷新频率现状未知 / 页面未见轮询周期声明」，**与代码不符**。按用户第 3 项要求核对 `useAsyncPage.ts` 与采集配置后，结论如下。以下「现状」列是实测事实，「建议」列仅为后续代码轮的设计目标，**两者不得混用**。

**`useAsyncPage.ts` 本身不含轮询**：全文 404 行只有 `autoLoad`（`:209`）、`minLoadingMs = 180`（`:212`，防骨架闪烁）、`keepDataOnError = true`（`:213`，注释 `:180-181` 提到「轮询场景推荐 true」）、`reload()` / `reloadAll()` / `reloadFailed()`（`:280,383,387`）等手动入口；**无 `setInterval`**。轮询由各页面自行 `setInterval` 实现。

**现状实测表**（2026-11-10 只读核查）：

| 实际周期 | 配置来源 | 页面与行号 |
| --- | --- | --- |
| **3s**（开发环境） | `.env.development` / `.env.example` 的 `VITE_REFRESH_INTERVAL=3000` | `V/ops/Alarms.vue:899,1220-1222`、`V/ops/Collector.vue:208,430` |
| 默认 5s（被 env 覆盖为 3s） | `import.meta.env.VITE_REFRESH_INTERVAL ?? 5000` | `V/ops/AlarmHistory.vue:451`、`V/ops/Telemetry.vue:277`（注释 `:246` 明确「后台轮询失败静默」） |
| 默认 15s（被 env 覆盖为 3s） | `?? 15000` | `V/ops/Equipment.vue:351`（注释 `:258` 静默）、`V/ops/Cabinets.vue:281` |
| **30s 硬编码** | 页面常量或字面量 | `V/overview/Index.vue:1043`（模板 `:8` 写「每 30 秒自动刷新」）、`V/monitor/SecurityIds.vue:568`、`SecurityFire.vue:694`、`SecurityCctv.vue:480`、`SecurityAcs.vue:540`、`PowerFuel.vue:1771`、`PowerBattery.vue:1152`、`HvacLiquid.vue:550`、`HvacCrac.vue:522`、`HvacChiller.vue:1582-1584` |
| 可配置，默认 10s | `(cfg.refreshSec \|\| 10) * 1000` | `V/monitor/BigScreen.vue:166` |
| 其他页面轮询 | — | `V/monitor/Scene3D.vue:471`、`PowerLinkage.vue:1032`、`SecurityCctv.vue:349`（巡检轮播） |
| **后端推送 5s** | `PUSH_INTERVAL_SEC = 5` | `backend/app/collectors/mock_collector.py:29,524,556`（仅 **mock** 采集器；真实采集器未声明统一周期，`backend/app/collectors/thing_models.py:313` 只是「程序扫描周期」标签翻译） |

**现状结论**：刷新策略是「环境变量 3s（dev）+ 页面硬编码 5s/15s/30s/10s」混合，**没有统一策略**；`useAsyncPage.ts` 不负责轮询，页面各自 `setInterval` 且部分页面轮询失败静默（`Telemetry.vue:246`、`Equipment.vue:258`），与「绝不静默降级」存在张力（后台轮询静默是有意设计，但需与显式刷新区分并在规范中写明）。

**统一策略建议（设计目标，不是现状）**：

| 数据类别 | 建议刷新 | 交互要求 | 相对现状的改动 |
| --- | --- | --- | --- |
| 告警 / 故障 / P0 异常 | WS 推送 + 30s 兜底 | 新告警 150–300ms 过渡、不闪烁、提供暂停 | 现状 3s 轮询，收敛到 WS |
| 实时遥测（电压/温度/流量/CPU） | 30s 统一常量 | 等宽数字 + 固定列宽，数值变化不引起抖动 | 现状多数已 30s，只需去掉硬编码 |
| 统计聚合（在线率/设备总数/PUE） | 60s | 页头显示刷新时间 | 现状驾驶舱 30s |
| 趋势 / 历史 / 报表 | 手动或 5min | 显式「刷新」按钮 + `TimeRangePicker` | 新增 |
| 资产台账 / 审计 / 配置 | 仅手动 / 变更后 | 分页与筛选写 URL，禁止自动刷新打断输入 | 现状 3s/15s 轮询，需取消 |
| 全站配置 | 单一 `VITE_REFRESH_INTERVAL` + 分层默认值 | 禁止页面内硬编码数字；`useAsyncPage` 保持无轮询 | 统一 3s/5s/15s/30s/10s |

**验收要求**：后续代码轮必须先按上表核对现状，再改；不得把「建议」列写进代码注释或文档当作既有实现；页头显示最后刷新时间；WS/轮询策略与后端采集周期对齐（真实采集周期仍需与后端确认）。

### 5.3 性能约束（写入规范，供后续轮遵循）

- ECharts 实例复用，主题切换时只 `setOption` 更新 `color` / `axisLine` / `splitLine` 等少数项，**不销毁重建**。
- 3D 场景（`V/monitor/Scene3D.vue`）由全量轮询改为增量更新；大屏（`V/monitor/BigScreen.vue`）避免整页重排。
- 长列表沿用 `C/common/VirtualList.vue`；>8 列宽表默认只渲染可见列集。
- 主题切换不得触发全页面路由重载。

---

## 6. 单位、阈值与文案的统一契约（草案）

后续代码轮建议新增 `frontend/src/config/metricsCatalog.ts`（**本轮不创建**），每项结构：

```
MetricDef {
  key          // 稳定标识，如 power.fuel.fullLoadHours
  labelKey     // i18n key（zh/en 同步）
  unit         // 统一单位字符串，见下表
  precision    // 小数位
  thresholds   // { warn, danger, direction: 'above'|'below' }
  severity     // 越限后的 P0/P1 级别
  source       // 端点路径，用于可信度标记
  group        // 设备域
}
```

**单位归一表**（消除现状 `℃`/`°C`、`bar`/`MPa`、`L/min`/`m³/h` 混用）：

| 现状混用 | 统一为 | 影响页面 |
| --- | --- | --- |
| `℃` / `°C` | `°C` | `HvacChiller.vue`、`HvacCrac.vue`、`HvacLiquid.vue`、`PowerGenset.vue` |
| `L/min` / `m³/h` | `m³/h`（流量），`L` 仅用于容积 | `HvacLiquid.vue:89,129`、`HvacDashboard.vue:98-99`、`PowerFuel.vue:28` |
| `bar` / `MPa` | `MPa`（压力），`bar` 仅在后端原始字段保留 | `HvacLiquid.vue:96`、`PowerFuel.vue:69` |
| `cps` / `条` / `次` | 保留业务单位但统一小数位与千分位 | `NetworkFirewalls.vue:56`、`SecurityAcs.vue:26` |
| `μS/cm` / `ppm` / `个/mL` | 保留，统一为 P2 明细区 | `HvacLiquid.vue:232-263` |

**i18n 约束**：任何新增或调整的用户可见文案必须同时写入 `frontend/src/i18n/locales/zh-CN.json` 与 `en-US.json`，保持 `scripts/check_i18n_keys.py --json` 的 zh/en 3072 键对齐；不得绕过 `tl()` / `t()` 直接写中文。

---

## 7. 验收清单（供后续代码轮）

| 检查项 | 期望 |
| --- | --- |
| 4 个总览页入口卡 | 每卡 3 个**按设备域差异化**的指标，无两卡完全相同 |
| P0 指标 | 4 个总览页 + 驾驶舱首屏均含「未处理告警/故障/越限」且视觉权重高于统计卡 |
| 阈值来源 | 模板中不再出现数值型阈值三元表达式，全部来自 `metricsCatalog` |
| 单位 | 上表 5 组混用全部归一 |
| 可信度 | 25 个已标记页 + 4 个本地 mock 页统一 `useMockFlag` 三档（§5.1）；`partial` 必须写明哪些字段是模拟的；无「错误当空态」 |
| 刷新 | 按 §5.2「现状实测 / 设计建议」分离执行；页头显示最后刷新时间；页面内不再硬编码轮询数字；真实采集周期与后端确认后再定策略 |
| 容量图层 | 四层（温度 / 电力 / 空间 / 承重）共用 `LayerSwitch`，第五维不进图层；承重标注「估算 · 非实测称重」 |
| 机柜制冷字段 | 按 [06](./06_ROADMAP.md) §7 决策 1 新增字段 + 迁移 + `openapi.json` 同步后才允许界面展示；未完成前不造假数据 |
| 契约 | 不新增端点 / 表 / 路由；仅决策 1 的字段级例外；`check_api_contract.py` 仍 200 paths / 271 operations |
| 路由 / i18n | `check_nav_routes.py --strict` 71 路由 0 死链 0 孤儿；zh/en 键对齐 |
| 图表 | 阈值虚线 + 图例 + 空态齐全；主题切换不重建实例 |

---

**阅读下一步**：[04_VISUAL_SPEC.md](./04_VISUAL_SPEC.md)（改成什么样：双主题、组件、图表）→ [05_RESPONSIVE_SPEC.md](./05_RESPONSIVE_SPEC.md)（四档响应式）。
