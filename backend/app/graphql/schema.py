"""阶段四 · GraphQL 只读出口 (P4-2)。

依赖 `strawberry-graphql[fastapi]` 为**可选**: 未安装时 `schema = None`,
main.py 会跳过挂载, 旧环境仍可正常启动 (ADR-0005 的可降级约束)。

暴露只读查询 (强制分页上限 200):
- cis(limit)                 : CI 节点 (来自 CMDB 关系图)
- relations(sourceCi)        : 关系边
- impact(ciId, depth)        : 沿真实关系的影响扩散
- ipSubnets(limit)           : IPAM 子网 + 利用率
- equipment(limit)           : 设备台账摘要

所有 resolver 复用 P2/P3 的 crud 纯函数, 不直接暴露 ORM 对象; 数据库异常
统一降级为空列表并记录日志, 不会把 500 抛给 GraphQL 调用方。
"""
from __future__ import annotations

import logging
from typing import Optional

from app.crud import ci_relation as ci_crud
from app.crud import p3 as p3_crud
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)
MAX_LIMIT = 200

try:
    import strawberry
except ImportError:  # pragma: no cover - 取决于部署是否安装可选依赖
    logger.info("strawberry 未安装, GraphQL 只读出口不启用 (可选依赖)")
    strawberry = None  # type: ignore[assignment]


def _limit(value: int) -> int:
    return max(1, min(int(value), MAX_LIMIT))


def _safe(fn, default):
    """Resolver 统一降级: 任一层数据不可用只影响该查询, 不破坏整个 schema。"""
    db = SessionLocal()
    try:
        return fn(db)
    except Exception as exc:  # noqa: BLE001 - 只读查询降级为空结果, 已记录日志
        logger.warning("GraphQL 查询降级: %s", exc)
        return default
    finally:
        db.close()


if strawberry is not None:

    @strawberry.type
    class CINode:
        id: str
        name: str

    @strawberry.type
    class Relation:
        id: int
        source: str
        target: str
        type: str

    @strawberry.type
    class ImpactItem:
        ci: str
        name: str
        hop: int
        via: str

    @strawberry.type
    class Subnet:
        id: int
        cidr: str
        total: int
        used: int
        utilization_pct: float

    @strawberry.type
    class EquipmentItem:
        id: int
        code: str
        name: str
        domain: str
        category: str

    @strawberry.type
    class Query:
        @strawberry.field(description="CI 节点列表 (关系图去重)")
        def cis(self, limit: int = 50) -> list[CINode]:
            def run(db):
                graph = ci_crud.build_graph(db)
                return [CINode(id=n["id"], name=n["name"]) for n in graph["nodes"][:_limit(limit)]]

            return _safe(run, [])

        @strawberry.field(description="CI 关系边 (可按源 CI 过滤)")
        def relations(self, source_ci: Optional[str] = None, limit: int = 50) -> list[Relation]:
            def run(db):
                edges = ci_crud.build_graph(db)["edges"]
                if source_ci:
                    edges = [e for e in edges if e["source"] == source_ci]
                return [
                    Relation(id=int(e["id"]), source=e["source"], target=e["target"], type=e["type"])
                    for e in edges[:_limit(limit)]
                ]

            return _safe(run, [])

        @strawberry.field(description="沿真实关系的有向影响扩散")
        def impact(self, ci_id: str, depth: int = 3) -> list[ImpactItem]:
            def run(db):
                out = ci_crud.impact(db, ci_id, min(depth, 6))
                return [
                    ImpactItem(ci=i["ci"], name=i["name"], hop=i["hop"], via=i["via"])
                    for i in out["impacted"][:MAX_LIMIT]
                ]

            return _safe(run, [])

        @strawberry.field(description="IPAM 子网与利用率")
        def ip_subnets(self, limit: int = 50) -> list[Subnet]:
            def run(db):
                return [
                    Subnet(
                        id=int(s["id"]), cidr=str(s["cidr"]),
                        total=int(s["total"]), used=int(s["used"]),
                        utilization_pct=float(s["utilization_pct"]),
                    )
                    for s in p3_crud.subnet_views(db)[:_limit(limit)]
                ]

            return _safe(run, [])

        @strawberry.field(description="设备台账摘要 (domain 可选过滤)")
        def equipment(self, domain: Optional[str] = None, limit: int = 50) -> list[EquipmentItem]:
            from app.models.equipment import Equipment

            def run(db):
                rows = p3_crud.list_rows(
                    db, Equipment, where={"domain": domain}, limit=_limit(limit)
                )
                return [
                    EquipmentItem(
                        id=int(r["id"]), code=str(r["code"]), name=str(r["name"]),
                        domain=str(r["domain"]), category=str(r["category"]),
                    )
                    for r in rows
                ]

            return _safe(run, [])

    schema = strawberry.Schema(query=Query)
else:
    schema = None
