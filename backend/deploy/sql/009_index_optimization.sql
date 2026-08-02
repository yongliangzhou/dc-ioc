-- =============================================================================
-- 5.1.3 索引优化脚本（索引规划复核）
-- -----------------------------------------------------------------------------
-- 用途: 根据高频查询模式(列表过滤/排序/时间范围)补充缺失索引, 加速查询并避免
--       全表扫描。_timescale 超表(hypertable)上建索引会自动成为"附加工件块索引"。
-- 执行: 在 PostgreSQL (TimescaleDB) 中运行; 生产建议在低峰期执行。
-- 注意: 重复执行幂等 (IF NOT EXISTS); 不会删除既有索引。
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. 工单 tickets: 列表页高频过滤 state/sys/lv + 排序 created
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_tickets_state        ON tickets (state);
CREATE INDEX IF NOT EXISTS ix_tickets_sys           ON tickets (sys);
CREATE INDEX IF NOT EXISTS ix_tickets_lv            ON tickets (lv);
CREATE INDEX IF NOT EXISTS ix_tickets_created       ON tickets (created DESC);
CREATE INDEX IF NOT EXISTS ix_tickets_owner         ON tickets (owner);
-- 组合索引: 覆盖 "按状态+系统筛选并倒序" 的典型列表查询
CREATE INDEX IF NOT EXISTS ix_tickets_state_sys_created
    ON tickets (state, sys, created DESC);

-- ---------------------------------------------------------------------------
-- 2. 告警 alarm_events: 按设备/级别/状态/触发时间过滤与排序
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_alarm_events_equipment ON alarm_events (equipment_id);
CREATE INDEX IF NOT EXISTS ix_alarm_events_level     ON alarm_events (level);
CREATE INDEX IF NOT EXISTS ix_alarm_events_state     ON alarm_events (state);
CREATE INDEX IF NOT EXISTS ix_alarm_events_triggered ON alarm_events (triggered_at DESC);
CREATE INDEX IF NOT EXISTS ix_alarm_events_rule      ON alarm_events (rule_id);

-- ---------------------------------------------------------------------------
-- 3. 遥测时序: point_data / realtime_metrics 时间范围查询
--    (TimescaleDB 超表: 时间索引由 create_hypertable 自动创建, 这里补设备+指标)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_point_data_equip_time
    ON point_data (equipment_id, time DESC);
CREATE INDEX IF NOT EXISTS ix_point_data_equip_metric
    ON point_data (equipment_id, metric);
CREATE INDEX IF NOT EXISTS ix_realtime_metrics_equip
    ON realtime_metrics (equipment_id, ts DESC);

-- 外部接入设备遥测
CREATE INDEX IF NOT EXISTS ix_external_metrics_device
    ON external_metrics (device_id, ts DESC);

-- ---------------------------------------------------------------------------
-- 4. 审计日志 audit_logs: 按用户/时间/动作检索
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_audit_logs_user       ON audit_logs (user_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_created    ON audit_logs (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action     ON audit_logs (action);

-- ---------------------------------------------------------------------------
-- 5. 拓扑层级过滤: idcs/rooms/cabinets/servers 状态与归属
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_rooms_idc              ON rooms (idc_id);
CREATE INDEX IF NOT EXISTS ix_cabinets_room          ON cabinets (room_id);
CREATE INDEX IF NOT EXISTS ix_cabinets_status        ON cabinets (status);
CREATE INDEX IF NOT EXISTS ix_servers_cabinet        ON servers (cabinet_id);
CREATE INDEX IF NOT EXISTS ix_servers_status         ON servers (status);

-- ---------------------------------------------------------------------------
-- 6. 知识库与运维: knowledge 按分类/领域检索
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_knowledge_category    ON knowledge (category);
CREATE INDEX IF NOT EXISTS ix_knowledge_domain      ON knowledge (domain);
CREATE INDEX IF NOT EXISTS ix_knowledge_code        ON knowledge (code);

-- ---------------------------------------------------------------------------
-- 7. 巡检/值班/演练: 计划与结果关联
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_inspection_items_plan ON inspection_items (plan_id);
CREATE INDEX IF NOT EXISTS ix_inspection_results_item ON inspection_results (item_id);
CREATE INDEX IF NOT EXISTS ix_shifts_group          ON shifts (group_id);
CREATE INDEX IF NOT EXISTS ix_shift_participants_shift ON shift_participants (shift_id);
CREATE INDEX IF NOT EXISTS ix_shift_participants_user  ON shift_participants (user_id);
CREATE INDEX IF NOT EXISTS ix_drill_records_plan    ON drill_records (plan_id);

-- ---------------------------------------------------------------------------
-- 8. 会话历史(登录审计)
-- ---------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS ix_session_history_user  ON session_history (user_id);
CREATE INDEX IF NOT EXISTS ix_session_history_login ON session_history (login_at DESC);

-- =============================================================================
-- 维护说明:
--   - 超表(point_data/realtime_metrics/external_metrics)的 time/ts 索引已由
--     create_hypertable 自动创建, 上表补充的是"设备+时间"复合索引。
--   - 若某索引长期零命中, 可在后续版本用 DROP INDEX 移除 (本脚本只增不减)。
--   - 可用以下语句验证索引是否被使用:
--       EXPLAIN (ANALYZE, BUFFERS)
--       SELECT * FROM tickets WHERE state='open' ORDER BY created DESC;
-- =============================================================================
