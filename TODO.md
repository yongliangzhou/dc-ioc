# 深化设计 TODO

> 生成日期：2026-07-28。来源：技术层深化评审（P0~P2）+ 业务层深化评审（B1~B7）。
> 状态标记：`[ ]` 待办 / `[~]` 进行中 / `[x]` 完成 / `[-]` 搁置

---

## 一、技术层（数据链路 / 告警引擎 / 可靠性）

### P0 — 正确性与数据风险

- [x] **P0-1 测点保留策略按存储引擎分层**
  - 位置：`backend/app/crud/external.py` `delete_old_metrics`、`backend/app/services/metric_agg.py`
  - 问题：DELETE 未区分 TimescaleDB / 普通物化视图；分批只 `flush()` 不 `commit()`，长事务风险；retention 与聚合刷新时间窗不一致
  - 方案：按 `metric_agg._detect(db)["mode"]` 分派 — timescale → `drop_chunks`；plain → 分批 DELETE 每批 commit 后 `refresh_views`；加 `EXTERNAL_METRIC_RETENTION_BATCH_SIZE` 配置

- [x] **P0-2 Kafka 摄取协程阻塞事件循环**
  - 位置：`backend/app/collectors/kafka_consumer.py` `_consume_loop`、`backend/app/services/external_ingest.py`
  - 问题：async 协程内直接调同步 `ingest_metrics`（含 `list_devices(limit=10000)` 同步查询），设备量上来消费吞吐塌方
  - 方案：`run_in_executor` 包裹同步摄取；`_category_map` 改为 JOIN 单设备 category（参考 `sweep_recent_metrics`），删掉热路径缓存

- [x] **P0-3 告警引擎状态持久化**
  - 位置：`backend/app/services/alarm_engine.py`
  - 问题：`_active_alarm_cache` / `_convergence_index` / `_disabled_rules` 全内存态 — 多 worker 不一致、重启丢状态、规则启停不持久
  - 方案：落 DB 表（`alarm_states` / `alarm_rules`）或 Redis；与 B7（规则配置化）同源设计

### P1 — 可靠性与契约一致性

- [x] **P1-4 测点幂等去重**
  - 问题：`MetricRaw` 无 `(device_id, metric_name, ts)` 唯一键，Kafka at-least-once 重投会重复落库
  - 方案：加唯一约束 + `ON CONFLICT DO NOTHING`
  - 落地：`MetricRaw` 模型加 `uq_metric_raw_device_name_ts` 唯一约束；`bulk_insert_metrics` 改用 `pg_insert(...).on_conflict_do_nothing(...)`（非 postgres 退化为普通插入）；迁移 `0003_metric_raw_unique` 清理历史重复行并建立唯一索引，`deploy/sql/007_metric_raw_unique.sql` 提供 `CONCURRENTLY` 零锁在线建索引版本供大表使用。

- [x] **P1-5 Kafka offset 手动提交 + DLQ 优化**
  - 问题：`enable_auto_commit=True` 导致失败消息不重投；`_send_to_dlq` 每条新建 producer；DLQ 无人消费
  - 方案：关自动提交、处理成功后手动 commit；常驻 DLQ producer；补 DLQ 重投消费者
  - 落地：`kafka_consumer` 主消费循环 `enable_auto_commit=False`，仅处理成功后 `consumer.commit({tp: OffsetAndMetadata(offset+1)})` 手动提交（崩溃未提交 → 重启重投，at-least-once）；DLQ producer 改为模块级单例（`_ensure_dlq_producer`/`_stop_dlq_producer`），不再每条新建；新增 `_dlq_redeliver_loop` 消费 DLQ topic 并重新注入 `_handle_message`，带 `DLQ_MAX_REDELIVER=3` 上限防毒消息死循环；`maybe_start_consumer` 改为 `_run_consumers` 同时驱动主消费与 DLQ 重投，共享常驻 producer，关闭时统一释放。

- [x] **P1-6 前端 stale 阈值与后端上报周期联动**
  - 位置：前端遥测页 `STALE_REPORT_MS = 15000`（硬编码）
  - 方案：后端在 realtime WS 消息 / 设备注册响应下发 `report_interval` / `stale_threshold`，前端动态采用
  - 落地：`config` 新增 `DEVICE_REPORT_INTERVAL_S=5`、`REALTIME_STALE_MULTIPLIER=3` 及派生属性 `stale_threshold_ms`（= 周期×倍数）；`ws.py` 的 `connected` 消息增下发 `report_interval_s` / `stale_threshold_ms`；`DeviceRegisterResponse` 增加同名字段并在 `device_register` 端点填充（采集器侧联动）；前端 `useTelemetry` 新增响应式 `reportIntervalS` / `metricStaleMs`（兜底 5s / 15000ms），处理 WS `connected` 消息动态覆盖，并返回给调用方；`DeviceMonitor.vue` 移除硬编码 `STALE_REPORT_MS`，改用 `metricStaleMs.value` 做单测点 stale 判定。改后端节奏配置即全局联动，前端无需改码。

