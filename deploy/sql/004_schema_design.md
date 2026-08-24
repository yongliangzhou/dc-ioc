# DC-IOC 核心表结构设计文档

## 一、ER 关系

```
idc (数据中心) 1 ──── N cabinet (机柜) 1 ──── N server (物理服务器)
                                        │
                                        └── N point_data (测点, 多态挂载)
```

- `cabinet.idc_id → idc.id` (ON DELETE CASCADE)
- `server.cabinet_id → cabinet.id` (ON DELETE CASCADE)
- `point_data` 采用 `(target_type, target_id)` **多态关联**，可挂载到 `idc / cabinet / server / env` 任意对象，不强加外键以换取写入性能与采集灵活性（应用层维护一致性）。

## 二、表字段摘要

### idc 数据中心
| 字段 | 类型 | 说明 |
|---|---|---|
| code | varchar(32) 唯一 | 站点编码 EC1-HZ |
| name / region / address | varchar | 名称/地域/地址 |
| power_capacity_mw / cooling_capacity_mw | numeric | 电力/制冷容量 |
| rack_capacity / rooms | int | 机柜容量/包间数 |

### cabinet 机柜
| 字段 | 类型 | 说明 |
|---|---|---|
| idc_id | int FK | 所属数据中心 |
| code / room / row | varchar | 编号/包间/机列 |
| u_total / u_used | int | U位总数/已用 |
| rated_power_kw / current_power_kw | numeric | 额定/当前功率 |

### server 物理服务器
| 字段 | 类型 | 说明 |
|---|---|---|
| cabinet_id | int FK | 所在机柜 |
| asset_no | varchar(64) 唯一 | 资产编号 |
| ip | varchar(45) | 管理 IP |
| u_start / u_end | int | U位起止（含约束 u_end≥u_start） |
| cpu_model/cpu_count/cpu_cores/memory_gb/disk_desc | — | 配置 |

### point_data 实时测点
| 字段 | 类型 | 说明 |
|---|---|---|
| id + ts | 复合主键 | ts 为分区键 |
| target_type / target_id | 多态对象 | idc/cabinet/server/env |
| metric | varchar(32) | temperature/humidity/cpu_usage/mem_usage/power_kw |
| value / unit / quality | — | 数值/单位/质量 |

## 三、索引优化建议

| 索引 | 类型 | 场景 | 理由 |
|---|---|---|---|
| `uq_cabinet_idc_code (idc_id, code)` | 唯一复合 | 同 IDC 内编号唯一 + FK 反查 | 覆盖"某 IDC 下所有机柜"，避免回表 |
| `ix_cabinet_idc_room (idc_id, room)` | 复合 | 包间容量热力统计 | 匹配前缀 idc_id，可复用 |
| `ix_server_cabinet_u (cabinet_id,u_start,u_end)` | 复合 | U位定位/空间冲突检测 | 范围查询最左前缀 cabinet_id |
| `ix_server_ip_status (ip, status)` | 复合 | 按 IP 查在线设备 | 高基数 IP 在前 |
| `ix_pd_target_metric_ts (type,id,metric,ts)` | 复合 | **单对象单指标时序拉取（最常用）** | 等值列在前、ts 排序列在后，索引内有序返回 |
| `ix_pd_metric_ts (metric, ts)` | 复合 | 同类指标全网对比 | 如全网温度排行 |
| `ix_pd_ts_brin (ts)` | **BRIN** | 大范围时间扫描/删除归档 | 时序顺序写，BRIN 体积仅为 B-tree 的 ~0.1% |

**不建议**对 `point_data` 建立过多单列 B-tree 索引——时序高频写入会显著放大写放大与维护成本。

## 四、point_data 大表优化（关键）

时序数据 10s 一笔、数万测点，日增千万级行，必须做以下优化：

1. **分区 / Hypertable**：用 TimescaleDB `create_hypertable('point_data','ts')`，7 天一 chunk（见 `003_point_data_hypertable.sql`）。分区后单 chunk 索引小、裁剪快、按时间整 chunk 删除归档零成本。
2. **原生压缩**：30 天前数据列式压缩（压缩率 ~90%），`segmentby=(target,metric)`。
3. **连续聚合**：预计算 `point_data_5min` 均值物化视图，看板/报表直接查聚合而非原始点，查询提速 1~2 个数量级。
4. **保留策略**：`add_retention_policy` 自动清理 1 年前原始数据。
5. **写入优化**：批量 `INSERT ... (COPY/executemany)`；采集层先写 Redis 最新值，再异步落 PG。
6. **Redis 缓存最新值**：`HSET latest:{target}:{metric}`，实时大屏读 Redis 不打 PG。

## 五、典型查询与命中索引

```sql
-- ① 某机柜近1小时温度曲线 → ix_pd_target_metric_ts
SELECT ts, value FROM point_data
WHERE target_type='cabinet' AND target_id=12 AND metric='temperature'
  AND ts > now() - interval '1 hour' ORDER BY ts;

-- ② 某 IDC 某包间所有机柜功率 → uq_cabinet_idc_code / ix_cabinet_idc_room
SELECT code, current_power_kw FROM cabinet WHERE idc_id=1 AND room='R01';

-- ③ 机柜内 U 位占用冲突检测 → ix_server_cabinet_u
SELECT 1 FROM server WHERE cabinet_id=5
  AND u_start <= 20 AND u_end >= 18;

-- ④ 全网温度 TOP (近5分钟) → ix_pd_metric_ts
SELECT target_id, value FROM point_data
WHERE metric='temperature' AND ts > now() - interval '5 minutes'
ORDER BY value DESC LIMIT 20;
```

## 六、执行方式

```bash
# 方式 A: 原生 SQL
psql -d dc_ioc -f deploy/sql/002_core_tables.sql
psql -d dc_ioc -f deploy/sql/003_point_data_hypertable.sql   # 需 TimescaleDB

# 方式 B: Alembic
cd backend && alembic upgrade head
```
