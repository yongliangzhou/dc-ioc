# DC-IOC 生产就绪检查清单 (Phase 3)

## CI/CD
- [x] GitHub Actions: backend lint + test + security scan
- [x] GitHub Actions: frontend typecheck + lint + build
- [x] Docker build + Trivy vulnerability scan (main branch)

## 环境隔离
- [x] .env.dev — 开发环境 (debug, mock, reload)
- [x] .env.staging — 预发环境 (接近生产, 保留 mock)
- [x] .env.prod — 生产环境模板 (所有凭据外部注入)
- [x] docker-compose.dev.yml — 热重载 + Prometheus 本地
- [x] docker-compose.staging.yml — 双副本 + 监控栈
- [x] docker-compose.prod.yml — 三副本 + Loki + Grafana

## 密钥管理
- [x] secret_check.py — 启动时 SECRET_KEY/admin 密码校验
- [x] 生产环境 SECRET_KEY 长度 ≥32 字符检查
- [x] 默认凭据阻止生产启动 (抛出 RuntimeError)

## 日志
- [x] loguru 结构化日志 (开发: 彩色, 生产: JSON)
- [x] 文件轮转: 按天 + 压缩 + 30 天保留
- [x] 错误日志独立文件 (90 天保留)
- [x] 敏感信息脱敏 (token/password)
- [x] Loki + Promtail 日志聚合

## 监控 (Prometheus)
- [x] prometheus-fastapi-instrumentator: HTTP 请求/延迟/体积
- [x] 自定义指标: WS 连接/告警数/设备状态/KPI
- [x] 告警规则: 后端宕机/高错误率/高延迟/PUE异常
- [x] Grafana 仪表盘自动加载
- [x] Node Exporter 主机指标

## 备份恢复
- [x] pg_dump 脚本: 全量 + 自定义格式 + S3 上传
- [x] pg_restore 脚本: 并行恢复 + 自动重建 + 连接管理
- [x] 定时清理: 本地保留 30 天
- [x] TimescaleDB 超表 schema 快照

## 压测
- [x] Locust: 只读用户 (viewer) + 写入用户 (operator)
- [x] 覆盖 9 个核心端点
- [x] 支持 headless 模式 (CI 集成)
