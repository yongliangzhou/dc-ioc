---
name: dc-ioc平台-Dify RAG接入与2D拓扑增强
overview: 两个目标：(1) 把 AI 运维助手升级为「Dify 做知识库 RAG 检索编排 + NIM 小模型生成」，并暴露本项目后端工具(告警/测点)供 Dify 回调；(2) 把数字孪生 2D 能流拓扑做得更具体生动(机房平面图 / 机柜热力 / 更丰富动画)，3D 保持现状。
design:
  architecture:
    framework: vue
  styleKeywords:
    - 科技感
    - 数据中心指挥中心
    - 暗色主题
    - 热力可视化
    - 发光能流
  fontSystem:
    fontFamily: PingFang SC
    heading:
      size: 20px
      weight: 600
    subheading:
      size: 15px
      weight: 500
    body:
      size: 13px
      weight: 400
  colorSystem:
    primary:
      - "#22D3EE"
      - "#3B82F6"
    background:
      - "#0B1220"
      - "#0F172A"
    text:
      - "#E2E8F0"
      - "#94A3B8"
    functional:
      - "#EF4444"
      - "#F59E0B"
      - "#10B981"
todos:
  - id: dify-config
    content: 后端 .env 与 config.py 新增 DIFY_API_KEY/BASE_URL/DATASET_ID/TOOL_KEY 配置
    status: completed
  - id: dify-client
    content: 新建 dify_client.py 封装 Knowledge retrieve（超时+异常回退）
    status: completed
    dependencies:
      - dify-config
  - id: assistant-rag
    content: 改 assistant_service.py 使 _retrieve 走 Dify 优先+关键词兜底，answer 拼接片段
    status: completed
    dependencies:
      - dify-client
  - id: dify-tools
    content: 新建 dify_tools.py 暴露受 DIFY_TOOL_KEY 保护的告警/测点/设备端点
    status: completed
    dependencies:
      - dify-config
  - id: assistant-api
    content: 改 assistant.py 的 /ask 与 /status 兼容 Dify 诊断与来源
    status: completed
    dependencies:
      - assistant-rag
      - dify-tools
  - id: topo-plan
    content: 用 [skill:ui-ux-pro-max] 生成数据中心拓扑设计系统，[skill:lucide-icons] 取图标
    status: completed
  - id: topo-enhance
    content: 增强 TopologyFlow.vue：机房平面图层+机柜热力+升级能流动画
    status: completed
    dependencies:
      - topo-plan
  - id: topo-page
    content: 改 TwinDashboard.vue 与 Assistant.vue 接入新图层与 Dify 来源标注
    status: completed
    dependencies:
      - topo-enhance
---

## 用户需求

用户希望 dc-ioc-platform 在两个方面达到更理想的效果：

1. **数字孪生拓扑更具体生动**：当前 2D 拓扑（TopologyFlow.vue）是抽象能流图，希望升级为更像真实数据中心的图（机房平面图背景、机柜热力、丰富动画）。3D 数字孪生（Twin3D.vue）保持现状不变。

2. **AI 运维助手接入 RAG（Dify）**：当前助手是「关键词打分（RAG-lite）」，无向量检索。用户选择：Dify 负责知识库检索编排，实际生成仍走现有 NIM 小模型（meta/llama-3.1-8b-instruct）；Dify 通过 API Tool 回调本项目后端（告警/测点）获取实时数据。

## 产品概述

在不引入重型依赖、不破坏现有运行模式（本地 uvicorn + npm run dev）的前提下，完成：

- 2D 数字孪生拓扑可视化升级，呈现真实数据中心机房平面图与机柜热力。
- AI 助手新增 Dify RAG 检索层 + 后端工具回调端点，保留 NIM 生成与实时态势注入。

## 核心功能

