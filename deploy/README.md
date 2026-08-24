# DC-IOC 平台 部署运维手册

> 数据中心 IOC（智能运营中心）一体化平台：前端可视化驾驶舱 + 后端 API + PostgreSQL + Redis。
> 本文档覆盖容器化一键部署、本地开发、常用运维与故障排查。

---

## 1. 架构概览

```
┌──────────────┐      /api, /ws       ┌──────────────────┐
│   Browser    │ ───────────────────► │   Frontend       │
│ (驾驶舱 UI)  │                      │   Nginx :8080    │
└──────────────┘                      │  - 静态资源托管   │
                                      │  - 反向代理       │
                                      └────────┬─────────┘
                                               │ 代理转发
                              ┌────────────────┼────────────────┐
                              ▼                                 ▼
                      ┌───────────────┐                ┌───────────────┐
                      │   Backend     │                │    Redis      │
                      │  FastAPI      │ ◄── 缓存 ─────│  :6379        │
                      │  Uvicorn :8000│                │ (overview 30s)│
                      └──────┬────────┘                └───────────────┘
                             │ SQL
                      ┌──────▼────────┐
                      │  PostgreSQL   │
                      │  :5432        │
                      └───────────────┘
```

| 服务      | 镜像                | 容器内端口 | 宿主机映射 | 说明                         |
|-----------|---------------------|------------|------------|------------------------------|
| postgres  | postgres:16-alpine  | 5432       | 5432       | 关系型数据库，持久化卷 pgdata |
| redis     | redis:7-alpine      | 6379       | 6379       | 缓存 / Celery 消息代理        |
| backend   | 本地构建 (Python)   | 8000       | 8000       | FastAPI + Uvicorn             |
| frontend  | 本地构建 (Nginx)    | 80         | 8080       | 静态托管 + 反向代理           |

---

## 2. 环境要求

- **Docker** ≥ 24.0 且 **Docker Compose** ≥ v2（建议直接安装 Docker Desktop）。
- 磁盘空间 ≥ 2 GB（镜像 + 构建缓存）。
- 端口 `5432 / 6379 / 8000 / 8080` 未被占用。

---

## 3. 一键部署（推荐）

> 适用于 Linux / macOS / Windows（PowerShell 或 `start.bat`）。

```bash
# 进入平台根目录
cd dc-ioc-platform

# （可选）根据模板生成后端环境变量
cp backend/.env.example backend/.env

# 构建并后台启动四个服务
docker compose up -d --build

# 查看服务状态
docker compose ps

# 实时日志
docker compose logs -f
```

启动成功后访问：

- 前端驾驶舱：<http://localhost:8080>
- 后端接口文档（Swagger）：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

### Windows 用户

直接双击 `start.bat`：脚本会自动检查 Docker、按需生成 `backend/.env`，并执行 `docker compose up -d --build`，最后打开浏览器。

---

## 4. 性能优化说明

### 4.1 后端 Redis 响应缓存

高频只读接口 `/api/dashboard/overview` 已启用 `cache_json` 装饰器（`backend/app/core/cache.py`）：

- 缓存键 = `MD5(prefix + 请求路径 + 查询串)`，TTL **30 秒**。
- 命中缓存直接返回，**不访问数据库 / 不重复计算**，显著降低 DB 压力。
- **优雅降级**：Redis 不可用时自动跳过缓存，不影响主流程。
- 序列化使用 `orjson`（更快），并回退到标准 `json`。

验证缓存是否生效：

```bash
# 第一次（回源）
curl -i http://localhost:8000/api/dashboard/overview | grep -i x-cache
# 30 秒内再次访问应命中缓存（响应更快，且 Redis 中存在对应 key）
docker compose exec redis redis-cli keys 'cache:*'
```

### 4.2 前端构建优化

`frontend/vite.config.ts` 已配置：

- **代码分割（`manualChunks`）**：`echarts / vue / axios / dayjs` 拆分为独立 chunk，利于浏览器长缓存与并行加载，首屏不再加载超大单包。
- **Gzip / Brotli 预压缩（`vite-plugin-compression`）**：构建期生成 `.gz` / `.br`，Nginx 通过 `gzip_static` 直接发送，省去运行时压缩开销。
- 产物文件名带 hash，内容变更才失效，适合强缓存（CDN）。

Nginx 侧（`frontend/nginx.conf`）已开启 `gzip_static on` 与 `gzip on`。

---

## 5. 配置说明

### 5.1 后端环境变量

后端读取 `backend/.env`（不存在时使用代码默认值）。关键变量：

| 变量 | 说明 | 容器默认值 |
|------|------|-----------|
| `POSTGRES_HOST` / `POSTGRES_PORT` | 数据库地址 | `postgres` / `5432` |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | 库账号 | `dcuser` / `dcpass` / `dc_ioc` |
| `REDIS_HOST` / `REDIS_PORT` | 缓存地址 | `redis` / `6379` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | 任务队列 | `redis://redis:6379/2`、`/3` |
| `CORS_ORIGINS` | 允许跨域来源 | `http://localhost:8080,...` |

> 在 `docker-compose.yml` 中已通过 `environment:` 注入容器网络内的正确地址，
> 本地直接运行后端时则使用 `.env` 中的 `127.0.0.1`。

### 5.2 数据库初始化

`deploy/sql/init.sql` 会在 PostgreSQL 首次启动时自动执行（挂载到
`/docker-entrypoint-initdb.d/`）。如需重建库表结构，可参考 `deploy/sql/` 下
`002_core_tables.sql`、`003_point_data_hypertable.sql` 及 `004_schema_design.md`。

---

## 6. 本地开发（不使用容器）

```bash
# 后端
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env           # 修改 POSTGRES_HOST=127.0.0.1 等
uvicorn app.main:app --reload --port 8000

# 前端 (另开终端)
cd frontend
npm install
npm run dev                   # http://localhost:5173 (Vite 代理 /api -> :8000)
```

---

## 7. 常用运维命令

```bash
# 查看各服务状态
docker compose ps

# 查看 / 跟踪日志
docker compose logs -f backend
docker compose logs -f frontend

# 仅重新构建某个服务
docker compose up -d --build backend

# 停止但不删除数据
docker compose down

# 停止并清空数据库 / 缓存数据卷（慎用！）
docker compose down -v

# 进入后端容器调试
docker compose exec backend bash

# 查看 Redis 缓存键
docker compose exec redis redis-cli keys '*'
```

---

## 8. 故障排查

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| `backend` 一直重启 / 连不上 DB | PostgreSQL 尚未就绪或账号不符 | 确认 `depends_on` 健康检查通过；检查 `POSTGRES_*` 变量 |
| 前端白屏 / 接口 502 | `backend` 未启动或 Nginx 代理失败 | `docker compose ps`；查看 `frontend` 日志；确认 `proxy_pass http://backend:8000` |
| `/api/dashboard/overview` 仍慢 | Redis 未启动或缓存未命中 | `docker compose exec redis redis-cli ping`；首次访问本就会回源 |
| 前端 404 刷新后丢失路由 | SPA 回退未生效 | 确认 `nginx.conf` 含 `try_files $uri $uri/ /index.html` |
| 构建 `npm run build` 类型错误 | `vue-tsc` 校验失败 | 本地 `npm run type-check` 定位；`manualChunks` 名称需与依赖一致 |
| 端口已被占用 | 宿主机已有服务 | 修改 `docker-compose.yml` 中的宿主机端口映射 |

---

## 9. 目录结构（节选）

```
dc-ioc-platform/
├── docker-compose.yml        # 根编排（4 服务）
├── start.bat                 # Windows 一键启动
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── .env.example
│   └── app/
│       ├── core/cache.py     # Redis 缓存装饰器
│       ├── cache/redis_client.py
│       └── api/v1/endpoints/dashboard.py   # /overview 启用 30s 缓存
├── frontend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── nginx.conf            # SPA + 反向代理
│   └── vite.config.ts        # 代码分割 + Gzip/Brotli
└── deploy/
    ├── README.md             # 本手册
    ├── nginx/
    └── sql/                  # 建表 / 初始化脚本
```
