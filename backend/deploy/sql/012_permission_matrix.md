# 5.4.2 权限矩阵（RBAC 设计）

> 基于 `app/core/deps.py` 的 `RoleChecker` / `PermissionChecker` 与 `app/models/user.py` 的角色模型。

## 1. 角色定义

| 角色 (role.name) | 标签 | 能力范围 |
| --- | --- | --- |
| `admin` | 系统管理员 | 全部读写 + 用户/角色管理 + 系统配置 |
| `operator` | 运维操作员 | 业务读写（工单/告警/知识库/巡检/演练/值班/风险） |
| `viewer` | 只读访客 | 全部只读查询（监控/拓扑/告警查看） |
| `is_superuser=True` | 超级用户 | 绕过所有角色/权限校验（任意角色） |

> 鉴权优先级：`is_superuser` > 角色名匹配 > 权限串匹配（`Role.permissions` JSON）。

## 2. 接口权限矩阵

| 模块 | 接口 | 读 (viewer) | 写 (operator) | 管理 (admin) |
| --- | --- | --- | --- | --- |
| 认证 | `GET /api/auth/me` | ✅ | ✅ | ✅ |
| 认证 | `POST /api/auth/login` | 公开（无 token） | | |
| 认证 | `POST /api/auth/refresh` | 公开（refresh token） | | |
| 认证 | `POST /api/auth/change-password` | ✅(本人) | ✅(本人) | ✅ |
| 用户 | `GET /api/auth/users` | ❌ | ❌ | ✅ |
| 用户 | `POST /api/auth/users` | ❌ | ❌ | ✅ |
| 用户 | `DELETE /api/auth/users/{id}` | ❌ | ❌ | ✅ |
| 监控 | `GET /api/metrics/*` | ✅ | ✅ | ✅ |
| 拓扑 | `GET /api/external/devices` | ✅ | ✅ | ✅ |
| 拓扑 | `GET /api/external/thing-models` | ✅ | ✅ | ✅ |
| 告警 | `GET /api/alarms/*` (查看) | ✅ | ✅ | ✅ |
| 告警 | `POST /api/alarms/*` (确认/处置) | ❌ | ✅ | ✅ |
| 工单 | `GET /api/ops/tickets` | ✅ | ✅ | ✅ |
| 工单 | `POST/PUT/PATCH/DELETE /api/ops/tickets` | ❌ | ✅ | ✅ |
| 知识库 | `GET /api/knowledge/*` | ✅ | ✅ | ✅ |
| 知识库 | `POST/PUT/DELETE /api/knowledge/*` | ❌ | ✅ | ✅ |
| 知识库 | `POST /api/knowledge/import` | ❌ | ✅ | ✅ |
| 巡检 | `GET /api/inspection/*` | ✅ | ✅ | ✅ |
| 巡检 | `POST/PUT/DELETE /api/inspection/*` | ❌ | ✅ | ✅ |
| 演练 | `GET /api/drill/*` | ✅ | ✅ | ✅ |
| 演练 | `POST/PUT/DELETE /api/drill/*` | ❌ | ✅ | ✅ |
| 值班 | `GET /api/shift/*` | ✅ | ✅ | ✅ |
| 值班 | `POST/PUT/DELETE /api/shift/*` | ❌ | ✅ | ✅ |
| 风险 | `GET /api/risk/*` | ✅ | ✅ | ✅ |
| 风险 | `POST/PUT/DELETE /api/risk/*` | ❌ | ✅ | ✅ |
| 运维 | 设备/资产 CRUD (`/api/ops/*`) | ❌ | ✅ | ✅ |
| 助手 | `GET /api/ops/assistant/*` | ✅ | ✅ | ✅ |
| 审计 | `GET /api/audit/*` | ❌ | ❌ | ✅ |

## 3. 权限粒度说明

- **读操作**：统一 `Depends(get_current_user)`，即任何已登录用户（含 viewer）可读。
- **业务写操作**：统一 `Depends(require_role("admin", "operator"))`。
- **账户/用户管理**：`Depends(require_role("admin"))`，viewer/operator 不可操作。
- **细粒度权限（可选）**：`Role.permissions` 支持 JSON 权限串（如 `alarm:write`），通过 `require_permission(...)` 使用，当前各接口以角色为主，预留细粒度扩展。

## 4. 种子角色（见 `seed_admin.py`）

```text
admin    -> is_superuser=True, 可管理用户/系统
operator -> 业务读写, 不可管理用户
viewer   -> 只读
```

## 5. 安全建议（后续）

1. viewer 不应出现在任何写接口（已满足）。
2. 敏感接口（用户删除、配置导出）建议增加二次确认/审计日志（审计中间件已覆盖写入 `audit_logs`）。
3. 定期审查 `roles.permissions` JSON，避免权限膨胀。
