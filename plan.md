# 数字孪生拓扑（Twin Topology）实施计划

> 面向 `ops/Twin.vue` + `components/twin/TopologyFlow.vue` 的迭代任务追踪。
> 状态图例：`✅ 已完成` / `🚧 进行中` / `⬜ 未开始`

---

## 任务① 能流速度 / 温度映射

- ✅ 真实测点驱动能流速度：每个节点有效负载率 `loadPct`（优先真实测点，回退模拟）归一化 → 能流动画时长（`TopologyFlow.vue:166` 注释段 + `:374` 归一化）
- ✅ 温度映射：供水→回水（冷量流）或通用温度 → 节点温度文本 `tempText` + 链路色温（`nodeTempText` `:176`）
- ✅ 负载/健康/冗余着色：`hColor` 健康分渐变、冗余标签
- ✅ 图例与来源标注：供电能流 / 制冷冷量流 / 故障传播 / 真实测点驱动 / 模拟负载

## 任务② 故障传播文字化

- ✅ `affectedIds` 驱动故障节点（`affected`）+ 下游（`downstream`）高亮与淡化
- ✅ 文字标注「故障传播 · N 台波及」（`TopologyFlow.vue:6`）
- ✅ 故障边红色描边（`fault` class）

## 任务③ 链路缩略图 / 聚焦交互

- ✅ 右上角缩略图面板：全网节点圆点（按域着色）+ 边 + 实时视口矩形（随主画布滚动同步）
- ✅ 缩略图点击定位主画布（居中滚动）；点击缩略图节点圆点直接聚焦
- ✅ 主画布改为固定像素滚动舞台（`max-height:520px; overflow:auto`），使导航有意义
- ✅ 点击节点聚焦：高亮该节点 + 直连邻居，其余节点/边 `dim` 淡化
- ✅ 悬停预览关联链路：`hoveredId` + `hotEdge`/`hot` 临时高亮
- ✅ 聚焦详情卡（左下浮窗）：负载/温度/健康/冗余/在线状态 + 实时测点字段 + 所属包间（`roomName` 经 `Twin.vue` 透传 `roomNameOfRoom`）

---

## 阻塞修复（导致 `Twin.vue` 500 的编译错误，已解决）

- ✅ 创建缺失组件 `components/common/Panel.vue`（`title`/`icon` + `#extra`/`default` slot）、`components/common/ViewHead.vue`（`title`/`sub` + `#actions` slot）——`Twin.vue` 此前 import 了但从未创建，Vite 解析失败 → 500
- ✅ 修复 `src/types/index.ts` 第 854 行孤立 `}`（语法错误 `TS1128`，Vite 解析失败 → 500）
- ✅ `TopologyFlow.vue`：补 `TopologyRealtime` 类型导入；`LEdge` 接口补 `source`/`target`；`affectedIds` 空安全（`?.` + `!`）
- ✅ `Twin.vue` 4 处历史类型不匹配（视图此前从未运行，未暴露）：
  - 知识面板 `knowledge.architecture` → `knowledge.arch?.design`
  - 知识面板 `knowledge.principle` → `knowledge.arch?.redundancy`
  - KPI `coverage.twins` → `tg.summary.equipmentCount`
  - KPI `coverage.refreshRate` → `coverage.refreshMs`（显示为 `x.x s`）

> 验证：`vite build`（与 dev server 同款 esbuild 管线）已通过 —— `✓ 2547 modules transformed`，确认 `Twin.vue`/`TopologyFlow.vue`/`Panel.vue`/`ViewHead.vue` 均正确编译，500 消除。

---

## 待验证 / 未做

- ⬜ **Docker 容器内浏览器冒烟测试**：当前 Docker 未运行，仅本地 `vite build` 通过。上线后需：
  ```bash
  docker exec dc-ioc-platform-frontend-1 rm -rf /app/node_modules/.vite && docker restart dc-ioc-platform-frontend-1
  ```
  再浏览器硬刷新（`Ctrl+Shift+R`），确认缩略图/聚焦交互在真实数据下正常。
- ⬜ （可选，非本次范围）其余预存类型错误：`api/index.ts`(`DomainOverview`)、`mockData.ts`、`Alarms.vue`、`Drill.vue`、`Equipment.vue`、`DomainDevices.vue`、`Pagination.vue`、`CollectorDeviceForm.vue` 等。这些与孪生拓扑任务无关，且 **esbuild 在 dev/build 时忽略类型错误、不会引发 500**，故未改动以免引入风险。

---

## 备注

- 任务①②③ 的代码改动均在 `TopologyFlow.vue`（主舞台/缩略图/聚焦）+ `Twin.vue`（数据接线/缺失组件透传）完成。
- `Panel.vue` / `ViewHead.vue` 为本次新增文件，属于「阻塞修复」而非任务①②③本身的需求。
