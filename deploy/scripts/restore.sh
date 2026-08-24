#!/bin/bash
# =============================================================
# DC-IOC PostgreSQL 恢复脚本
#
# 用法:
#   ./restore.sh backups/dc_ioc_20240101_020000.sql          # 恢复到默认数据库
#   ./restore.sh backups/dc_ioc_20240101_020000.dump --db dc_ioc_staging
#   ./restore.sh backups/dc_ioc_20240101_020000.dump --parallel 4
#
# 建议: 恢复前先对当前数据库做快照!
# =============================================================
set -euo pipefail

# ---- 配置 ----
DB_HOST="${POSTGRES_HOST:-127.0.0.1}"
DB_PORT="${POSTGRES_PORT:-5432}"
DB_USER="${POSTGRES_USER:-dcuser}"
DB_NAME="${POSTGRES_DB:-dc_ioc}"
DB_PASS="${POSTGRES_PASSWORD:-dcpass}"

PARALLEL=2
DRY_RUN=false
CUSTOM_DB=""

# ---- 参数解析 ----
BACKUP_FILE=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --db) CUSTOM_DB="$2"; shift 2 ;;
        --parallel) PARALLEL="$2"; shift 2 ;;
        --dry-run) DRY_RUN=true; shift ;;
        --help|-h)
            echo "用法: $0 <backup_file> [--db DB_NAME] [--parallel N] [--dry-run]"
            exit 0
            ;;
        *) BACKUP_FILE="$1"; shift ;;
    esac
done

if [[ -z "$BACKUP_FILE" ]]; then
    echo "错误: 请指定备份文件路径"
    exit 1
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "错误: 备份文件不存在: $BACKUP_FILE"
    exit 1
fi

[[ -n "$CUSTOM_DB" ]] && DB_NAME="$CUSTOM_DB"

export PGPASSWORD="$DB_PASS"

# ---- 确认操作 ----
echo "============================================"
echo "  DC-IOC 数据库恢复"
echo "============================================"
echo "  目标数据库: $DB_HOST:$DB_PORT/$DB_NAME"
echo "  备份文件:   $BACKUP_FILE"
echo "  文件大小:   $(du -h "$BACKUP_FILE" | cut -f1)"
echo "  并行任务:   $PARALLEL"
echo "============================================"

if $DRY_RUN; then
    echo "[DRY RUN] 不执行实际恢复"
    exit 0
fi

# ---- 检查备份格式 ----
EXT="${BACKUP_FILE##*.}"

if [[ "$EXT" == "dump" ]]; then
    # 自定义格式: 使用 pg_restore
    RESTORE_CMD="pg_restore"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 自定义格式恢复 (pg_restore)..."

    # 恢复前断开所有连接 (避免 "database is being accessed" 错误)
    echo "断开 $DB_NAME 的所有连接..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d postgres -c "
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '$DB_NAME' AND pid <> pg_backend_pid();
    " 2>/dev/null || true

    # 删除并重建数据库
    echo "重建数据库 $DB_NAME..."
    dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" --if-exists "$DB_NAME" 2>/dev/null || true
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -O "$DB_USER" "$DB_NAME"

    # 启用 TimescaleDB 扩展
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
        CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
    "

    # 执行恢复
    $RESTORE_CMD \
        -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --no-owner --no-acl \
        --jobs="$PARALLEL" \
        --verbose \
        "$BACKUP_FILE"
else
    # 纯 SQL 格式: 使用 psql
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] SQL 格式恢复 (psql)..."
    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$BACKUP_FILE"
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 恢复完成!"

# 清理
unset PGPASSWORD
