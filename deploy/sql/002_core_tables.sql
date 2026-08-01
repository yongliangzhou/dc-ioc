-- ============================================================================
-- DC-IOC 核心表结构 DDL (PostgreSQL 14+)
-- 数据中心 / 包间(功能间) / 统一设备台账 / 机柜 / 物理服务器 / 实时测点 / 告警
-- 用法: psql -d dc_ioc -f 002_core_tables.sql
-- 设计参照: deploy/sql/004_schema_design.md + 阿里云数据中心弱电课程业务单元分类
-- ============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- 1. 数据中心 IDC
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS idc (
    id                    SERIAL PRIMARY KEY,
    code                  VARCHAR(32)  NOT NULL,
    name                  VARCHAR(128) NOT NULL,
    region                VARCHAR(64)  NOT NULL,
    address               VARCHAR(255) NOT NULL DEFAULT '',
    power_capacity_mw     NUMERIC(10,3) NOT NULL DEFAULT 0,   -- 电力容量 MW
    cooling_capacity_mw   NUMERIC(10,3) NOT NULL DEFAULT 0,   -- 制冷容量 MW
    rack_capacity         INTEGER      NOT NULL DEFAULT 0,    -- 机柜总容量
    rooms                 INTEGER      NOT NULL DEFAULT 0,    -- 包间数
    status                VARCHAR(16)  NOT NULL DEFAULT '运营',
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_idc_code UNIQUE (code)
);
COMMENT ON TABLE idc IS '数据中心';
CREATE UNIQUE INDEX IF NOT EXISTS ix_idc_code   ON idc (code);
CREATE INDEX        IF NOT EXISTS ix_idc_region ON idc (region);
CREATE INDEX        IF NOT EXISTS ix_idc_status ON idc (status);

-- ---------------------------------------------------------------------------
-- 2. 包间 / 功能间 Room
--    分类(kind): it_room/substation/battery_room/chiller_station/carrier_room/ups_room/noc
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS room (
    id             SERIAL PRIMARY KEY,
    idc_id         INTEGER      NOT NULL REFERENCES idc(id) ON DELETE CASCADE,
    code           VARCHAR(32)  NOT NULL,
    name           VARCHAR(64)  NOT NULL DEFAULT '',
    kind           VARCHAR(32)  NOT NULL DEFAULT 'it_room',
    floor          VARCHAR(16)  NOT NULL DEFAULT '',
    rack_capacity  INTEGER      NOT NULL DEFAULT 0,
    cold_aisle_t   DOUBLE PRECISION NOT NULL DEFAULT 0,   -- 冷通道均温
    hot_aisle_t    DOUBLE PRECISION NOT NULL DEFAULT 0,   -- 热通道均温
    rh             DOUBLE PRECISION NOT NULL DEFAULT 0,   -- 相对湿度
    pressure_pa    DOUBLE PRECISION NOT NULL DEFAULT 0,   -- 正压 Pa (5~10)
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_room_idc_code UNIQUE (idc_id, code)
);
COMMENT ON TABLE room IS '包间/功能间';
CREATE INDEX IF NOT EXISTS ix_room_idc_code ON room (idc_id, code);
CREATE INDEX IF NOT EXISTS ix_room_kind     ON room (kind);

