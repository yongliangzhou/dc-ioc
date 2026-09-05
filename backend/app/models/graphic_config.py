"""图形页编辑配置 (统一图形编辑入口的持久化存储)。

冷源工艺流程 / 制冷链路 / 温度云图 / 10KV 与 0.4KV 一次系统图 / 配电链路 /
柴发并机 / 储油示意 / 电池组拓扑 / 门禁平面 / 周界示意 / 消防平面 等图形页面,
原来都是"页面内写死坐标 + 接口数据"的只读渲染, 没有任何编辑入口。

本表按 kind (图形标识) 存一份 JSON 场景覆盖层:
    { nodes: [{id,label,type,x,y,status,params}], edges: [...], params: {...}, removed: [id] }
页面渲染时把接口数据构成的节点清单与本覆盖层合并: 改名/改坐标/改参数 = 覆盖,
removed 中的 id = 删除, 覆盖层里新增的 id = 用户自建节点。
这样既有展示逻辑不需要重写, 又能真正支持"图形内容增删改"。
"""
from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.session import Base


class GraphicConfig(Base):
    """按 kind 唯一的一份图形场景配置 (JSONB 覆盖层)。"""

    __tablename__ = "graphic_config"

    kind = Column(String(64), primary_key=True)
    title = Column(String(128), nullable=True)
    payload = Column(JSONB, nullable=True)
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
            "kind": self.kind,
            "title": self.title or "",
            "payload": self.payload or {"nodes": [], "edges": [], "params": {}, "removed": []},
            "updatedBy": self.updated_by or "system",
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }
