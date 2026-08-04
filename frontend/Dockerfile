# =========================================================
# 前端多阶段构建: dev (Vite HMR) / prod (Nginx 静态)
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
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund || npm ci --no-audit --no-fund

# 拷贝所有源文件 (config/ts/vite)；源码目录通过 volume 覆盖实现热更新
COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]


# ---- Build 阶段: 编译 ----
FROM node:20-alpine AS build
WORKDIR /app

ENV npm_config_registry=https://registry.npmmirror.com \
    npm_config_fetch_timeout=120000 \
    npm_config_fetch_retries=5 \
    npm_config_fetch_retry_mintimeout=10000 \
    npm_config_fetch_retry_maxtimeout=60000
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund || npm ci --no-audit --no-fund

COPY . .
RUN npm run build


# ---- Prod 阶段: Nginx 托管 ----
FROM nginx:1.27-alpine AS prod

RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=5 \
  CMD wget -qO- http://localhost/healthz >/dev/null 2>&1 || exit 1

CMD ["nginx", "-g", "daemon off;"]