-- ---------------------------------------------------------------------------
-- 3. 统一设备台账 Equipment (按阿里云课程 domain/category 业务单元分类)
--    domain : hvac_source/hvac_terminal/power_hv/power_lv/power_genset/
--             power_fuel/power_batt/sec_cctv/sec_acs/sec_ids/sec_fire
--    category: chiller/cooling_tower/chw_pump/ups/hvdc/genset/fuel_tank/
--             battery_group/camera/door_ctrl/fence/smoke_detector/...
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS equipment (
    id           SERIAL PRIMARY KEY,
    idc_id       INTEGER      NOT NULL REFERENCES idc(id) ON DELETE CASCADE,
    room_id      INTEGER      NULL REFERENCES room(id) ON DELETE SET NULL,
    code         VARCHAR(64)  NOT NULL,
    name         VARCHAR(128) NOT NULL DEFAULT '',
    domain       VARCHAR(32)  NOT NULL,
    category     VARCHAR(32)  NOT NULL,
    vendor       VARCHAR(64)  NOT NULL DEFAULT '',
    model        VARCHAR(128) NOT NULL DEFAULT '',
    status       VARCHAR(16)  NOT NULL DEFAULT '运行',
    load_pct     DOUBLE PRECISION NOT NULL DEFAULT 0,
    run_hours    INTEGER      NOT NULL DEFAULT 0,
    redundancy   VARCHAR(16)  NOT NULL DEFAULT '',
    attrs        JSONB        NOT NULL DEFAULT '{}'::jsonb,   -- 类别专属参数
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_equipment_idc_code UNIQUE (idc_id, code)
);
COMMENT ON TABLE equipment IS '统一设备台账(按课程业务单元)';
CREATE INDEX IF NOT EXISTS ix_equipment_idc_code  ON equipment (idc_id, code);
CREATE INDEX IF NOT EXISTS ix_equipment_domain    ON equipment (domain);
CREATE INDEX IF NOT EXISTS ix_equipment_category  ON equipment (category);
CREATE INDEX IF NOT EXISTS ix_equipment_dom_cat   ON equipment (domain, category);
CREATE INDEX IF NOT EXISTS ix_equipment_room      ON equipment (room_id);
CREATE INDEX IF NOT EXISTS ix_equipment_status    ON equipment (status);

-- ---------------------------------------------------------------------------
-- 4. 机柜 Cabinet  (FK -> idc)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cabinet (
    id                SERIAL PRIMARY KEY,
    idc_id            INTEGER      NOT NULL REFERENCES idc(id) ON DELETE CASCADE,
    code              VARCHAR(32)  NOT NULL,
    room              VARCHAR(32)  NOT NULL,
    "row"             VARCHAR(16)  NOT NULL DEFAULT '',
    u_total           INTEGER      NOT NULL DEFAULT 42,        -- U位总数
    u_used            INTEGER      NOT NULL DEFAULT 0,
    rated_power_kw    NUMERIC(8,2) NOT NULL DEFAULT 10.0,
    current_power_kw  NUMERIC(8,2) NOT NULL DEFAULT 0,         -- 当前功率
    status            VARCHAR(16)  NOT NULL DEFAULT '在用',
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);
COMMENT ON TABLE cabinet IS '机柜';
-- 同一 IDC 内机柜编号唯一 (复合唯一索引, 兼顾 FK 反查)
CREATE UNIQUE INDEX IF NOT EXISTS uq_cabinet_idc_code ON cabinet (idc_id, code);
-- 按 包间 检索机柜
CREATE INDEX        IF NOT EXISTS ix_cabinet_idc_room ON cabinet (idc_id, room);
CREATE INDEX        IF NOT EXISTS ix_cabinet_status   ON cabinet (status);

-- ---------------------------------------------------------------------------
-- 5. 物理服务器 Server  (FK -> cabinet)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS server (
    id           SERIAL PRIMARY KEY,
    cabinet_id   INTEGER      NOT NULL REFERENCES cabinet(id) ON DELETE CASCADE,
    asset_no     VARCHAR(64)  NOT NULL,
    hostname     VARCHAR(128) NOT NULL DEFAULT '',
    ip           VARCHAR(45)  NOT NULL,
    brand        VARCHAR(64)  NOT NULL DEFAULT '',
    model        VARCHAR(128) NOT NULL DEFAULT '',
    u_start      INTEGER      NOT NULL,                        -- 起始U位
    u_end        INTEGER      NOT NULL,                        -- 结束U位
    cpu_model    VARCHAR(128) NOT NULL DEFAULT '',
    cpu_count    INTEGER      NOT NULL DEFAULT 2,
    cpu_cores    INTEGER      NOT NULL DEFAULT 0,
    memory_gb    INTEGER      NOT NULL DEFAULT 0,
    disk_desc    VARCHAR(255) NOT NULL DEFAULT '',
    business     VARCHAR(128) NOT NULL DEFAULT '',
    status       VARCHAR(16)  NOT NULL DEFAULT '在线',
    created_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT uq_server_asset_no UNIQUE (asset_no),
    CONSTRAINT ck_server_u_range     CHECK (u_end >= u_start),
    CONSTRAINT ck_server_u_start_pos CHECK (u_start >= 1)
);
COMMENT ON TABLE server IS '物理服务器';
CREATE UNIQUE INDEX IF NOT EXISTS ix_server_asset_no  ON server (asset_no);
-- 机柜内 U 位定位 / 空间冲突检测 (cabinet_id + u_start + u_end)
CREATE INDEX        IF NOT EXISTS ix_server_cabinet_u ON server (cabinet_id, u_start, u_end);
CREATE INDEX        IF NOT EXISTS ix_server_ip_status ON server (ip, status);
CREATE INDEX        IF NOT EXISTS ix_server_business  ON server (business);
CREATE INDEX        IF NOT EXISTS ix_server_status    ON server (status);

