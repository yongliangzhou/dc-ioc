"""统一告警触达中心数据模型。

notification_channel —— 通知通道配置 (类型/地址/最低级别/静默窗口/启停)。
notification_record —— 每一次实际触达尝试的留痕 (sent/failed/muted/dedup),
供通知中心页查询与"同告警+同通道 N 分钟去重"判定。

级别路由语义: min_level 为该通道接收的最低告警级别 (crit > warn > info),
级别数值 ≥ min_level 才投递。channel_name 在 record 上做快照,
通道被删除后历史记录仍可读。
"""
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Index, Integer, String, Text, func

from app.db.session import Base


class NotificationChannel(Base):
    __tablename__ = "notification_channel"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    type = Column(String(32), nullable=False)            # dingtalk/email/wechat/sms/custom
    name = Column(String(64), nullable=False)            # 展示名
    url = Column(Text, nullable=True)                    # webhook 地址 / 网关端点
    min_level = Column(String(8), nullable=False, default="crit")  # crit/warn/info
    quiet_start = Column(String(5), nullable=True)       # "22:00" 静默开始
    quiet_end = Column(String(5), nullable=True)         # "07:00" 静默结束 (跨零点支持)
    enabled = Column(Boolean, nullable=False, default=True)
    updated_by = Column(String(64), nullable=True, default="system")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "url": self.url or "",
            "minLevel": self.min_level or "crit",
            "quietStart": self.quiet_start,
            "quietEnd": self.quiet_end,
            "enabled": bool(self.enabled),
            "updatedBy": self.updated_by or "system",
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class NotificationRecord(Base):
    __tablename__ = "notification_record"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    alarm_id = Column(String(64), nullable=True, index=True)
    channel_id = Column(BigInteger, nullable=False, index=True)
    channel_name = Column(String(64), nullable=True)     # 快照, 通道删除后历史可读
    level = Column(String(8), nullable=False)            # crit/warn/info
    title = Column(String(255), nullable=False)
    status = Column(String(16), nullable=False, default="sent")  # sent/failed/muted/dedup
    error = Column(Text, nullable=True)                  # 失败原因 (status=failed 时)
    retry_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        # 去重查询: 同告警 + 同通道 + 时间窗 (notification_service 去重判定走该索引)
        Index("ix_notification_record_dedup", "alarm_id", "channel_id", "created_at"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "alarmId": self.alarm_id,
            "channelId": self.channel_id,
            "channelName": self.channel_name or "",
            "level": self.level,
            "title": self.title,
            "status": self.status or "sent",
            "error": self.error or "",
            "retryCount": self.retry_count or 0,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }
