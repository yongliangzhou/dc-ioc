# 三大新功能分阶段实施计划

> 目标：物模型编辑、多数据中心、3D 数字孪生拓扑
> 制定日期：2026-08-08

## 阶段总览（6 个里程碑，按依赖顺序）

```
阶段0  基建与依赖        → three 依赖、i18n 框架、路由骨架（无业务，纯铺垫）
阶段1  物模型后端        → 表/CRUD/接口，接管 GET /thing-models
阶段2  物模型前端编辑器   → 三栏编辑器 + 实时预览 + 校验（依赖阶段1）
阶段3  多数据中心后端     → IDC 表/CRUD/切换/对比/统一告警接口（依赖 domain_overview）
阶段4  多数据中心前端     → 管理页 + 跨中心对比仪表盘 + 统一告警（依赖阶段3）
阶段5  3D 数字孪生拓扑    → three.js 场景 + 实时映射（依赖阶段3 的 current-idc）
阶段6  集成验证与容器重建  → 清缓存、重建容器、端到端验证
```

## 阶段 0：基建与依赖铺垫（约 0.5 天）

| 任务 | 文件 | 说明 |
|---|---|---|
| 安装 three.js | `frontend/package.json` + `npm i` | 加 `three@^0.16x`；Docker 前端容器重建后需重跑 `npm i` 并清 `.vite` 缓存、重建 `@dc-ioc/ui` 软链（历史坑） |
| i18n key 框架 | `zh-CN.json` / `en-US.json` | 预置 `thingModel` / `datacenter` / `twin` 三大命名空间 key 骨架 |
| 路由占位 | `frontend/src/router/index.ts` | 注册 `/ops/thing-model`、`/ops/datacenter`、`/ops/datacenter/compare`、`/twin/3d` 路由（先指向占位组件） |
| 数据中心 store 骨架 | `frontend/src/stores/datacenter.ts` | pinia store：`currentIdcId`、`idcList`、`setCurrentIdc()`，预留持久化到 `/api/idc/current` |

**验证**：`npm run dev` 四路由可访问（占位页），无 console 报错。

## 阶段 1：物模型后端（约 1.5 天）

- 数据模型 `models/thing_model.py`：`ThingModel`(key 唯一/name/category/domain/protocol/vendor/model + TimestampMixin)、`ThingModelItem`(thing_model_id FK/cascade / item_type / identifier / name / data_type / unit / desc / extra JSONB)
- Schema `schemas/thing_model.py`：`ThingModelItemBase/Create`、`ThingModelCreate/Update`、`ThingModelOut`(nested items)
- CRUD `crud/thing_model.py`：list(模糊) / get / create(事务批量 upsert) / update / delete
- 接口 `api/v1/endpoints/thing_model.py`：`GET/POST/PUT/DELETE /api/thing-models`（写接口 `require_role("admin")`）
- 注册：`models/__init__.py` import+__all__；`api/v1/router.py` include_router

**验证**：`up -d backend` 后 `curl /api/thing-models` 返回空数组；POST 后能 GET。

## 阶段 2：物模型前端编辑器（约 2 天）

- 文件 `views/ops/ThingModelEditor.vue` + `api/thingModel.ts`
- 三栏：左=模型列表(搜索+新建)；中=属性/服务/事件 Tab(增删行)；右=实时 JSON 预览(computed)
- `constants/thingModels.ts` 改为后端兜底；`CollectorDeviceForm` 读后端物模型 API

## 阶段 3：多数据中心后端（约 1.5 天）

- 扩充 `models/idc.py`：补 `status`/`capacity_kw`/`region`/`description`；当前中心 `is_current` 或 settings 表
- `crud/idc.py`：list/get/create/update/delete/set_current + compare(复用 domain_overview 按 center) + unified_alarms
- 接口 `api/v1/endpoints/idc.py`：`GET/POST/PUT/DELETE /api/idc`、`GET/PUT /api/idc/current`、`GET /api/idc/compare`、`GET /api/idc/alarms`

## 阶段 4：多数据中心前端（约 2 天）

- `views/ops/DataCenterManage.vue`：中心卡片网格 + 新建/编辑抽屉 + 设为当前 → store
- `views/ops/DataCenterCompare.vue`：并排 KPI + vue-echarts 对比 + 统一告警滚动列表
- `datacenter.ts` 的 `currentIdcId` 被拓扑/监控消费

## 阶段 5：3D 数字孪生拓扑（约 2.5 天）

- `views/twin/Twin3D.vue`：idc→room→cabinet→device 层级 Group；BoxGeometry + InstancedMesh；OrbitControls
- 实时映射：节流轮询改 material.color/emissive；分层下拉控制 group.visible
- 生命周期 onUnmounted dispose；受 currentIdcId 驱动

## 阶段 6：集成验证与容器重建（约 1 天）

- 后端 `docker compose -f docker-compose.yml -f deploy/docker-compose.dev.yml up -d backend`
- 前端 `docker exec dc-ioc-platform-frontend-1 rm -rf /app/node_modules/.vite` + restart
- 确认 @dc-ioc/ui 软链；浏览器硬刷新走查
- 分模块提交 `feat(thing-model)` / `feat(datacenter)` / `feat(twin3d)`

## 关键风险

1. 建表失败全站 500：新模型必须注册 `models/__init__.py`，后端必须 `up -d` 重建
2. 前端 HMR 不生效：改完 .vue/.ts 必须清 .vite + restart + 硬刷新
3. three 体积：Docker 前端镜像重跑 npm i
4. 数据来源复用 `dc_aggregator`，不自造数据层
5. 写接口加 `require_role`
