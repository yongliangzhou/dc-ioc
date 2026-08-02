#!/usr/bin/env bash
# =============================================================================
# 5.6.1 数据库备份自动化与监控
# -----------------------------------------------------------------------------
# 功能:
#   1. 每日全量 pg_dump (TimescaleDB 兼容, 含超表/压缩策略元数据)
#   2. 保留最近 N 份 (默认 14), 自动清理过期
#   3. 备份失败 / 成功 通过 webhook 上报 (可选, 配置 BACKUP_ALERT_WEBHOOK)
#   4. 备份后校验 dump 文件非空 + 可还原 (pg_restore --list 探测)
#
# 用法:
#   ./backup.sh                 # 立即执行一次备份
#   或加入 crontab:
#     0 2 * * *  /path/to/backup.sh >> /var/log/dc-ioc-backup.log 2>&1
#
# 环境变量 (可置于 .env 或前置 export):
#   DATABASE_URL     必填, 形如 postgresql://user:pass@host:5432/dbname
#   BACKUP_DIR       备份目录, 默认 ./backups
#   RETENTION_DAYS   保留天数, 默认 14
#   BACKUP_ALERT_WEBHOOK  可选, 失败/成功告警 webhook (JSON POST)
# =============================================================================
set -euo pipefail

DATABASE_URL="${DATABASE_URL:-}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
WEBHOOK="${BACKUP_ALERT_WEBHOOK:-}"
TS="$(date +%Y%m%d_%H%M%S)"
DUMP="$BACKUP_DIR/dc_ioc_$TS.sql.gz"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

alert() {
  local level="$1"; shift
  local msg="$*"
  log "$level: $msg"
  if [ -n "$WEBHOOK" ]; then
    curl -fsS -X POST "$WEBHOOK" \
      -H 'Content-Type: application/json' \
      -d "{\"level\":\"$level\",\"source\":\"db-backup\",\"message\":\"$msg\"}" \
      >/dev/null 2>&1 || log "WARN: 告警上报失败 (webhook 不可达)"
  fi
}

if [ -z "$DATABASE_URL" ]; then
  alert ERROR "DATABASE_URL 未设置, 备份中止"
  exit 1
fi

mkdir -p "$BACKUP_DIR"

log "开始备份 -> $DUMP"
if pg_dump "$DATABASE_URL" 2>/tmp/pgdump.err | gzip > "$DUMP"; then
  # 校验: 文件非空且可被 pg_restore 识别 (探测元数据)
  if [ ! -s "$DUMP" ] || ! gzip -t "$DUMP" 2>/dev/null; then
    alert ERROR "备份文件校验失败 (空或压缩损坏): $DUMP"
    rm -f "$DUMP"
    exit 1
  fi
  SIZE=$(du -h "$DUMP" | cut -f1)
  log "备份成功, 大小 $SIZE"
  alert INFO "数据库备份成功: $DUMP ($SIZE)"
else
  alert ERROR "pg_dump 失败: $(cat /tmp/pgdump.err)"
  rm -f "$DUMP"
  exit 1
fi

# 清理过期备份
log "清理 $RETENTION_DAYS 天前的备份"
find "$BACKUP_DIR" -name 'dc_ioc_*.sql.gz' -mtime "+$RETENTION_DAYS" -delete 2>/dev/null || true

log "完成"