-- ---------------------------------------------------------------------------
-- 6. 实时测点时序 Point_Data
--    多态对象 (target_type/target_id) + 指标, 按 ts 时序
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS point_data (
    id           BIGSERIAL,
    ts           TIMESTAMPTZ NOT NULL,                          -- 采集时间(分区键)
    target_type  VARCHAR(16) NOT NULL,                          -- idc/cabinet/server/env
    target_id    BIGINT      NOT NULL,
    metric       VARCHAR(32) NOT NULL,                          -- temperature/humidity/cpu_usage...
    value        DOUBLE PRECISION NOT NULL,
    unit         VARCHAR(16) NOT NULL DEFAULT '',
    quality      SMALLINT    NOT NULL DEFAULT 100,
    CONSTRAINT pk_point_data PRIMARY KEY (id, ts)
);
COMMENT ON TABLE point_data IS '实时测点时序数据';

-- 单对象单指标时序拉取 (最常用)
CREATE INDEX IF NOT EXISTS ix_pd_target_metric_ts
    ON point_data (target_type, target_id, metric, ts);
-- 同类指标全局对比 (如全网温度)
CREATE INDEX IF NOT EXISTS ix_pd_metric_ts
    ON point_data (metric, ts);
-- 时间 BRIN 索引: 顺序写时序表, 大范围时间扫描, 体积极小
CREATE INDEX IF NOT EXISTS ix_pd_ts_brin
    ON point_data USING brin (ts);

-- ---------------------------------------------------------------------------
-- 7. 告警 Alarm (point_data 之上的业务层告警)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS alarm (
    id         SERIAL PRIMARY KEY,
    ts         TIMESTAMPTZ NOT NULL,
    level      VARCHAR(8)  NOT NULL,          -- crit/warn/info
    system     VARCHAR(32) NOT NULL,          -- 业务系统 暖通-冷源/...
    domain     VARCHAR(32) NOT NULL DEFAULT '',
    category   VARCHAR(32) NOT NULL DEFAULT '',
    code       VARCHAR(64) NOT NULL DEFAULT '',
    desc       VARCHAR(255) NOT NULL DEFAULT '',
    state      VARCHAR(16) NOT NULL DEFAULT '处理中',  -- 处理中/已派单/观察中/已闭环/自动消警
    owner      VARCHAR(32) NOT NULL DEFAULT '',
    value      DOUBLE PRECISION NOT NULL DEFAULT 0,
    unit       VARCHAR(16) NOT NULL DEFAULT '',
    ack        BOOLEAN     NOT NULL DEFAULT false,
    rule       VARCHAR(64) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
COMMENT ON TABLE alarm IS '告警';
CREATE INDEX IF NOT EXISTS ix_alarm_level_ts      ON alarm (level, ts);
CREATE INDEX IF NOT EXISTS ix_alarm_system_state  ON alarm (system, state);
CREATE INDEX IF NOT EXISTS ix_alarm_domain       ON alarm (domain);

COMMIT;
