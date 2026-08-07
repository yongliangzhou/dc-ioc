# =========================================================
# 前端多阶段构建: dev (Vite HMR) / prod (Nginx 静态)
# 构建上下文 = 项目根目录 (以便 COPY packages/ 和 frontend/)
# =========================================================

# ---- Dev 阶段: Vite dev server (热更新) ----
FROM node:20-alpine AS dev
WORKDIR /app

# 使用国内镜像源 + 超时/重试，避免受限网络下 npm install 静默挂起
ENV npm_config_registry=https://registry.npmmirror.com \
    npm_config_fetch_timeout=120000 \
    npm_config_fetch_retries=5 \
    npm_config_fetch_retry_mintimeout=10000 \
    npm_config_fetch_retry_maxtimeout=60000

# 拷贝前端 package 文件 + 共享 UI 库
COPY frontend/package.json frontend/package-lock.json* ./
COPY packages/ /packages/

# 安装前端依赖 (file:../packages/dc-ioc-ui 在 /app 内解析为 /packages/dc-ioc-ui)
RUN npm install --no-audit --no-fund || npm ci --no-audit --no-fund

# 安装并构建 @dc-ioc/ui (确保 dist/ 存在)
RUN cd /packages/dc-ioc-ui && npm install --no-audit --no-fund && npx vite build

# 修正 npm 为 file: 依赖创建的 symlink (Windows Docker 卷挂载会把目标解析为宿主机绝对路径, 容器内无效)
RUN rm -f /app/node_modules/@dc-ioc/ui && ln -s /packages/dc-ioc-ui /app/node_modules/@dc-ioc/ui

# 拷贝前端其余源文件；源码目录通过 volume 覆盖实现热更新
COPY frontend/. .

# vite 缓存目录持久化，避免容器重启丢失
VOLUME ["/app/node_modules/.vite"]

EXPOSE 5173

# HMR 文件监听使用 polling 模式 (vite.config.ts server.watch.usePolling)
# 解决 WSL2/Docker 卷挂载下 inotify 不触发的问题
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


# ---- Build 阶段: 编译 ----
FROM node:20-alpine AS build
WORKDIR /app

ENV npm_config_registry=https://registry.npmmirror.com \
    npm_config_fetch_timeout=120000 \
    npm_config_fetch_retries=5 \
    npm_config_fetch_retry_mintimeout=10000 \
    npm_config_fetch_retry_maxtimeout=60000

COPY frontend/package.json frontend/package-lock.json* ./
COPY packages/ /packages/

RUN npm install --no-audit --no-fund || npm ci --no-audit --no-fund

# 构建 UI 库 (prod 构建需要完整的类型定义)
RUN cd /packages/dc-ioc-ui && npm install --no-audit --no-fund && npx vite build

COPY frontend/. .
RUN npm run build


# ---- Prod 阶段: Nginx 托管 ----
FROM nginx:1.27-alpine AS prod

RUN rm -f /etc/nginx/conf.d/default.conf
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=5 \
  CMD wget -qO- http://localhost/healthz >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
