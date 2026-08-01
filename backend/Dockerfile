# =========================================================
# 后端多阶段构建: dev (热重载) / prod (精简)
# =========================================================

# pip 镜像源 (默认阿里云镜像, 构建环境可稳定高速访问;
#   可用 --build-arg PIP_INDEX_URL=... 覆盖, 例如官方源 https://pypi.org/simple)
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple

# ---- Dev 阶段: 含热重载, 挂载源码 ----
FROM python:3.12-slim AS dev
ARG PIP_INDEX_URL

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} --timeout 60 --retries 5 -r requirements.txt

EXPOSE 8000

# 默认 CMD (在 docker-compose.dev.yml 中被覆盖为 --reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# ---- Prod 阶段: 精简镜像, 等 PostgreSQL 就绪 ----
FROM python:3.12-slim AS prod
ARG PIP_INDEX_URL

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -i ${PIP_INDEX_URL} --timeout 60 --retries 5 -r requirements.txt

COPY . .

EXPOSE 8000

# 等待 PostgreSQL 就绪后再启动 Uvicorn
CMD ["sh", "-c", " \
until python -c \"import socket,sys; s=socket.socket(); s.settimeout(2); \
sys.exit(0 if s.connect_ex(('${POSTGRES_HOST:-postgres}', ${POSTGRES_PORT:-5432}))==0 else 1)\"; \
do echo 'waiting for postgres...'; sleep 2; done; \
echo 'postgres is up - starting uvicorn'; \
uvicorn app.main:app --host 0.0.0.0 --port 8000"]
