# ADR-0003: JWT/RBAC 与 X-Collector-Token 双鉴权

- 状态: 已接受
- 日期: 2026-07-23
- 决策者: 平台架构 / 安全

## 背景

系统有两类调用方：①浏览器用户（登录、按角色访问 60+ 页面）；②无人值守采集器/外部系统（高频 `POST /api/external/*`，没有交互式登录，且可能部署在隔离网络）。要求：采集器凭证泄露不影响用户体系；用户 Token 泄露不能伪造测点；生产环境不允许弱默认密钥。

## 决策

| 通道 | 凭证 | 校验位置 | 授权 |
|---|---|---|---|
| 浏览器 | `Authorization: Bearer <JWT>` | `app/core/deps.py::get_current_user` | RBAC：`admin` / `operator` / `viewer`，写操作用 `require_role("admin","operator")` |
| 采集器 | `X-Collector-Token: <token>` | `app/api/v1/endpoints/external.py` | 仅 `/api/external/*`，不叠加登录依赖 |
| Dify 工具回调 | 独立 Bearer `DIFY_TOOL_KEY` | `endpoints/dify_tools.py` | 仅 `/api/ops/dify/tools/*` |

- `api_router` 对业务域统一挂 `_auth = [Depends(get_current_user)]`，`external` / `dify_tools` 显式排除。
- JWT 支持 refresh（前端 401 自动刷新）；自助注册固定 `viewer` 且默认关闭（`ALLOW_SELF_REGISTER`）。
- `app/core/secret_check.py` 在 prod 启动时拒绝 `SECRET_KEY < 16` 字符、默认 admin 密码、空的 `EXTERNAL_COLLECTOR_TOKEN`。
- 审计：写操作由 `AuditMiddleware` 记录，敏感表由 DB 触发器做行级审计。

## 备选方案

| 方案 | 优点 | 否决原因 |
|---|---|---|
| 给采集器建一个「服务账号」走同一 JWT | 一套体系 | Token 过期/轮换对无人值守设备不友好；权限粒度会意外放大到业务端点 |
| mTLS 双向证书 | 安全性最高 | Docker Compose 单机部署与第三方采集器接入成本过高，v1 不现实 |
| 无鉴权内网信任 | 简单 | 违反生产安全基线，`secret_check` 明确禁止 |

## 后果

### 正面
- 凭证隔离：采集器令牌泄露不会获得页面访问权限。
- 认证逻辑集中在依赖注入，端点只需声明 `dependencies`。

### 负面 / 需承担的成本
- 三套凭证需在 `.env.example` / 部署文档中逐一说明，轮换流程要分别维护。
- RBAC 是角色级而非对象级；阶段四前**没有行级租户隔离**（`tenant_id` 预留但不过滤）。
- 阶段四引入 `tenant_context` 后，需保证 JWT 中的 `tenant_id` 不可由客户端 `X-Tenant-Id` 越权覆盖（仅 admin 可跨租户）。

### 后续动作
- 阶段四 ADR 补充：多租户行级隔离与 `without_tenant_filter()` 豁免边界。
- 长期可评估采集器 Token 的按设备粒度与自动轮换。
