# Contributing Guide · DC-IOC Platform

感谢参与贡献。本文是**可执行的工程约定**，按此操作可避免最常出现的几类失败：孤儿页面、i18n 键缺失、Alembic 与 `create_all` 漂移、CI 里才暴露的模板语法错误。

## 1. 工作流

| 项 | 约定 |
|---|---|
| 分支 | `feature/<phase>-<topic>`（如 `feature/p2-cmdb-relation`）、`fix/<topic>`、`docs/<topic>` |
| Commit | `<type>(<scope>): <中文简述>`，type ∈ `feat / fix / docs / refactor / test / chore / ci` |
| PR | 必须附：改动说明、验收命令输出、数据库变更说明（有/无）、截图（UI 改动） |
| 合并前 | 第 6 节「提交前检查」全部通过 |

## 2. 新增一个页面：四件套（最重要）

项目菜单由 `frontend/src/layouts/DefaultLayout.vue` 的 `nav` 计算属性**手工维护**，不是由路由自动生成；图标来自 `NavIcon.vue` 的内联 SVG 映射（缺失时会**静默**回退成通用圆圈）。所以新增页面必须同时完成四件事：

1. **路由**：在 `frontend/src/router/index.ts` 的 `children` 中注册，带 `meta.title` 与 `requiredRoles`。
   ```ts
   {
     path: 'ops/my-page',
     component: () => import('@/views/ops/MyPage.vue'),
     meta: { title: '我的页面', requiredRoles: ['admin', 'operator'] },
   }
   ```
2. **菜单**：在 `DefaultLayout.vue` 对应分组 `items` 中加 `{ path, title: t('nav.myPage'), ico: 'Cable' }`。分组 `id` 必须保持稳定（折叠状态按 id 记忆）。
3. **图标**：优先复用 `NavIcon.vue` 的 `ICONS` 已有键；确需新增时补一段 lucide 风格 24×24 SVG（不要使用 emoji 作为图标）。
4. **i18n**：`frontend/src/i18n/locales/zh-CN.json` 与 `en-US.json` 同步新增 `nav.myPage` 及页面文案段（`myPage.*`），**两侧键集合必须完全一致**：
   ```bash
   python scripts/check_i18n_keys.py --json     # 期望 missing = 0
   ```

> 校验：路由数 ↔ 菜单项数一一对应（0 孤儿页 / 0 死链）。阶段四插件化落地后改由 `scripts/check_nav_routes.py` 自动校验，且新页应优先在后端插件清单注册。

## 3. 新增一个后端业务域

分层依赖方向固定：`endpoints → services → crud → models`，出参一律用 `schemas` 序列化，禁止反向依赖。

```
backend/app/models/<domain>.py        # SQLAlchemy ORM
backend/app/schemas/<domain>.py       # Pydantic DTO (Create / Update / Out)
backend/app/crud/<domain>.py          # 纯 DB 操作
backend/app/api/v1/endpoints/<domain>.py   # 路由, 写操作 require_role("admin","operator")
backend/app/services/<domain>_service.py   # 仅当含业务规则时
```

接入点（三处小改动）：

- `backend/app/models/__init__.py`：注册模型（供 `Base.metadata.create_all` 与 Alembic autogenerate 收集）。
- `backend/app/api/v1/router.py`：`include_router(... prefix="/...", dependencies=_auth)`。
- 需要WS/定时任务时在 `app/main.py` / `app/core/lifespan.py` 注册。

约定：

- 所有业务端点挂 `/api` 前缀；外部采集器走独立 `X-Collector-Token`，不要叠加登录依赖。
- 写操作统一 `dependencies=[Depends(require_role("admin", "operator"))]`。
- 异常必须带 `logger`（`logging.getLogger(__name__)`），不要写裸 `except:`；捕获 `Exception` 时记录日志或加 `# noqa: BLE001` 说明。
- 原生 SQL 只允许参数化绑定（`scripts/sql_guard.py` 会在 CI 拦截 f-string 拼接）。
- 不合格输入用 `HTTPException(422/400)` 或 Pydantic `Literal`/`Field` 校验，不要静默吞掉。