### P2 — 可观测与运维

- [x] **P2-7 通知渠道接通**
  - 问题：`alarm_engine._notify` 有注册机制但全仓无注册方，告警只打日志
  - 方案：注册 WS 广播 handler（告警面板实时刷新），预留 webhook（钉钉/邮件/微信）
  - 落地：WS 广播 handler `ws_broadcaster.setup_alarm_notify()` 由原来仅在 KPI 循环内注册，改为 `lifespan` **启动即注册**（`_notify_registered` 幂等），告警面板经 `wsBus` 收到 `alarm` 消息实时 `ingestRealtime` 刷新；新增 `services/alarm_notify_webhook.py` 预留钉钉/邮件/微信通道，`config` 增加 `ALARM_WEBHOOK_DINGTALK_URL/EMAIL_URL/WECHAT_URL`（默认空=关闭），配置后由 `register_webhook_notifier()` 经 `alarm_engine.register_notify_handler("webhook", …)` 接通（标准库 urllib 异步线程 POST，无新依赖）。告警落库(db)/WS/Webhook 三者并行分发。

- [x] **P2-8 Prometheus 指标暴露**
  - 方案：`/metrics` 暴露删除条数/耗时、摄取 QPS、告警触发率、活跃告警数、WS 在线连接数
  - 落地：`monitoring` 原有 `/metrics`（prometheus_fastapi_instrumentator）已挂载；补齐指标落点：① 摄取 QPS — `bulk_insert_metrics` 自增 `external_points_ingested`（按接收条数，rate() 得 QPS）+ 新增 `external_ingest_latency_seconds` 直方图（批量写入延迟）；② 删除条数/耗时 — `delete_old_metrics` 自增 `metric_retention_deleted_total`（plain 用真实删除行数，timescale 用 drop 前预估值）+ 新增 `metric_retention_duration_seconds` 直方图；③ 告警触发率 — `alarm_engine.evaluate` 在新建/升级告警时自增 `alarms_triggered`（label severity/system，rate() 得触发率）；④ 活跃告警数 — `lifespan` KPI 循环按 severity 分维度 `alarms_active` Gauge 实时 set；⑤ WS 在线连接数 — 原 `ws_connections_active` Gauge 已在 KPI 循环 set。无新增依赖，`/metrics` 直接可见。

---

## 二、业务层（消除"双源割裂"，打通真实闭环）

- [x] **B2 统一设备主数据：external_devices 即台账**（最核心，B1/B3/B5 的前置）
  - 问题：`/api/equipment` 来自 `generated.list_equipment`，与采集器接入的 `external_devices` 两套
  - 方案：台账以 `external_devices` 为单一事实源，generated 仅零设备兜底；改 `dc_aggregator.list_equipment` + 前端台账页

- [x] **B1 告警中心消费真实告警引擎**
  - 问题：告警中心看 `/api/ops/alarms`（generated 假告警），真实告警在 `/api/alarms/active` 被架空；"转工单"要的却是真实告警
  - 方案：前端改用 `getActiveAlarms`；确认/关单回写 `ack_alarm` / `resolve_alarm`；转工单后告警标记关联，工单关单联动 resolve
  - 落地：`/api/alarms/active` 改为返回 `alarm_engine` 真实活跃告警（含 `ack`/`resolve` 端点）；`realtimeLinkage` 改消费 `getActiveAlarms`；`/api/ops/tickets/from-alarm` 兼容真实引擎告警并标记关联；工单关单联动 `resolve_alarm`。告警中心活动列表不再混入 generated 假告警。

- [x] **B5 专业域"生成器骨架"收敛**
  - 问题：暖通/电力页结构来自 `generated.*` 骨架，新接入设备类别不在骨架内则页面看不到
  - 方案：真实设备列表为骨架 + 物模型定义指标，生成器仅零设备兜底
  - 落地：新增 `GET /api/domain/{category}`（`dc_aggregator.domain_overview`），以 external_devices 为骨架、物模型定义指标（含阈值状态着色）；零真实设备回退合成骨架。暖通/电力 8 个页面统一改用 `DomainDevices` 通用组件，新增类别设备自动可见。

