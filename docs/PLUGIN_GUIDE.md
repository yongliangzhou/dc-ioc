# 插件开发指南（阶段四）

目标：**新增一个页面不再需要改 `DefaultLayout.vue` 的 `nav` 硬编码**，只需在后端插件清单注册。

## 架构

```text
backend/app/core/plugin_registry.py (BUILTIN_PLUGINS)
        │  可选覆盖: backend/plugins.json
        ▼
GET /api/plugins/manifest  ──►  frontend/src/plugins/manifest.ts
        │                            │ 接口失败 → FALLBACK_MANIFEST
        ▼                            ▼
                      mergePluginNav(staticNav, plugins, t)
                                    ▼
                       DefaultLayout.vue 的 nav computed
```

约束：

1. 路由仍需在 `frontend/src/router/index.ts` 注册（Vue Router 必须静态/动态导入知道组件）。
2. i18n 键仍需双语同步（`scripts/check_i18n_keys.py` 门禁）。
3. 图标仍需在 `NavIcon.vue` 的 `ICONS` 中存在（缺失会静默回退成圆圈）。
4. 导航**不需要**手工加项；`group` 必须是 `DefaultLayout.vue` 中已有的稳定分组 id：`overview` / `facility` / `alarm` / `ops` / `asset` / `energy` / `knowledgeAi` / `platform` / `system`。
5. `scripts/check_nav_routes.py` 会校验「菜单路径 ↔ 路由」一一对应，CI 有死链即失败。

## 完整示例：新增「容量报表」页面

### 1. 前端页面 + 路由

```vue
<!-- frontend/src/views/ops/CapacityReport.vue -->
<template><div class="p3-page"><h1>{{ t('capacityReport.title') }}</h1></div></template>
<script setup lang="ts">
import { useI18n } from 'vue-i18n'
const { t } = useI18n()
</script>
```

```ts
// frontend/src/router/index.ts (children 内)
{
  path: 'ops/capacity-report',
  component: () => import('@/views/ops/CapacityReport.vue'),
  meta: { title: '容量报表', requiredRoles: ['admin', 'operator'] },
}
```

### 2. i18n 双语键

`zh-CN.json` / `en-US.json` 同步新增 `nav.capacityReport` 与 `capacityReport.title`。

### 3. 后端注册清单

在 `backend/app/core/plugin_registry.py` 的 `BUILTIN_PLUGINS` 追加：

```python
{
    "id": "capacity-report", "group": "asset", "path": "/ops/capacity-report",
    "icon": "BarChart3", "i18nKey": "nav.capacityReport",
    "requiredRoles": ["admin", "operator"], "enabled": True,
},
```

### 4. 离线兜底清单

在 `frontend/src/plugins/manifest.ts` 的 `FALLBACK_MANIFEST` 追加同 `id`/`path` 的项（后端不可达时仍可导航）。

### 5. 验证

```bash
python scripts/check_nav_routes.py --strict   # 0 死链 / 0 孤儿路由
python scripts/check_i18n_keys.py --json      # 0 缺失
cd frontend && npx vue-tsc --noEmit && npm run build
```

## 部署方覆盖（无需改代码）

创建 `backend/plugins.json`：

```json
{
  "plugins": [
    { "id": "capacity-report", "enabled": false },
    { "id": "discovery", "enabled": true }
  ]
}
```

- 同名 `id` 覆盖内置项字段；新 `id` 直接新增。
- 文件损坏 / 非法 JSON 时自动回落内置清单并打 warning，导航不会变空。
- `enabled: false` 的项不会出现在返回清单里，但**页面路由仍存在**——如需彻底下线请同时移除路由或在路由守卫里拦截。

## 后端插件端点（可选）

插件若需要自己的 API，按 `CONTRIBUTING.md` 第 3 节新增一个 `endpoints/<domain>.py` 并在 `api/v1/router.py` 注册；插件清单只负责导航注册。契约变更后运行：

```bash
python backend/scripts/export_openapi.py --static
python scripts/check_api_contract.py
```
