# Changelog

All notable changes to this project are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

_Nothing pending. Next: calibrate the CI coverage ratchet against the first full CI report._

## [0.16.0] - 2026-11-08

### Added

- **P4 Pluginization**: `app/core/plugin_registry.py` + `GET /api/plugins/manifest`, frontend `plugins/manifest.ts` with offline fallback and `mergePluginNav()`; `scripts/check_nav_routes.py` CI gate (0 dead links / 0 orphan routes); `docs/PLUGIN_GUIDE.md`.
- **P4 GraphQL**: optional `strawberry-graphql[fastapi]` read-only schema (`cis` / `relations` / `impact` / `ipSubnets` / `equipment`, limit ≤ 200), lazily mounted at `/graphql`; startup still works without the dependency.
- **P4 Tenant isolation**: `tenant_context.py` ContextVar + `do_orm_execute` ORM hook + `TenantMiddleware`; applies only to models with `tenant_id`, zero behavior change when no context; `without_tenant_filter()` exemption; migration 0018 composite indexes.
- **P4 Configurable dashboard**: `useDashboardLayout.ts` (visibility / reorder / server persistence via `graphic-config/dashboard` / localStorage fallback / restore default), 6-section wrappers in `views/overview/Index.vue`, `styles/print.css`, Vitest pure-function tests.
- **P3**: IPAM (VLAN/subnet/address, utilization, next-available), discovery staging area (zero-dependency asyncio TCP probe, private-only /24 cap, `DISCOVERY_ENABLED` off by default), procurement + stocktake (expiring list, variance report), custom device fields (`equipment.custom_attributes` + generic renderer); migrations 0014–0017; 4 frontend pages.
- **P2**: full OpenAPI contract export (`backend/scripts/export_openapi.py`, dynamic preferred / static AST fallback, 199 paths / 270 operations) + drift guard; CMDB `ci_relation` layer with graph/impact BFS; fault impact now merges real relations (`topologySource` / `realRelations`, backward compatible); migration 0013.
- **P1**: `README.en.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, ADR 0001–0005, independent Playwright E2E package (10 smoke paths), exception-hygiene AST gate, CI coverage/nav/contract gates.

### Changed

- `frontend/openapi.json` regenerated to cover all backend routes (was 29 endpoints).
- Sidebar dynamic plugin items moved out of `DefaultLayout.vue` hard-coded `nav` into the manifest; static nav remains as the base.
- `app/db/session.py` now installs an idempotent ORM tenant filter hook.
- CI coverage gate calibrated to `--cov-fail-under=15` as a conservative ratchet baseline (raise to 25/35/45 after measuring the first CI report).

### Fixed (pre-push local CI reproduction)

- `useDashboardLayout.spec.ts`: 去掉 `x.id === 'ghost'` 的 TS2367 比较错误，`vue-tsc --noEmit` 恢复 0 错误。
- `crud/ci_relation.py`: `relations_for_faults()` 把 `SessionLocal()` 也纳入 `try`，会话创建失败时正确降级为 legacy 拓扑（原先直接抛异常）。
- `services/p3_services.py`: IPAM 子网统计改为「按地址数计算总量 + 集合判定已用」，IPv6 不再错误扣除一个地址；同时避免超大 IPv6 前缀全量展开导致 OOM。
- `db/session.py`: 租户过滤 hook 在 `all_mappers` 为空时回退 `bind_mapper`，使 `Query.count()` 等聚合查询不再绕过行级隔离。

### Migration Notes

- Run `cd backend && alembic upgrade head` on existing databases (chain 0013 → 0018).
- New installs are covered by lifespan `create_all`.
- Set `DISCOVERY_ENABLED=true` to enable network discovery endpoints.
- `/graphql` is mounted only when `strawberry-graphql[fastapi]` is installed.

## [0.12.0] - 2026-09

### Added

- Unified graphic editor: JSON scene overlay for 12 diagram pages (`graphic_config`), with real CRUD for refuel records (`refuel_record`).
- Unified notification center: channel CRUD, level routing, quiet windows, 10-min dedup, retry ≤ 2, delivery records, test send; registered as the 4th alarm notify handler.
- Alarm → ticket automation bridge: idempotent auto-ticket creation for `crit`+ alarms (configurable `ALARM_AUTO_TICKET_MIN_LEVEL`), SLA per severity, bidirectional linkage, source badges.
- Capacity What-if simulator (`POST /api/ops/capacity/what-if`): four-dimension headroom + 85%/100% exhaustion months + bottleneck ranking.
- i18n parity audit script (`scripts/check_i18n_keys.py --json`, 2960 keys, zero gaps) and pytest baseline of 41 cases.

### Fixed

- `crud/tenant.py`: `_to_snake()` blindly converted camelCase fields, causing `TypeError` on tenant creation — replaced with model-column mapping.
- 16 backend modules: blind `except` blocks now log (single-shot warning / high-frequency debug) with no control-flow change.
- Frontend: empty `catch` and `console.log` removed; multi-source pages unified on `useAsyncPageAll` + `ErrorBanner`; write errors normalized via `toErrorMessage`.
- Alembic 0011/0012 aligned with lifespan `create_all` self-healing (drift columns backfilled).

## [0.11.0] - 2026-08

### Added

- Sidebar regrouped into 9 collapsible groups with stable ids (fold state survives i18n switching); current group auto-expands on route change.
- 13 previously missing `NavIcon` glyphs added (55/55 menu icons present); 4 new i18n group keys.

### Fixed

- `FaultImpact.vue` missing `useToast()` and `TenantManage.vue` missing `useConfirm` import — both were runtime `is not defined` errors.
- Husky pre-commit had never been active: `prepare` now runs `cd .. && husky frontend/.husky`, and the hook `cd frontend` first (git executes hooks from the repo root).

## [0.10.0] - 2026-08

### Added

- Multi-model AI registry with runtime hot switch (`/api/ops/assistant/models`, `/select`, `/status`), `LLM_MODELS` env override.
- iHealth monthly health report page (7 domains → total score / grade / donut chart / findings).
- Liquid-cooling and power-chain diagram layout improvements; dark-tech card restyle for 7 ops pages.

### Fixed

- `HealthReport.generate()` now wraps i18n lookups with `s()` to avoid `undefined.replace` crashes.

## [0.9.0] - 2026-08

### Added

- Thing model backend (`thing_models` + `thing_model_items`) with graphical editor; write ops restricted to admin.
- 3D digital twin (`three.js`): location layers, OrbitControls, 8s telemetry recoloring, dispose on unmount.
- Multi-datacenter: IDC CRUD, global current-site switch, cross-site comparison, unified alarms; `idc_id` soft association on external devices.

### Fixed

- CI `npm ci` lockfile sync (three.js), explicit `--file frontend/Dockerfile`, reuse committed `@dc-ioc-ui/dist`.

## [0.8.0] - 2026-08

### Added

- Unified alarm type system (`lv→level`, `sys→system`, `desc→message`, `state→status`, `ts→time`), eliminating 86+ `vue-tsc` errors.
- OpenAPI client generation via orval (`generated/index.ts`, 1604 lines) + `generatedWrapper.ts` axios bridge.
- Shared component package `@dc-ioc/ui` (StatusBadge / AlarmBadge / KpiCard), Vite library mode.
- Pre-commit Vue SFC template syntax check; Docker HMR polling fix for WSL2/inotify.

## [0.7.0] - 2026-08

### Added

- `GET /api/runbooks/related` (alarm-linked runbooks); generic uploads (`/api/uploads/avatar|attachment|batch`).
- Ticket state machine validation + SLA `due_at` / `is_overdue`.
- Log/audit → alarm bridge; self-registration behind `ALLOW_SELF_REGISTER`.
- Data dictionary (27 tables), Mermaid ER diagram, permission matrix, 100-endpoint list, index & TimescaleDB optimization SQL.
- Idempotent seed scripts (`seed_admin.py`, `seed_demo.py`), backup automation, Redis/cache strategy docs.

### Fixed

- `cache_json` signature-preservation bug (broke FastAPI `Request` injection); dashboard caching and `invalidate_prefix()` added.

## [0.6.0] - 2026-08

### Added

- Network monitoring suite (5 pages): switches, routers/BGP, firewalls, wireless.
- API type completion for monitor/hvac modules; `vue-tsc --noEmit` zero errors; ruff clean.

## [0.5.0] - 2026-07

### Added

- Full liquid cooling model: primary/secondary CDU, GPU cold plates, leak detection (128 sensors), heat recovery, 3-stage free cooling.
- Chiller plant scaled to 8 chillers (4+2+N), 28MW; all frontend counts computed dynamically.

## [0.4.0] - 2026-07

### Added

- Mock fallback for v2 demo views, inertial random-walk telemetry, over-limit linkage engine (`realtimeLinkage.ts`), alarm → ticket closure in the alarm center.

## [0.3.0] - 2026-07

### Added

- CI/CD (ruff, bandit, safety, pytest+coverage, vue-tsc, build, Trivy); dev/staging/prod env isolation.
- Startup secret checks, structured loguru logs, Prometheus metrics + 12 alert rules, Grafana + Loki/Promtail.
- Backup/restore scripts and Locust load tests.

## [0.2.0] - 2026-07

### Added

- Unified data flow: MockCollector/Kafka → `/api/external/*` → `metric_raws` → `dc_aggregator` (real preferred, generated fallback with `_source`).
- JWT + RBAC, TimescaleDB hypertable (7d compression / 90d retention / continuous aggregates), alarm engine (13 device classes, 5-min convergence, suppression), WebSocket KPI/alarm broadcast.

## [0.1.0] - 2026-07

### Added

- Initial skeleton: FastAPI + Vue3 + PostgreSQL + Redis, 11 business-domain endpoint placeholders, static cockpit mock.