- [x] **B3 运维作业域与真实资产/告警联动**
  - 问题：巡检/维保/演练/排班全是 generated 孤立数据，无 `device_id` 关联
  - 方案：任务关联真实设备；基于告警/设备类别自动生成巡检维保计划；排班班次作为工单 `owner` 来源
  - 落地：`/api/ops/inspection` 以 external_devices 为巡检对象（告警设备置顶"告警触发"）、合并自建路线；`/api/ops/maintain` 按真实设备类别生成 PM 计划并关联代表设备；`/api/ops/drill` 依真实专业域类别生成建议演练；排班 `ShiftSchedule` 已为 DB 真实数据，可作为工单 `owner` 来源（`/api/ops/shift`）。前端巡检/维保/演练页展示"真实资产"来源标记与设备关联。

- [x] **B4 容量/能耗真实数据底座**（与 P0-1 协同设计）
  - 问题：`capacity / energy` 为 generated；容量历史靠快照逆推；retention 循环会删原始表
  - 方案：建独立"分析型长期时序"（retention 不清它），容量/能耗基于真实聚合计算
  - 落地：新增 `capacity_energy_history` 独立表（模型 `CapacityEnergyHistory` + 迁移 `0004` + 手动 SQL `deploy/sql/008`），与 `metric_raws` 解耦，retention 循环不清理它；`app/services/capacity_energy.py` 基于真实设备功率测点聚合（设施总功率=进线 `active_power`/功率测点和，制冷=暖通类功率和，损耗=设施×4%，IT=设施−制冷−损耗，PUE=设施/IT，当日能耗≈设施平均功率×已过去小时数）；`rollup_day` 每日 upsert 真实聚合入长期时序，`lifespan.metric_retention_loop` 在保留清理后调用 `rollup_recent` 维持趋势；`agg.capacity()`/`agg.energy()` 改为读真实聚合，无真实设备时回退生成器（`_source` 标记来源）。

- [x] **B6 AI 运维助手注入实时态势上下文**（可选增强）
  - 方案：知识库 RAG + 活跃告警 + 设备实时测点作为问答上下文
  - 落地：`assistant_service.answer()` 新增 `_build_situation`/`_situation_to_text`，实时聚合① 活跃告警（`alarm_engine.get_active_alarms()`，内存热路径，取近 20 条）② 若上下文携带 `device_id` 则取其实时测点（`crud.external.latest_metrics`，内存最新值）；态势文本并入检索上下文（参与弱匹配打分，提升与当前告警/测点相关预案命中率）并注入 LLM 用户提示（无 LLM 时仅增强检索）；响应新增 `situation` 字段（活跃告警 + 设备实时测点）供前端展示/复用。`AssistantContext` 增加 `device_id`，`AssistantAskResp` 增加嵌套 `situation`。全部走内存、无额外 DB 开销。前端可在上述设备页把当前 `device_id` 传入 context 以获得设备级实时态势。

- [x] **B7 告警规则配置化 + 物模型驱动**（衔接 P0-3）
  - 方案：`DEFAULT_RULES` 硬编码改 DB/配置存储；从 `thing_models` 推导默认阈值带
  - 落地：① 配置化——新增 `hydrate_rules()` 在 `hydrate_alarm_engine()` 启动时从 `alarm_rule` 表加载阈值到内存索引 `_MATCHED_RULES`/`RULE_ORDER`，DB 成为运行时单一事实源（DB 不可用/空时回退 import 期 `_build_index()`，行为不变）；`rule_id` 本就是 `采集器类别:测点`、与 DB 主键对齐，DB 启停（toggle_rule/set_rule_status）本就实时生效。② 物模型驱动——新增 `services/alarm_rule_derive.py`，由 `mock_collector._CATEGORY_METRICS` 的物理量程 `(min,max)` 推导默认阈值带（量程外→crit，靠近边缘 10%→warn）；`seed_alarm_rules()` 种子由 `DEFAULT_RULES`（手调基线）+ 推导规则合并，`ON CONFLICT DO NOTHING` 保留用户编辑；新增设备类别自动获得合理默认规则。阈值单位优先取测点级。

---

## 三、推荐推进顺序

1. **P0-2** Kafka 摄取阻塞（最容易悄悄拖垮吞吐）
2. **P0-3** 告警持久化（可信度基础，与 B7 同源）
3. **P0-1** 保留策略分层（与 B4 协同）
4. **B2** 台账单一事实源（业务闭环前置）
5. **B1** 告警中心闭环 → **B5** 专业域收敛 → **B3** 作业联动
6. **P1-4/5** 幂等与 offset → **B4** 容量能耗底座
7. **P1-6 / P2-7 / P2-8 / B6 / B7** 收尾增强