- 2D 拓扑机房平面图背景：按机房/机柜层绘制楼层平面图、机柜行列网格与标签。
- 机柜热力气泡：按设备温度/负载渲染热力色块与脉冲动画。
- 能流动画升级：粒子流光、故障扩散高亮、可点选详情卡。
- Dify 知识库检索：后端调用 Dify Knowledge API 召回 top-k 片段，替代关键词打分检索。
- Dify 工具端点：新增受 DIFY_TOOL_KEY 保护的 /api/ops/dify/tools/* 供 Dify API Tool 回调（活跃告警、实时/历史测点、设备列表）。
- NIM 生成保持不变：召回片段 + 实时态势 仍交由现有 _call_llm 生成回答。

## 技术栈选择

- 前端：Vue3 + TypeScript + Vite（沿用现有），2D 拓扑继续原生 SVG（无新重型依赖）。
- 后端：FastAPI + SQLAlchemy + PostgreSQL（沿用现有），新增 Dify HTTP 客户端（标准库 urllib，与现有 _call_llm 一致，无新第三方依赖）。
- 配置：沿用 .env 环境变量注入（与 LLM_ *并列新增 DIFY_*）。
- 3D（Twin3D.vue）：保持现状，不改动。

## 实现方案

### 一、2D 数字孪生拓扑增强

**策略**：在现有 `TopologyFlow.vue`（纯 SVG）基础上程序化增强，不换渲染技术。新增「机房平面图层」作为拓扑底图，叠加机柜热力气泡与升级能流动画。后端 topology 数据已含节点分层（lane/load/health），前端按 `location` 派生机房-机柜网格坐标。

**关键决策**：

- 机房平面图用 SVG `<g>` 程序化绘制，避免引入图片素材；机柜用圆角矩形网格，按拓扑节点归属聚合。
- 机柜热力：设备温度映射颜色（复用现有 colorFor 逻辑），机柜聚合显示平均温度气泡 + CSS/SVG 脉冲动画（animate 元素，避免 requestAnimationFrame 成本）。
- 能流：保留 animateMotion 流光，新增粒子密度随 load 变化（控制 path 上 circle 数量，上限防过载）。

**性能**：拓扑节点上限受 `getTwinTopology` 返回量约束；机柜热力聚合在前端一次性计算 O(n)，动画用 SVG 原生属性，不触发 React/Vue 重渲染循环；避免每帧重算布局。

### 二、AI 助手 Dify RAG 接入

**策略**：新增 `dify_client.py` 封装 Dify Knowledge 检索（POST /v1/datasets/{id}/retrieve）与对话（可选），在 `assistant_service.py` 中以「Dify 召回优先、关键词打分兜底」的分层检索替换纯关键词 `_retrieve`。生成仍走现有 `_call_llm`（NIM）。新增 `dify_tools.py` 路由，暴露受 `DIFY_TOOL_KEY` 保护的端点供 Dify API Tool 回调。

**关键决策**：

- Dify 作为检索层：`_retrieve` 改为：先尝试 Dify retrieve 取 top-k 片段（带 score 归一），失败或为空时回退现有 `_retrieve` 关键词打分（保证离线可用，符合现有可观测性设计）。
- 生成复用 NIM：召回片段 + `_build_situation`（活跃告警/实时测点）拼成 prompt，仍走 `_call_llm`，现有回退逻辑不变。
- 工具端点：Dify 配置 API Tool 时需可访问的本项目 HTTP 端点，新增 `/api/ops/dify/tools/alarms/active`、`/metrics/realtime`、`/devices`，用 Header `Authorization: Bearer ${DIFY_TOOL_KEY}` 校验，复用 `alarms.py`/`external.py` 现有查询函数避免重复实现。
- 配置：`.env` 新增 `DIFY_API_KEY`、`DIFY_BASE_URL`（默认 http://localhost:5001/v1）、`DIFY_DATASET_ID`、`DIFY_TOOL_KEY`；`config.py` 读取；缺失时 `_llm_config` 风格守卫，不阻断启动。

**性能与可靠性**：Dify retrieve 设置超时（复用 LLM_TIMEOUT 思路，urllib timeout）；失败快速回退本地检索，不阻塞问答；工具端点复用现有 DB session 查询，无额外全表扫描。

## 实现说明（防回归）

- 复用现有 `_call_llm`、`_build_situation`、`check_llm_status`，勿重写 LLM 调用。
- Dify 检索失败必须回退关键词打分（现有测试/前端「知识库检索（大模型不可用）」横幅逻辑保留）。
- 工具端点加 `DIFY_TOOL_KEY` 校验，与现有 `_rw` 依赖区分；不暴露写操作。
- 2D 拓扑改动保持纯 SVG + 现有 `layerAssign` 算法，勿破坏故障 BFS 高亮与 minimap。
- 本地运行直接读 .env 生效；若用 Docker 重建后端需 `docker compose ... up -d backend`（.env 不被 restart 读取）。

## 架构设计

```mermaid
graph TD
  A[前端 Assistant.vue] -->|POST /api/ops/assistant/ask| B[assistant_service.answer]
  B --> C{_retrieve 分层检索}
  C -->|优先| D[dify_client.retrieve 召回 top-k]
  C -->|兜底| E[现有关键词打分 _retrieve]
  B --> F[_build_situation 实时态势]
  B --> G[_call_llm NIM 生成]
  H[Dify 平台] -->|API Tool 回调| I[/api/ops/dify/tools/*]
  I --> J[alarms/external 现有查询]
  K[TwinDashboard] --> L[TopologyFlow 增强]
  L --> M[机房平面图层+机柜热力+能流动画]
```

## 目录结构

```
dc-ioc-platform/
├── backend/
│   ├── .env                                    # [MODIFY] 新增 DIFY_API_KEY/DIFY_BASE_URL/DIFY_DATASET_ID/DIFY_TOOL_KEY
│   ├── app/
│   │   ├── core/config.py                      # [MODIFY] 读取 DIFY_* 配置项（与 LLM_* 并列）
│   │   ├── services/
│   │   │   ├── assistant_service.py            # [MODIFY] _retrieve 改为 Dify 优先+关键词兜底；answer() 拼接 Dify 片段
│   │   │   └── dify_client.py                  # [NEW] Dify Knowledge retrieve 封装（urllib，超时+回退）
│   │   └── api/v1/endpoints/
│   │       ├── assistant.py                    # [MODIFY] /ask 透传新检索；/status 增加 Dify 连通诊断
│   │       └── dify_tools.py                   # [NEW] /api/ops/dify/tools/alarms/active、/metrics/realtime、/devices 受 DIFY_TOOL_KEY 保护
├── frontend/
│   └── src/
│       ├── views/twin/TwinDashboard.vue        # [MODIFY] 接入增强版拓扑，新增机房平面图开关/图例
│       ├── components/twin/TopologyFlow.vue    # [MODIFY] 新增机房平面图层、机柜热力气泡、升级能流动画；保留 layerAssign/BFS/minimap
│       └── views/ops/Assistant.vue             # [MODIFY] 显示 Dify 知识来源标注；诊断横幅兼容 Dify 状态
```

## 关键代码结构（可选）

```python
# backend/app/services/dify_client.py
def dify_retrieve(question: str, top_k: int = 5) -> list[dict]:
    """调用 Dify Knowledge API 召回片段；失败抛异常由调用方兜底。"""

# backend/app/api/v1/endpoints/dify_tools.py
@router.get("/alarms/active")   # Header Bearer DIFY_TOOL_KEY 校验
@router.get("/metrics/realtime")  # device_id 参数
@router.get("/devices")
```

## 设计风格

2D 数字孪生拓扑升级采用「科技感数据中心指挥中心」风格：深色机房平面图底图，机柜网格以细线描边，机柜热力用蓝→青→黄→红渐变色块表现温度负载，能流用发光粒子沿管线流动。整体保持与现有平台一致的暗色主题，新增机房平面图背景层（楼层轮廓 + 冷/电通道标注），机柜悬停显示详情卡，故障节点红色脉冲扩散。交互：点击机柜聚焦、滚轮缩放、minimap 导航保持现状并适配新图层。

## 页面规划

仅增强现有「数字孪生拓扑」页面（TwinDashboard），不新增页面：

1. 顶部 KPI 与模型选择器（保持）
2. 机房平面图底图层（新增）：楼层轮廓 + 机柜行列网格 + 通道标注
3. 机柜热力气泡层（新增）：按设备温度聚合的热力色块 + 脉冲动画
4. 能流拓扑层（升级）：保留分层算法，粒子流光密度随负载变化
5. 详情卡与图例（升级）：机柜/设备详情、温度色阶图例、Dify 知识来源标注（助手页）

## Agent Extensions

### Skill

- **ui-ux-pro-max**
- Purpose: 为 2D 拓扑升级提供设计系统参考（配色、字体、间距、动效规范），确保视觉与现有平台一致且达到「生动具体」。
- Expected outcome: 生成适配数据中心主题的设计规范，指导 TopologyFlow.vue 机房平面图与热力配色实现。
- **lucide-icons**
- Purpose: 为拓扑图例、机柜状态、助手知识来源标注提供一致的 SVG 图标（不使用 emoji）。
- Expected outcome: 下载所需图标（如 Server、Thermometer、Activity、Database 等）并集成到增强组件。