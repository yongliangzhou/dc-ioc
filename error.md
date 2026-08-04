# dc-ioc-platform 问题清单与解决办法

> 基于 4 路并行代码审计 + 配置核验 + 电力监控模块深度改造经验生成。
> 覆盖前端 47 个视图、后端 API/服务层、构建配置与工程化。
> 优先级：P0（必须立即修）→ P1（本周）→ P2（两周内）→ P3（精修）

---

## 目录

- [一、安全性与后端架构](#一安全性与后端架构)
- [二、前端性能](#二前端性能)
- [三、代码质量与架构合理性](#三代码质量与架构合理性)
- [四、用户界面(UI)与交互体验(UX)](#四用户界面ui与交互体验ux)
- [五、功能完整性与数据处理](#五功能完整性与数据处理)
- [六、优化优先级矩阵](#六优化优先级矩阵)
- [七、实施路线图](#七实施路线图)

---

## 一、安全性与后端架构

### 问题 S-01：CORS 允许所有来源（🔴 高危 / P0）

**问题描述**
`backend/app/core/config.py` 中 CORS 配置 `allow_origins=["*"]`，任意网站可携带凭证跨域调用 API，存在 CSRF 攻击与数据泄露风险。

**涉及文件**
- `backend/app/core/config.py`
- `backend/app/main.py`

**解决办法**
改为白名单 + 环境变量配置：

```python
# config.py
class Settings(BaseSettings):
    CORS_ORIGINS: str = "http://localhost:5173"
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

# main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**实施步骤**
1. `config.py` 新增 `CORS_ORIGINS` 字段
2. `.env` 配置具体域名（开发 localhost:5173，生产实际域名）
3. `main.py` 使用白名单

**预期效果**：消除 CSRF/数据泄露面
**风险**：低（开发环境需配置 localhost）

---

### 问题 S-02：硬编码 Secret Key（🔴 高危 / P0）

**问题描述**
`backend/app/core/security.py` 中 JWT 密钥可能硬编码，泄露后可伪造任意 token，绕过认证。

**涉及文件**
- `backend/app/core/security.py`
- `backend/app/core/config.py`

**解决办法**
密钥从环境变量读取，启动时校验非默认值，生产用 >=32 字节随机串：

```python
# config.py
SECRET_KEY: str = ""
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = 480

# 启动校验
if not settings.SECRET_KEY or settings.SECRET_KEY == "changeme":
    raise RuntimeError("SECRET_KEY 未配置，禁止启动")
```

**实施步骤**
1. `config.py` 新增 `SECRET_KEY` 字段
2. `.env` 配置强随机密钥（`python -c "import secrets; print(secrets.token_urlsafe(48))"`）
3. `security.py` 读取 `settings.SECRET_KEY`
4. 启动时校验

**预期效果**：杜绝密钥泄露导致的 token 伪造
**风险**：低

---

### 问题 S-03：无全局异常处理中间件（🟠 高 / P1）

**问题描述**
`backend/app/main.py` 未注册 `@app.exception_handler(Exception)`，未捕获异常会返回 500 + 堆栈泄露，暴露内部实现。

**涉及文件**
- `backend/app/main.py`

**解决办法**
添加全局异常处理器，统一返回 `{code, message}`，记录日志但不向前端暴露堆栈：

```python
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.exception(f"Unhandled error: {request.url.path}")
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务内部错误，请稍后重试"},
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": exc.detail},
    )
```

**实施步骤**
1. `main.py` 注册全局异常处理器
2. 区分 HTTPException（业务错误）与 Exception（系统错误）
3. 日志记录完整堆栈，响应只返回通用 message

**预期效果**：防堆栈泄露 + 前端错误处理一致
**风险**：低

---

### 问题 S-04：模拟数据服务用于生产（🟠 高 / P1）

**问题描述**
`backend/app/services/dc_ioc_data.py` 返回内存随机生成的数据（如 `rnd()` 生成电压电流），非真实采集数据，若直接部署生产会误导运维。

**涉及文件**
- `backend/app/services/dc_ioc_data.py`

**解决办法**
明确标注为 demo 模式，增加 `DATA_SOURCE=mock|real` 开关：

```python
# config.py
DATA_SOURCE: str = "mock"  # mock | real

# service 层
if settings.DATA_SOURCE == "mock":
    return _mock_data()
return _real_data()  # 接入真实采集系统
```

**实施步骤**
1. config 增加 `DATA_SOURCE` 开关
2. dc_ioc_data.py 拆分 mock/real 两条路径
3. 接入真实采集时通过相同接口契约替换实现
4. 启动日志明确打印当前数据源

**预期效果**：避免模拟数据误用于生产决策
**风险**：中（需保证接口契约不变）

---

### 问题 S-05：登录接口未限流（🟠 高 / P1）

**问题描述**
`backend/app/core/ratelimit.py` 已定义限流中间件，但未在生产路由（尤其是登录接口）应用，存在暴力破解风险。

**涉及文件**
- `backend/app/core/ratelimit.py`
- `backend/app/api/v1/endpoints/auth.py`

**解决办法**
登录接口强制限流（如 5 次/分钟/IP）：

```python
from app.core.ratelimit import rate_limit

@router.post("/login")
@rate_limit(times=5, minutes=1)  # 每分钟最多 5 次
async def login(credentials: LoginRequest):
    ...
```

**实施步骤**
1. 确认 ratelimit 装饰器实现完整
2. 登录接口应用限流
3. 限流命中时返回 429 + Retry-After

**预期效果**：防暴力破解
**风险**：低

---

### 问题 S-06：RBAC 权限控制不完善（🟡 中 / P2）

**问题描述**
仅有认证（JWT 校验），缺角色权限校验，任何登录用户都能访问所有功能。

**涉及文件**
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/core/security.py`

**解决办法**
增加 `require_role` 装饰器/依赖：

```python
def require_role(*roles: str):
    async def dependency(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "权限不足")
        return user
    return dependency

@router.delete("/alarms/{id}")
async def delete_alarm(user: User = Depends(require_role("admin", "operator"))):
    ...
```

**实施步骤**
1. User model 增加 role 字段
2. 实现 `require_role` 依赖
3. 按端点敏感度逐步加权限校验

**预期效果**：最小权限原则
**风险**：低

---

### 问题 S-07：日志未过滤敏感信息（🟡 中 / P2）

**问题描述**
`backend/app/core/logging_config.py` 未过滤 password/token 字段，可能将敏感信息写入日志文件。

**涉及文件**
- `backend/app/core/logging_config.py`

**解决办法**
增加日志 filter，脱敏敏感字段：

```python
import re

class SensitiveFilter(logging.Filter):
    PATTERNS = {
        "password": re.compile(r'"password"\s*:\s*"[^"]*"'),
        "token": re.compile(r'(Bearer\s+)[^\s,]+'),
    }
    def filter(self, record):
        msg = str(record.msg)
        for key, pat in self.PATTERNS.items():
            msg = pat.sub(f'"{key}":"***"', msg)
        record.msg = msg
        return True
```

**实施步骤**
1. 实现 SensitiveFilter
2. logging_config 注册 filter
3. 审计现有日志调用点

**预期效果**：防敏感信息泄露到日志
**风险**：低

---

### 问题 S-08：DB 查询需审计参数化（🟡 中 / P1）

**问题描述**
虽有 alembic 迁移（`backend/alembic/versions/`），需确认所有查询走 ORM 参数化，禁止字符串拼接 SQL，存在 SQL 注入风险。

**涉及文件**
- `backend/app/api/v1/endpoints/*.py`
- `backend/app/services/*.py`

**解决办法**
全局审计 SQL 查询：
1. 搜索 `text(`、`execute(`、`f"SELECT`、`.format(` 等危险模式
2. 全部改为 ORM 参数化查询或 `text()` + bind params
3. ESLint/CI 加规则禁止裸字符串 SQL

**实施步骤**
1. `grep -rn "execute\|text\|SELECT\|INSERT\|UPDATE\|DELETE" backend/app/`
2. 逐个审查，替换危险写法
3. 加 CI 检查

**预期效果**：消除 SQL 注入
**风险**：低

---

## 二、前端性能

### 问题 P-01：echarts 全量引入（🟠 高 / P1）

**问题描述**
`frontend/package.json` 依赖 `echarts ^5.6.0` 全量引入，构建产物 `echarts.CkutTTYC.js` 达 1,036 kB（gzip 343 kB），占总体积 70%+。

**涉及文件**
- `frontend/package.json`
- `frontend/src/**/echarts` 相关 import

**解决办法**
改为按需引入：

```ts
// src/utils/echarts.ts
import * as echarts from "echarts/core"
import { LineChart, BarChart, GaugeChart, PieChart } from "echarts/charts"
import {
  GridComponent, TooltipComponent, LegendComponent,
  TitleComponent, DataZoomComponent,
} from "echarts/components"
import { CanvasRenderer } from "echarts/renderers"

echarts.use([
  LineChart, BarChart, GaugeChart, PieChart,
  GridComponent, TooltipComponent, LegendComponent,
  TitleComponent, DataZoomComponent, CanvasRenderer,
])
export default echarts
```

**实施步骤**
1. 统计项目用到的图表类型（LineChart/BarChart/GaugeChart/PieChart）与组件
2. 新建 `src/utils/echarts.ts` 按需注册
3. 全局替换 `import * as echarts from "echarts"` → `import echarts from "@/utils/echarts"`
4. 构建验证所有图表正常

**预期效果**：echarts 包预计降至 ~300 kB（gzip ~100 kB），首屏 -250 kB
**风险**：中（需确保所有用到的组件都已注册，否则运行时报错）

---

### 问题 P-02：大列表无虚拟滚动（🟠 高 / P2）

**问题描述**
- `frontend/src/views/monitor/PowerBattery.vue`：6 组 × 40~80 单体 = 480 个色块全量 `v-for` 渲染
- `frontend/src/views/ops/AlarmHistory.vue`：告警历史可能上千条全量渲染
- `frontend/src/components/monitor/DeviceTable.vue`：设备表全量渲染

**涉及文件**
- `frontend/src/views/ops/AlarmHistory.vue`
- `frontend/src/components/monitor/DeviceTable.vue`
- `frontend/src/views/monitor/PowerBattery.vue`

**解决办法**
- 电池单体色块（480 个）：加 `content-visibility: auto` 减少非可视区渲染（轻量方案）
- 告警历史/设备表：引入 `@tanstack/vue-virtual` 虚拟滚动

```ts
// 安装
npm i @tanstack/vue-virtual

// 使用
import { useVirtualizer } from "@tanstack/vue-virtual"
const rowVirtualizer = useVirtualizer({
  count: data.value.length,
  getScrollElement: () => scrollRef.value,
  estimateSize: () => 44,
})
```

**实施步骤**
1. 安装 `@tanstack/vue-virtual`
2. AlarmHistory 改造为虚拟滚动
3. DeviceTable 改造
4. PowerBattery 单体网格加 `content-visibility: auto`

**预期效果**：告警历史 1000 条时 DOM 节点从 10000+ 降至 ~50
**风险**：低

---

### 问题 P-03：请求层无缓存/防抖/重试/取消（🟡 中 / P2）

**问题描述**
`frontend/src/api/request.ts` axios 封装无缓存、防抖、错误重试、请求取消。

**涉及文件**
- `frontend/src/api/request.ts`

**解决办法**
- GET 请求增加短时缓存（相同 URL 5s 内复用响应）
- 搜索类输入加 debounce
- 网络错误自动重试 1 次
- 路由切换时用 AbortController 取消未完成请求

```ts
// 简易 GET 缓存
const cache = new Map<string, { data: unknown; ts: number }>()
const CACHE_TTL = 5000

request.get = (url, config) => {
  const cached = cache.get(url)
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return Promise.resolve(cached.data)
  }
  return axios.get(url, config).then(res => {
    cache.set(url, { data: res, ts: Date.now() })
    return res
  })
}
```

**实施步骤**
1. request.ts 增加 GET 缓存层
2. 增加 retry 拦截器（仅网络错误，最多 1 次）
3. 提供 `useDebouncedRequest` composable
4. 路由切换时取消待请求

**预期效果**：减少冗余请求，提升响应感
**风险**：低

---

### 问题 P-04：轮询定时器未统一管理（🟡 中 / P2）

**问题描述**
监控类页面常用 `setInterval` 轮询数据，需确认所有页面 `onUnmounted` 时 `clearInterval`，否则切页面后内存泄漏 + 鬼请求。

**涉及文件**
- `frontend/src/views/monitor/*.vue`（轮询页面）

**解决办法**
封装 `usePolling` composable，自动管理生命周期：

```ts
// src/composables/usePolling.ts
export function usePolling(fn: () => Promise<void>, interval: number) {
  let timer: number | null = null
  const start = () => { fn(); timer = window.setInterval(fn, interval) }
  const stop = () => { if (timer) { clearInterval(timer); timer = null } }
  onMounted(start)
  onUnmounted(stop)
  return { start, stop }
}
```

**实施步骤**
1. 新建 `usePolling.ts`
2. 审计所有 `setInterval` 调用点
3. 逐步替换为 `usePolling`

**预期效果**：杜绝定时器泄漏
**风险**：低

---

### ✅ 已做得好的部分（保持）

`frontend/vite.config.ts` 已配置：
- manualChunks 分包（echarts/vue/axios 独立）
- gzip + brotli 预压缩
- hash 文件名（强缓存友好）
- 路由全懒加载（`router/index.ts` 所有页面 `() => import()`）

这部分质量高，保持即可。

---

## 三、代码质量与架构合理性

### 问题 Q-01：全模块大量重复代码（🔴 高 / P1）—— 不止 Power 系列

**问题描述**
经全项目审计，重复代码是**全局性问题**，远超 Power 系列，覆盖 Power/Network/Hvac/Security/ops 全部模块。最严重的是：**4 个公共组件已存在但引用 0 次**，所有页面都在重复造轮子。

#### 重复证据（实测数据）

**① 公共组件已存在但完全未使用**
| 公共组件 | 引用次数 | 说明 |
|---------|---------|------|
| `Panel.vue`（卡片容器） | **0 次** | 17 个文件各自重写 `.card`/`.card-head` |
| `ViewHead.vue`（页头） | **0 次** | 所有页面各自重写 `.view-head` |
| `KvsPanel.vue`（KV 面板） | **0 次** | 13 个文件各自重写 `.kv-grid` |
| `ErrorBoundary.vue`（错误边界） | **0 次** | 各页面手写 try-catch + error 展示 |
| `MetricCard.vue`（指标卡） | 65 次 | ✅ 唯一被充分使用的公共组件 |

**② 工具函数重复（同名）**
| 函数 | 重复次数 | 分布模块 |
|------|---------|---------|
| `fmt` | **23 处 / 18 文件** | Power×5 + Network×4 + Hvac×1 + ops×3 + admin/energy/overview×3 |
| `fmtNum` | 4 处 | Network 系列（Firewalls/Routers/Switches/Wireless） |
| `fmtBps` | 4 处 | Network 系列（同上 4 文件） |
| `genHours` | 5 处 | Network 系列 + 其他 |
| `pct` | 3 处 | Network Dashboard 等 |
| `breakerCls` | 3 处 | Power 系列 |
| `loadCls` | 3 处 | Power 系列 |
| `tempCls` | 3 处 | Power 系列 |
| `pfCls` | 3 处 | Power 系列 |
| `formatTime` | 2 处 | HvacCrac / HvacLiquid |
| `utilCls` | 2 处 | NetworkRouters / NetworkSwitches |
| `genTimeData` | 2 处 | NetworkFirewalls / NetworkRouters |
| `barCls` | 2 处 | Network 系列 |

**③ 工具函数重复（同功能异名）—— Hvac 系列最典型**
| 功能 | Power 叫法 | Hvac 叫法 | Network 叫法 |
|------|-----------|----------|-------------|
| 数值格式化 | `fmt` | `numVal`/`formatVal`/`fv` | `fmtNum`/`ms` |
| 时间格式化 | — | `formatTime` | — |
| 状态着色 | `breakerCls`/`loadCls` | `statusRow` | `utilCls`/`barCls` |

**④ CSS 类重复（按文件数）**
| CSS 类 | 重复文件数 | 说明 |
|--------|-----------|------|
| `.muted` | 19 文件 | 通用灰色文字 |
| `.card-head` | 17 文件 | 卡片标题栏（Panel.vue 已有但没用） |
| `.ct`/`.section-title`/`.tag`/`.mono`/`.redundancy` | 13 文件 | 知识库+表格通用样式 |
| `.d-name`/`.chip` | 9 文件 | 设备名+标签 |
| `.tag.g`/`.tag.a`/`.tag.r`/`.tag.b` | 7 文件 | 状态标签 4 色（每文件重写一遍） |
| `.pill` | 62 处 | 状态药丸 |

**⑤ 知识库渲染块重复**（`.section-title`/`.redundancy`/`.logic-list`）
13 个文件各自复制了"阈值/架构/逻辑/故障锁定"4 段完全相同的模板（Power×5 + Network×4 + Hvac + Security + 其他）。

**涉及文件**（按模块系列）
- **Power 系列（5 文件）**：`PowerHv.vue`/`PowerLv.vue`/`PowerGenset.vue`/`PowerFuel.vue`/`PowerBattery.vue`
- **Network 系列（4 文件）**：`NetworkRouters.vue`/`NetworkFirewalls.vue`/`NetworkSwitches.vue`/`NetworkWireless.vue`
- **Hvac 系列（3 文件）**：`HvacChiller.vue`/`HvacCrac.vue`/`HvacLiquid.vue`
- **Security 系列（4 文件）**：`SecurityFire.vue`/`SecurityCctv.vue`/`SecurityAcs.vue`/`SecurityIds.vue`
- **ops 系列**：`Alarms.vue`/`AlarmHistory.vue`/`Maintenance.vue`/`AuditLogs.vue`/`EnergyDashboard.vue`/`Index.vue`

#### 解决办法

**第一层：启用已有公共组件（立即可做，0 新代码）**
```vue
<!-- 替换前：每页重写 -->
<div class="view-head"><h1>...</h1></div>
<div class="card"><div class="card-head">...</div></div>

<!-- 替换后：用已有组件 -->
<ViewHead title="..." subtitle="..." />
<Panel title="..." pill="...">...</Panel>
```

**第二层：抽取通用 composable + 样式**
```
frontend/src/
├── components/common/
│   ├── Panel.vue              ✅ 已有, 启用即可
│   ├── ViewHead.vue           ✅ 已有, 启用即可
│   ├── KvsPanel.vue           ✅ 已有, 启用即可
│   ├── ErrorBoundary.vue      ✅ 已有, 启用即可
│   └── KnowledgePanel.vue     ← 新建: 知识库 4 合 1 (thresholds/arch/logic/faults)
├── composables/
│   ├── useFormat.ts           ← 新建: fmt/fmtNum/fmtBps/fmtEnergy/formatTime/pct (全局通用)
│   └── useStatusColor.ts      ← 新建: breakerCls/loadCls/tempCls/pfCls/utilCls/barCls (状态着色)
└── styles/
    └── common.css             ← 新建: .muted/.d-name/.mono/.tag/.pill/.chips/.section-title (全局共享)
```

```ts
// useFormat.ts —— 统一所有格式化函数
export function useFormat() {
  const fmt = (v: number | null | undefined, dp = 2) =>
    v == null || !Number.isFinite(v) ? '-' : Number(v).toFixed(dp)
  const fmtNum = (n: number) => fmt(n, 0)
  const fmtBps = (bps: number) => {
    if (bps >= 1e9) return (bps / 1e9).toFixed(2) + ' Gbps'
    if (bps >= 1e6) return (bps / 1e6).toFixed(2) + ' Mbps'
    return (bps / 1e3).toFixed(2) + ' Kbps'
  }
  const fmtEnergy = (v: number | null) => v == null ? '-' : Math.round(v).toLocaleString()
  const formatTime = (t?: string) => t || '-'
  const pct = (v: number | null) => v == null ? 0 : Number(v.toFixed(1))
  return { fmt, fmtNum, fmtBps, fmtEnergy, formatTime, pct }
}

// useStatusColor.ts —— 统一状态着色
export function useStatusColor() {
  const loadCls = (load: number) => load >= 90 ? 'r-text' : load >= 80 ? 'a-text' : 'g-text'
  const tempCls = (t: number, warn: number, alarm: number) =>
    t >= alarm ? 'r-text' : t >= warn ? 'a-text' : 'g-text'
  const pfCls = (pf: number) => pf >= 0.95 ? 'g-text' : pf >= 0.9 ? 'a-text' : 'r-text'
  const utilCls = (v: number) => v > 85 ? 'r-text' : v > 60 ? 'a-text' : 'g-text'
  const breakerCls = (v: string) => isClosed(v) ? 'g' : v.includes('分') ? 'b' : 'a'
  return { loadCls, tempCls, pfCls, utilCls, breakerCls }
}
```

```vue
<!-- KnowledgePanel.vue —— 13 文件的知识库块合 1 -->
<template>
  <div v-if="knowledge?.thresholds?.length"><!-- 阈值 --></div>
  <div v-if="knowledge?.arch"><!-- 架构 --></div>
  <div v-for="g in knowledge?.logic"><!-- 逻辑 --></div>
  <div v-if="knowledge?.faults?.length"><!-- 故障锁定 --></div>
</template>
```

#### 实施步骤

**阶段 1：启用已有公共组件（0.5d，最高 ROI）**
1. 全局替换 `.view-head` → `<ViewHead>`
2. 全局替换 `.card`/`.card-head` → `<Panel>`
3. 全局替换 `.kv-grid` → `<KvsPanel>`
4. 关键页面外层包 `<ErrorBoundary>`

**阶段 2：抽通用 composable（1d）**
1. 新建 `useFormat.ts`，合并 fmt/fmtNum/fmtBps/fmtEnergy/formatTime/pct（23+4+4+5+3+2 处 → 1 处）
2. 新建 `useStatusColor.ts`，合并 breakerCls/loadCls/tempCls/pfCls/utilCls/barCls（3+3+3+3+2+2 处 → 1 处）
3. 逐文件替换并 `vue-tsc` 验证

**阶段 3：抽共享 CSS + 知识库组件（1d）**
1. 新建 `common.css`，提取 `.muted`/`.d-name`/`.mono`/`.tag`/`.pill`/`.chips`/`.section-title`（13-19 文件 → 1 处）
2. 新建 `KnowledgePanel.vue`，13 文件知识库块合 1
3. 逐文件替换并 `vite build` 验证

**预期效果**
- 减少重复代码 **~4000+ 行**（远超原估的 1500 行）
- 23 处 `fmt` → 1 处，4 处 `fmtBps` → 1 处，13 处知识库块 → 1 组件
- 17 处 `.card-head` → Panel 组件，19 处 `.muted` → common.css
- 后续任何样式/格式调整改 1 处即可全局生效

**风险**：低（纯重构，类型检查 + 构建验证保障；阶段 1 是启用已有组件，几乎零风险）

---

### 问题 Q-02：无代码规范工具 ESLint/Prettier/Husky（🟠 高 / P1）

**问题描述**
项目完全无 ESLint/Prettier/Husky/lint-staged 配置，代码风格依赖人工维护，94 处 `any` 无约束。

**涉及文件**
- `frontend/package.json`（devDependencies 缺失）

**解决办法**
```bash
npm i -D eslint @vue/eslint-config-typescript @vue/eslint-config-prettier prettier husky lint-staged
```

```js
// eslint.config.js
import vueTs from '@vue/eslint-config-typescript'
import vuePrettier from '@vue/eslint-config-prettier'
export default [
  vueTs,
  vuePrettier,
  { rules: {
    'no-unused-vars': 'error',
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/consistent-type-imports': 'error',
  }},
]
```

```json
// .prettierrc
{ "semi": false, "singleQuote": true, "printWidth": 100, "tabWidth": 2 }
```

```json
// package.json
"lint-staged": {
  "*.{ts,vue}": ["eslint --fix", "prettier --write"]
}
```

**实施步骤**
1. 安装依赖
2. 写配置
3. `npx eslint --fix .` 一次性修复
4. `npx husky init` + 加 pre-commit hook

**预期效果**：杜绝风格分歧，拦截 any 滥用
**风险**：低（首次 fix 可能改动较多文件，建议单独提交）

---

### 问题 Q-03：测试覆盖率低（🟠 高 / P2）

**问题描述**
仅 10 个测试文件，47 个视图 + 后端数十个 endpoint，覆盖率明显不足。已配 vitest + @vue/test-utils 但未充分利用。

**涉及文件**
- `frontend/src/**/*.test.ts`（仅 10 个）
- `frontend/vitest.config.ts`

**解决办法**
优先补齐核心模块测试：
- 前端：`power.ts` 的 mapper 函数（纯函数易测）、公共组件、store
- 后端：auth endpoint、告警引擎、数据服务契约
- 目标：核心 service/util 覆盖率 ≥ 70%

```ts
// power.test.ts 示例
import { mapHvDetailed } from '@/api/power'
describe('mapHvDetailed', () => {
  it('空数据返回默认结构', () => {
    const r = mapHvDetailed({})
    expect(r.incomers).toEqual([])
    expect(r.total).toBe(0)
  })
  it('正确映射进线', () => {
    const r = mapHvDetailed({ incomers: [{ id: 'I-01', u: 10.5 }] })
    expect(r.incomers).toHaveLength(1)
  })
})
```

**实施步骤**
1. 前端：先补 `power.ts` mapper 测试（纯函数最高 ROI）
2. 后端：补 auth + alarm_engine 测试
3. CI 加 `npm run test:run` 门禁

**预期效果**：回归保障
**风险**：低

---

### 问题 Q-04：TypeScript any 使用过多（🟡 中 / P2）

**问题描述**
94 处 `: any` / `as any`，主要集中在 `request.ts` 响应类型与 `power.ts` 的 `RawItem`。

**涉及文件**
- `frontend/src/api/request.ts`
- `frontend/src/api/power.ts`
- `frontend/src/types/index.ts`

**解决办法**
逐步用 `unknown` + 类型守卫替代 `any`；API 响应定义具体 response 类型：

```ts
// 替换前
function mapHv(raw: any): HvSummary

// 替换后
type RawItem = Record<string, unknown>
function mapHv(raw: RawItem): HvSummary
```

**实施步骤**
1. `request.ts` 响应类型从 `any` 改 `unknown`
2. 各 mapper 的 `RawItem` 明确化
3. ESLint `no-explicit-any` 规则逐步从 warn 升 error

**预期效果**：类型安全提升
**风险**：低

---

## 四、用户界面(UI)与交互体验(UX)

### 问题 U-01：交互态处理不一致（🟠 高 / P2）

**问题描述**
部分页面有 `加载中/加载失败` 三态，部分页面直接渲染无 loading。PowerXxx 系列有完整三态，但其他页面不统一。

**涉及文件**
- `frontend/src/views/**/*.vue`（多处）

**解决办法**
封装 `<AsyncState>` 包装组件，统一三态渲染：

```vue
<!-- src/components/common/AsyncState.vue -->
<template>
  <div v-if="loading" class="loading"><slot name="loading">加载中...</slot></div>
  <div v-else-if="error" class="error"><slot name="error" :error="error">{{ error }}</slot></div>
  <div v-else-if="empty" class="empty"><slot name="empty">暂无数据</slot></div>
  <slot v-else />
</template>
```

**实施步骤**
1. 新建 `AsyncState.vue`
2. 逐页替换加载/错误/空态逻辑
3. 统一样式

**预期效果**：交互体验一致
**风险**：低

---

### 问题 U-02：i18n 硬编码中文（🟠 高 / P2）

**问题描述**
电力页面大量 chips/表头硬编码中文（如 `'三相电压 Ua/Ub/Uc'`、`'进线开关'`），未走 `tl()`。语言文件 key 覆盖不全。

**涉及文件**
- `frontend/src/views/monitor/Power*.vue`
- `frontend/src/locales/zh-CN.json` / `en-US.json`

**解决办法**
- 短期：表头/chips 等固定文案补 `tl()`
- 长期：写脚本扫描 `.vue` 模板中裸中文，输出待补清单

```bash
# 扫描裸中文
grep -rnP '[\x{4e00}-\x{9fff}]' frontend/src/views --include='*.vue' | grep -v "tl(" | grep -v '<!--'
```

**实施步骤**
1. 运行扫描脚本生成待补清单
2. 逐个替换为 `tl('key')`
3. 同步补 zh-CN.json / en-US.json
4. CI 加 i18n 完整性检查

**预期效果**：多语言完整可切换
**风险**：低

---

### 问题 U-03：可访问性缺失（🟡 中 / P3）

**问题描述**
全项目 aria 属性稀少，表格无 `caption`/`scope`，图标按钮无 `aria-label`，颜色告警仅靠色差无文字冗余（色盲不友好）。

**涉及文件**
- `frontend/src/**/*.vue`（全局）

**解决办法**
- 表格加 `<caption>` + `<th scope="col">`
- 图标按钮加 `aria-label`
- 告警状态 `tag` 同时用色+文字（已有文字，保持）
- 大页面加 `tabindex` 与键盘聚焦样式
- 颜色对比度检查（WCAG AA 标准 4.5:1）

**实施步骤**
1. 表格语义化（caption/scope）
2. 图标按钮补 aria-label
3. 键盘导航支持
4. 对比度审计

**预期效果**：符合 WCAG AA
**风险**：低

---

### 问题 U-04：响应式设计不完善（🟡 中 / P3）

**问题描述**
部分页面有 `@media (max-width: 1180px)`，部分无。大表格在小屏溢出。

**涉及文件**
- `frontend/src/views/**/*.vue`（部分无 media query）

**解决办法**
- 统一 `scroll-x` 处理表格溢出（电力页面已做，其他页面补齐）
- 关键页面增加断点适配
- 大屏 dashboard 适配（1920/2560）

**实施步骤**
1. 审计无 media query 的页面
2. 表格统一加 `scroll-x`
3. 补断点

**预期效果**：多终端适配
**风险**：低

---

### 问题 U-05：表单验证不统一（🟡 中 / P2）

**问题描述**
项目使用了多个不同的验证方式，缺乏统一验证规则或组件。

**涉及文件**
- `frontend/src/views/ops/Equipment.vue`
- `frontend/src/views/ops/Assistant.vue`
- `frontend/src/views/auth/Login.vue`

**解决办法**
封装统一表单验证 composable：

```ts
// src/composables/useFormValidation.ts
export const rules = {
  required: (msg = '必填') => (v: unknown) => !!v || msg,
  email: (v: string) => /^[^@]+@[^@]+\.[^@]+$/.test(v) || '邮箱格式错误',
  phone: (v: string) => /^1\d{10}$/.test(v) || '手机号格式错误',
}
```

**实施步骤**
1. 新建 `useFormValidation.ts`
2. 统一各表单调用
3. 错误提示样式统一

**预期效果**：表单体验一致
**风险**：低

---

## 五、功能完整性与数据处理

### 问题 F-01：实时数据推送未全面应用（🟡 中 / P3）

**问题描述**
告警有 WS（`frontend/src/stores/modules/alarms.ts` store 有 WS 连接），但电力/环境监控用轮询，实时性不足。

**涉及文件**
- `frontend/src/stores/modules/alarms.ts`
- `frontend/src/views/monitor/*.vue`

**解决办法**
高频变化数据（告警、实时电参量）走 WS 推送，低频走轮询：

**实施步骤**
1. 后端扩展 WS 通道（电力实时数据）
2. 前端复用 alarms.ts 的 WS 模式
3. 高频数据切 WS，低频保留轮询

**预期效果**：实时性提升
**风险**：中（需后端配合）

---

### 问题 F-02：错误边界组件缺失（🟡 中 / P2）

**问题描述**
部分页面未使用统一的错误处理组件或逻辑，组件级错误会导致整页白屏。

**涉及文件**
- `frontend/src/views/**/*.vue`（部分）

**解决办法**
使用 Vue `onErrorCaptured` + 错误边界组件：

```vue
<!-- ErrorBoundary.vue -->
<template>
  <slot v-if="!error" />
  <div v-else class="error-boundary">
    <p>组件加载失败</p>
    <button @click="error = null">重试</button>
  </div>
</template>
<script setup>
import { onErrorCaptured, ref } from 'vue'
const error = ref(null)
onErrorCaptured((e) => { error.value = e; return false })
</script>
```

**实施步骤**
1. 新建 `ErrorBoundary.vue`
2. 关键页面外层包裹
3. 上报错误到监控

**预期效果**：避免整页白屏
**风险**：低

---

### 问题 F-03：依赖版本锁定与安全审计（🟡 中 / P2）

**问题描述**
需确认 `package.json` 与 `requirements.txt` 依赖是否有版本锁定，是否有已知漏洞依赖。

**涉及文件**
- `frontend/package.json`
- `backend/requirements.txt`

**解决办法**
- 前端：`npm audit` 修复漏洞，锁定 `package-lock.json`
- 后端：`pip-audit` 检查，使用 `pip-tools` 锁定

**实施步骤**
1. `npm audit` + `pip-audit`
2. 修复高危漏洞
3. CI 加自动化审计

**预期效果**：依赖安全
**风险**：低

---

## 六、优化优先级矩阵

| 优先级 | 编号 | 优化项 | 工作量 | 预期收益 | 风险 |
|--------|------|--------|--------|---------|------|
| **P0** | S-01 | CORS 白名单 | 0.5d | 消除高危漏洞 | 低 |
| **P0** | S-02 | 密钥环境变量 | 0.5d | 防 token 伪造 | 低 |
| **P1** | S-03 | 全局异常处理 | 0.5d | 防堆栈泄露 | 低 |
| **P1** | S-04 | 模拟数据开关 | 1d | 防误用 | 中 |
| **P1** | S-05 | 登录限流 | 0.5d | 防爆破 | 低 |
| **P1** | S-08 | SQL 参数化审计 | 1d | 防 SQL 注入 | 低 |
| **P1** | P-01 | echarts 按需引入 | 1d | 首屏 -250kB | 中 |
| **P1** | Q-01 | PowerXxx 公共抽取 | 2d | 减 1500 行重复 | 低 |
| **P1** | Q-02 | ESLint+Prettier+Husky | 1d | 风格统一 | 低 |
| **P2** | S-06 | RBAC 权限 | 2d | 最小权限 | 低 |
| **P2** | S-07 | 日志脱敏 | 0.5d | 防信息泄露 | 低 |
| **P2** | P-02 | 虚拟滚动 | 1d | 大列表流畅 | 低 |
| **P2** | P-03 | 请求层缓存/防抖 | 1d | 减冗余请求 | 低 |
| **P2** | P-04 | 轮询 composable | 1.5d | 防泄漏 | 低 |
| **P2** | Q-03 | 补核心测试 | 2d | 回归保障 | 低 |
| **P2** | Q-04 | any 类型治理 | 1d | 类型安全 | 低 |
| **P2** | U-01 | 交互态组件 | 1d | 体验一致 | 低 |
| **P2** | U-02 | i18n 补全 | 1d | 多语言完整 | 低 |
| **P2** | U-05 | 表单验证统一 | 1d | 体验一致 | 低 |
| **P2** | F-02 | 错误边界 | 0.5d | 防白屏 | 低 |
| **P2** | F-03 | 依赖安全审计 | 0.5d | 依赖安全 | 低 |
| **P3** | U-03 | 可访问性 | 2d | 合规 | 低 |
| **P3** | U-04 | 响应式补齐 | 1.5d | 多终端 | 低 |
| **P3** | F-01 | WS 实时推送 | 2d | 实时性 | 中 |

---

## 七、实施路线图

### 第一周：P0 安全加固（2d）
- [ ] S-01 CORS 白名单
- [ ] S-02 密钥环境变量

立即消除高危项。

### 第二周：P1 性能与工程化（6.5d）
- [ ] S-03 全局异常处理
- [ ] S-05 登录限流
- [ ] S-08 SQL 参数化审计
- [ ] S-04 模拟数据开关
- [ ] P-01 echarts 按需引入
- [ ] Q-01 PowerXxx 公共代码抽取
- [ ] Q-02 ESLint+Prettier+Husky

### 第三~四周：P2 体验与质量（12d）
- [ ] P-02 虚拟滚动
- [ ] P-03 请求层增强
- [ ] P-04 轮询 composable
- [ ] Q-03 补核心测试
- [ ] Q-04 any 治理
- [ ] U-01 交互态组件
- [ ] U-02 i18n 扫描补全
- [ ] U-05 表单验证统一
- [ ] S-06 RBAC
- [ ] S-07 日志脱敏
- [ ] F-02 错误边界
- [ ] F-03 依赖审计

### 第五周+：P3 精修（5.5d）
- [ ] U-03 可访问性
- [ ] U-04 响应式补齐
- [ ] F-01 WS 实时推送

---

> **总计**：24 项优化，预计 26 人天。
> 建议从 P0 安全加固起步，两周内完成 P1，可将项目从"功能完备但工程粗糙"提升至"可生产交付"水准。
