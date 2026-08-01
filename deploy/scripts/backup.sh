#!/bin/bash
# =============================================================
# DC-IOC PostgreSQL 备份脚本 (含 TimescaleDB 时序数据)
#
# 用法:
#   ./backup.sh                          # 全量备份
#   ./backup.sh --db dc_ioc_staging      # 指定数据库
#   ./backup.sh --compressed             # 压缩备份
#   ./backup.sh --s3 s3://my-bucket/dc-ioc/  # 上传到 S3
#
# 定时任务 (crontab):
#   0 2 * * * /path/to/backup.sh --compressed --s3 s3://bucket/
# =============================================================
set -euo pipefail

# ---- 配置 (可通过环境变量覆盖) ----
DB_HOST="${POSTGRES_HOST:-127.0.0.1}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-dcuser}"
DB_NAME="${POSTGRES_DB:-dc_ioc}"
DB_PASS="${POSTGRES_PASSWORD:-dcpass}"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"  # 本地保留天数
S3_PATH="${S3_PATH:-}"                  # S3 路径 (可选)

COMPRESSED=false
CUSTOM_DB=""

# ---- 参数解析 ----
while [[ $# -gt 0 ]]; do
    case "$1" in
        --db) CUSTOM_DB="$2"; shift 2 ;;
        --compressed) COMPRESSED=true; shift ;;
        --s3) S3_PATH="$2"; shift 2 ;;
        --retention) RETENTION_DAYS="$2"; shift 2 ;;
        *) echo "未知参数: $1"; exit 1 ;;
    esac
done

[[ -n "$CUSTOM_DB" ]] && DB_NAME="$CUSTOM_DB"

# ---- 准备 ----
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql"
mkdir -p "$BACKUP_DIR"

export PGPASSWORD="$DB_PASS"

# ---- 执行备份 (pg_dump 自定义格式支持并行恢复) ----
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始备份: $DB_NAME -> $BACKUP_FILE"

if $COMPRESSED; then
    # 自定义格式 (二进制, 体积更小, 支持并行恢复)
    pg_dump \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --format=custom \
        --compress=6 \
        --no-owner \
        --no-acl \
        --verbose \
        -f "${BACKUP_FILE}.dump" 2>&1
    BACKUP_FILE="${BACKUP_FILE}.dump"
else
    # 纯 SQL 格式 (可读, 兼容性好)
    pg_dump \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --format=plain \
        --no-owner \
        --no-acl \
        --verbose \
        -f "$BACKUP_FILE" 2>&1
fi

BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份完成: $BACKUP_FILE (大小: $BACKUP_SIZE)"

# ---- 可选: TimescaleDB 超表单独快照 (仅 schema) ----
SCHEMA_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}_schema.sql"
pg_dump \
    -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --schema-only --no-owner --no-acl \
    -f "$SCHEMA_FILE" 2>/dev/null
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Schema 快照: $SCHEMA_FILE"

# ---- 上传到 S3 (可选) ----
if [[ -n "$S3_PATH" ]]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 上传到 S3: $S3_PATH"
    if command -v aws &>/dev/null; then
        aws s3 cp "$BACKUP_FILE" "${S3_PATH}/$(basename "$BACKUP_FILE")" --storage-class STANDARD_IA
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] S3 上传完成"
    else
        echo "⚠ AWS CLI 未安装, 跳过 S3 上传"
    fi
fi

# ---- 清理过期备份 ----
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 清理 ${RETENTION_DAYS} 天前的本地备份..."
find "$BACKUP_DIR" -name "${DB_NAME}_*.sql*" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true
find "$BACKUP_DIR" -name "${DB_NAME}_*_schema.sql" -mtime "+${RETENTION_DAYS}" -delete 2>/dev/null || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 备份任务结束"

# 清理环境变量
unset PGPASSWORD
