"""CMDB 关系层数据访问 + 影响扩散纯逻辑 (阶段二)。

BFS 规则:
- 从 source_ci 出发沿「有向边」扩散 (source → target), 深度上限 6;
- visited 防环, 发现回边时置 has_cycle=True 但不重复入队;
- 无关系时返回 topology_source="fallback", 供前端标注「当前为内置拓扑推演」。
"""
from __future__ import annotations

import logging
from collections import deque

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.ci_relation import CiRelation
from app.schemas.ci_relation import RELATION_TYPES

logger = logging.getLogger(__name__)

MAX_DEPTH = 6


class CiConflictError(ValueError):
    """重复关系 / 非法关系。"""


def create_relation(db: Session, payload: dict) -> dict:
    """新建关系; 重复边抛 CiConflictError, 由端点转 409。"""
    src = str(payload["source_ci"]).strip()
    tgt = str(payload["target_ci"]).strip()
    rtype = str(payload.get("relation_type") or "connects_to")
    if src == tgt:
        raise CiConflictError("CI 不能与自身建立关系")
    if rtype not in RELATION_TYPES:
        raise CiConflictError(f"不支持的关系类型: {rtype}")
    exists = db.scalar(
        select(CiRelation).where(
            CiRelation.source_ci == src,
            CiRelation.target_ci == tgt,
            CiRelation.relation_type == rtype,
        )
    )
    if exists is not None:
        raise CiConflictError("该关系已存在")
    row = CiRelation(
        source_ci=src,
        target_ci=tgt,
        source_name=payload.get("source_name") or "",
        target_name=payload.get("target_name") or "",
        relation_type=rtype,
        description=payload.get("description") or "",
        created_by=payload.get("created_by") or "system",
        tenant_id=payload.get("tenant_id"),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row.to_dict()


def list_relations(
    db: Session,
    source_ci: str | None = None,
    relation_type: str | None = None,
    keyword: str | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    stmt = select(CiRelation)
    if source_ci:
        stmt = stmt.where(CiRelation.source_ci == source_ci)
    if relation_type:
        stmt = stmt.where(CiRelation.relation_type == relation_type)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(
            CiRelation.source_ci.like(like),
            CiRelation.target_ci.like(like),
            CiRelation.source_name.like(like),
            CiRelation.target_name.like(like),
        ))
    stmt = stmt.order_by(CiRelation.id.desc()).limit(min(limit, 500)).offset(offset)
    return [r.to_dict() for r in db.scalars(stmt).all()]


def delete_relation(db: Session, relation_id: int) -> bool:
    row = db.get(CiRelation, relation_id)
    if row is None:
        return False
    db.delete(row)
    db.commit()
    return True


def _all_edges(db: Session) -> list[dict]:
    return list_relations(db, limit=500)


def build_graph(db: Session) -> dict:
    """关系图: 节点去重 + 边列表。"""
    edges = _all_edges(db)
    names: dict[str, str] = {}
    for e in edges:
        names.setdefault(e["source_ci"], e["source_name"] or e["source_ci"])
        names.setdefault(e["target_ci"], e["target_name"] or e["target_ci"])
    nodes = [{"id": ci, "name": name} for ci, name in names.items()]
    return {
        "nodes": nodes,
        "edges": [
            {
                "source": e["source_ci"],
                "target": e["target_ci"],
                "type": e["relation_type"],
                "id": e["id"],
            }
            for e in edges
        ],
        "total": len(edges),
        "topology_source": "real" if edges else "fallback",
    }


def impact(db: Session, source_ci: str, depth: int = 3, relation_type: str | None = None) -> dict:
    """有向 BFS 影响扩散 (纯逻辑, 可单测)。"""
    depth = max(1, min(int(depth), MAX_DEPTH))
    edges = _all_edges(db)
    if not edges:
        return {
            "source_ci": source_ci,
            "depth": depth,
            "topology_source": "fallback",
            "impacted": [],
            "total": 0,
            "has_cycle": False,
        }

    adj: dict[str, list[tuple[str, str]]] = {}
    names: dict[str, str] = {}
    for e in edges:
        if relation_type and e["relation_type"] != relation_type:
            continue
        adj.setdefault(e["source_ci"], []).append((e["target_ci"], e["relation_type"]))
        names.setdefault(e["source_ci"], e["source_name"] or e["source_ci"])
        names.setdefault(e["target_ci"], e["target_name"] or e["target_ci"])

    queue: deque[tuple[str, int, str, list[str], set[str]]] = deque(
        [(source_ci, 0, "root", [source_ci], {source_ci})]
    )
    seen: dict[str, tuple[int, str, list[str]]] = {}
    has_cycle = False
    while queue:
        cur, hop, via, path, on_path = queue.popleft()
        if hop >= depth:
            continue
        for nxt, rtype in adj.get(cur, []):
            if nxt in on_path:
                has_cycle = True
                continue
            if nxt in seen:
                continue
            new_path = path + [nxt]
            seen[nxt] = (hop + 1, rtype, new_path)
            queue.append((nxt, hop + 1, rtype, new_path, on_path | {nxt}))

    impacted = [
        {
            "ci": ci,
            "name": names.get(ci, ci),
            "hop": hop,
            "via": via,
            "path": path,
        }
        for ci, (hop, via, path) in sorted(seen.items(), key=lambda kv: (kv[1][0], kv[0]))
    ]
    return {
        "source_ci": source_ci,
        "depth": depth,
        "topology_source": "real",
        "impacted": impacted,
        "total": len(impacted),
        "has_cycle": has_cycle,
    }


def relations_for_faults(fault_ids: list[int], depth: int = 3) -> list[dict]:
    """供故障影响分析复用: 把数字故障源映射为 `equipment:<id>` 并沿真实关系扩散。

    单独开一个 Session (而非复用调用方的 db), 保证 `analyze()` 在没有 DB 参数的
    既有调用方式下也能工作; 数据库不可达时只记日志并返回空列表, 输出与改造前一致。
    """
    from app.db.session import SessionLocal

    out: list[dict] = []
    db = None
    try:
        db = SessionLocal()  # 与后续查询一起纳入 try, 建会话失败也走降级
        for fid in fault_ids:
            source = f"equipment:{fid}"
            result = impact(db, source, depth)
            for item in result["impacted"]:
                out.append({
                    "faultId": fid,
                    "sourceCi": source,
                    "ci": item["ci"],
                    "name": item["name"],
                    "hop": item["hop"],
                    "via": item["via"],
                    "path": item["path"],
                })
    except Exception as exc:  # noqa: BLE001 - 关系库不可用时降级为 legacy 拓扑, 已记录日志
        logger.warning("真实 CI 关系扩散失败, 回退内置拓扑: %s", exc)
    finally:
        if db is not None:
            db.close()
    return out


def list_options(db: Session, limit: int = 100) -> list[dict]:
    """可选 CI 清单: 设备台账 / 机柜 / 外部设备并集。

    任一来源查询失败只记日志并跳过 (例如该表尚未建或数据源未就绪), 不影响其它来源。
    """
    from app.models.cabinet import Cabinet
    from app.models.equipment import Equipment
    from app.models.external import ExternalDevice

    options: list[dict] = []
    sources = (
        ("equipment", Equipment, "id", "code", "name", "设备"),
        ("cabinet", Cabinet, "id", "code", None, "机柜"),
        ("external", ExternalDevice, "id", "device_id", "name", "外部设备"),
    )
    for prefix, model, id_col, code_col, name_col, kind in sources:
        try:
            rows = db.query(model).limit(max(1, min(limit, 500))).all()
            for row in rows:
                rid = getattr(row, id_col, None)
                code = getattr(row, code_col, None) or str(rid)
                name = getattr(row, name_col, "") if name_col else ""
                options.append({
                    "ci": f"{prefix}:{rid}",
                    "name": str(name or code),
                    "kind": kind,
                })
        except Exception as exc:  # noqa: BLE001 - 单来源不可用时降级, 已记录日志
            logger.warning("CI 选项来源 %s 查询失败, 已跳过: %s", prefix, exc)
    return options