## 4. 数据库变更：Alembic 双轨

生产库由 Alembic 管理，dev/test 由 lifespan `create_all` 兜底建表。两者必须一致：

1. 在 `backend/alembic/versions/` 新建修订，`down_revision` 指向链尾（见 `docs/IMPLEMENTATION_PLAN.md` 5.3 修订链）。
2. DDL 全部 `IF NOT EXISTS`，`downgrade()` 对称可回滚；新增列用 `ADD COLUMN IF NOT EXISTS`。
3. 模型注册进 `models/__init__.py`，确保 `create_all` 能建出同结构表。
4. 存量环境升级：`cd backend && alembic upgrade head`；回滚：`alembic downgrade -1`。
5. 新增列必须可空或有默认值，避免破坏既有数据；出参用 `to_dict()` 白名单，不要直接 `SELECT *` 透出。

## 5. 测试

- 后端：`tests/` 使用 `conftest.py` 的 `make_client()`（轻量 FastAPI + `get_current_user` 依赖覆盖）+ `make_sqlite_sessionmaker()`（SQLite 内存库），**不依赖真实 Postgres/Docker**。
  ```bash
  pytest tests/ -q --timeout=30 --cov=app --cov-fail-under=45
  ```
  含 PG 方言类型（`JSONB` / `BIGSERIAL`）的模型不能直接建到 SQLite，使用 `pre_ddl` 或泛型 `JSON` 类型。
- 前端：`npm run test:run`（Vitest）、`npx vue-tsc --noEmit`、`npm run build`。
- E2E：`frontend/e2e/` 是独立 npm 包（不污染主 lockfile），详见其 README。
- 每个新后端模块至少一份 `tests/test_*.py`；覆盖率门禁随阶段递进（45 → 50 → 55 → 60）。

## 6. 提交前检查

```bash
# 后端
cd backend && ruff check app/ && python -m compileall -q app
cd .. && pytest tests/ -q --timeout=30

# 前端
cd frontend && npx vue-tsc --noEmit && npm run test:run && npm run build

# 全局门禁
python scripts/check_i18n_keys.py --json
python scripts/sql_guard.py backend/app
```

pre-commit 钩子位于 `frontend/.husky/pre-commit`，**git 从仓库根执行钩子**，因此钩子内部先 `cd frontend`；`prepare` 脚本为 `cd .. && husky frontend/.husky`。若 `core.hooksPath` 为空说明 husky 未激活，请检查该脚本。钩子会扫描 Vue SFC 模板语法（多行 `@click` / `@change` 等），避免问题只在 CI 暴露。

## 7. 常见坑

| 现象 | 原因 / 处理 |
|---|---|
| 前端改了源码但页面不变 | Docker 挂载下 HMR 不生效：`docker exec <frontend> rm -rf /app/node_modules/.vite` → `docker restart <frontend>` → Ctrl+Shift+R |
| 改 `.env` 不生效 | 环境变量在容器启动时注入，`docker compose restart` 不会重读；用 `up -d backend` 重建 |
| 菜单图标变成圆圈 | `NavIcon.vue` 的 `ICONS` 缺该键，且回退是静默的 |
| 中英切换后折叠状态错乱 | 分组 `id` 不要用 `t('...')` 结果，必须是稳定字符串 |
| `vue-tsc` 报 TS7016 | `@dc-ioc/ui/dist` 的 `.d.ts` 被 vite 清空，重新 `cd packages/dc-ioc-ui && npm run build` |
| 新增端点未进契约 | 运行 `python backend/scripts/export_openapi.py` 重新导出 `frontend/openapi.json` |

## 8. 文档

- 架构决策记录写在 `docs/adr/`，模板见 `docs/adr/README.md`；决策（不是实现细节）才写 ADR。
- 每个版本发布前更新 `CHANGELOG.md` 的 `[Unreleased]` 并同步 `README.md` 头部版本号与 `backend/app/main.py` 的 `version` / `/health`。
- 插件开发见 `docs/PLUGIN_GUIDE.md`（阶段四落地后）。
