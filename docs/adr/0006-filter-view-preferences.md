# ADR-0006 筛选视图的个人隔离与持久化

- **状态**：已接受
- **日期**：2026-11-10
- **关联**：`04_VISUAL_SPEC.md` §6.2、ADR-0004（图形场景覆盖层）、`07_STAGE3_LEDGER.md`

## 背景

阶段 3-A 收敛了筛选栏、分页与遮罩的样式契约，但「保存视图 / 列配置」仍是缺口。
它们不是样式统一，而是新增功能，必须先确定三件事：视图归谁、存在哪里、无写权限时怎么办。

调研发现后端已有 `/api/ops/graphic-config/{kind}`（ADR-0004）：`kind` 是 `String(64)`
主键、无白名单，`payload.params` 为 `Dict[str, str]`，GET/PUT/DELETE 齐备，
`useDashboardLayout.ts` 已实现「server → localStorage → default」三级回退范式。

## 决策

1. **视图归属为「个人」**，不做团队共享。把用户维度编进 `kind`：
   `fv:{username}:{pageId}`，超 64 字符时改用 `fv:{user16}:{page24}:{fnv1a(raw)}`。
   这样在「按 kind 全局单例」的存储上实现按人 + 按页隔离，**不新增表、端点或迁移**。
2. **载荷**：`params.views = JSON.stringify(views)`、`params.defaultId = id | ''`。
   `GraphicScene.params` 只接受字符串，因此必须序列化；`nodes/edges/removed` 留空。
   一个视图 = `{ id, name, filters, columns, page?, size? }`。
3. **权限降级**：PUT 限 `admin/operator`。viewer 或后端不可达时回退 localStorage，
   返回 `source: 'local'`，由 `FilterBar` 挂 `DataBadge` 标注「仅本机保存」，
   **不静默伪装成已同步**。
4. **边界**：每人每页最多 10 个视图，第一个为默认；所有外部输入经防御式
   `normalize*`（未知字段丢弃、locked 列强制可见、order 重排为连续值）。
5. **列配置**：`ColumnSeed[]` 元数据 + `applyColumns()` 输出给现有
   `DeviceTable.vue` 的 `columns` prop，表格组件不改动。
6. **`HvacLiquid.vue` 的 `L/min` 保留**：后端 `mock_collector.py:298` 冷板支路流量
   就是 L/min，主管/冷冻水（:48/:65）是 m³/h，两者不同量纲，不做数值换算；
   只在列标签显式标注「冷板支路」并在 `metricsCatalog` 登记两种单位口径。

## 后果

- 零后端改动、零数据库迁移；复用既有权限模型与 ADR-0004 覆盖层机制。
- `GET /api/ops/graphic-config` 会列出全部 kind（含各用户的视图 title），
  仅登录用户可见，当前可接受。
- 若未来需要团队共享、跨设备同步或视图审计，须新增 `/api/ops/view-preferences`
  与按 `user_id` 索引的表；本决策不排除该演进。
- 列配置与 Esc/焦点陷阱目前只在 `Equipment.vue` 建立范式，其余页需逐页抽
  `<th>/<td>` 元数据并确认遮罩 close 回调，无法机械批量替换。
