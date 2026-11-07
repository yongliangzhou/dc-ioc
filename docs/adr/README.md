# Architecture Decision Records (ADR)

本目录记录 **架构决策**（为什么这样设计、放弃了什么），不记录实现细节。实现细节见 `README.md`、`docs/database_design.md`、`docs/IMPLEMENTATION_PLAN.md`。

## 模板

```markdown
# ADR-00XX: <标题>
- 状态: 提议 | 已接受 | 已废弃 | 被 ADR-00YY 取代
- 日期: YYYY-MM-DD
- 决策者: <角色/团队>

## 背景
<问题、约束、可选方案的前提条件>

## 决策
<一句话结论 + 关键规则>

## 备选方案
| 方案 | 优点 | 否决原因 |
|---|---|---|

## 后果
### 正面
### 负面 / 需承担的成本
### 后续动作
```

## 索引

| 编号 | 标题 | 状态 | 关联版本 |
|---|---|---|---|
| [0001](./0001-timescaledb-over-influxdb.md) | 时序存储选择 TimescaleDB 而非 InfluxDB | 已接受 | v0.2 |
| [0002](./0002-aggregator-fallback.md) | 聚合层「真实链路优先 + 生成数据兜底」 | 已接受 | v0.2 |
| [0003](./0003-dual-auth.md) | JWT/RBAC 与 X-Collector-Token 双鉴权 | 已接受 | v0.2 |
| [0004](./0004-graphic-overlay.md) | 图形编辑采用 JSON 场景覆盖层 | 已接受 | v0.12 |
| [0005](./0005-cmdb-relation-and-phased-upgrade.md) | 引入 CMDB 关系层与四阶段升级路线 | 已接受 | v0.13–v0.16 |

新增 ADR 时：编号递增、不要修改已接受的 ADR 正文（用新 ADR 标记「取代」），并更新本索引。
