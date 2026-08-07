"""知识库 CRUD (2.3)。"""
from __future__ import annotations

from typing import Optional

import re
from sqlalchemy.orm import Session

from app.models.knowledge import KnowledgeItem

_CODE_RE = re.compile(r"(\d+)\s*$")


def _next_code(db: Session) -> str:
    """基于现有最大编号生成下一个唯一 code (KB-xxxx)。

    不能用 count()+1: 删除条目会产生编号缺口, 导致与已存在的更高 code 冲突
    (如删掉 KB-0006 后 count 回退, 新条目算出 KB-0089 却已存在 -> 主键冲突)。
    """
    max_n = 0
    for (c,) in db.query(KnowledgeItem.code).all():
        if c:
            m = _CODE_RE.search(c)
            if m:
                max_n = max(max_n, int(m.group(1)))
    return f"KB-{max_n + 1:04d}"


def _to_snake(d: dict) -> dict:
    """将前端/契约的 camelCase 键转换为模型 snake_case 列名。"""
    out = {}
    for k, v in d.items():
        s = "".join("_" + c.lower() if c.isupper() else c for c in k)
        out[s] = v
    return out


def list_items(
    db: Session,
    *,
    category: Optional[str] = None,
    domain: Optional[str] = None,
    type: Optional[str] = None,
    kw: Optional[str] = None,
    review_status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    q = db.query(KnowledgeItem)
    if category:
        q = q.filter(KnowledgeItem.category == category)
    if domain:
        q = q.filter(KnowledgeItem.domain == domain)
    if type:
        q = q.filter(KnowledgeItem.type == type)
    if review_status:
        q = q.filter(KnowledgeItem.review_status == review_status)
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            (KnowledgeItem.title.ilike(like))
            | (KnowledgeItem.summary.ilike(like))
            | (KnowledgeItem.content.ilike(like))
        )
    q = q.order_by(KnowledgeItem.hot.desc(), KnowledgeItem.id.desc())
    rows = q.offset(offset).limit(limit).all()
    return [_to_dict(r) for r in rows]


def count(
    db: Session,
    *,
    category: Optional[str] = None,
    domain: Optional[str] = None,
    type: Optional[str] = None,
    kw: Optional[str] = None,
    review_status: Optional[str] = None,
) -> int:
    q = db.query(KnowledgeItem)
    if category:
        q = q.filter(KnowledgeItem.category == category)
    if domain:
        q = q.filter(KnowledgeItem.domain == domain)
    if type:
        q = q.filter(KnowledgeItem.type == type)
    if review_status:
        q = q.filter(KnowledgeItem.review_status == review_status)
    if kw:
        like = f"%{kw}%"
        q = q.filter(
            (KnowledgeItem.title.ilike(like))
            | (KnowledgeItem.summary.ilike(like))
            | (KnowledgeItem.content.ilike(like))
        )
    return q.count()


def related(db: Session, *, system: Optional[str] = None, domain: Optional[str] = None, metric: Optional[str] = None, limit: int = 10) -> list[dict]:
    """根据告警的 system/domain/metric 匹配处置预案。"""
    rows = db.query(KnowledgeItem).all()
    scored: list[tuple[int, dict]] = []
    for r in rows:
        score = 0
        if domain and domain in (r.related_domains or []):
            score += 3
        if system and system in (r.related_categories or []):
            score += 2
        if metric and metric in (r.related_metrics or []):
            score += 2
        # 兜底: domain 与 category 同义匹配
        if domain and r.category and domain.replace("_", "-") in r.category:
            score += 1
        if score > 0:
            scored.append((score, _to_dict(r)))
    scored.sort(key=lambda x: (-x[0], not x[1]["hot"], x[1]["id"]))
    return [d for _, d in scored[:limit]]


def get(db: Session, item_id: str) -> Optional[dict]:
    try:
        iid = int(item_id)
    except (TypeError, ValueError):
        row = db.query(KnowledgeItem).filter(KnowledgeItem.code == item_id).first()
    else:
        row = db.query(KnowledgeItem).filter(KnowledgeItem.id == iid).first()
    return _to_dict(row) if row else None


def create(db: Session, *, data: dict) -> dict:
    data = _to_snake(data)
    if not data.get("code"):
        data["code"] = _next_code(db)
    # 导入切分自动生成的内容默认待审核; 手动新建默认通过(由创建人即视为已确认)
    if data.get("review_status") is None:
        data["review_status"] = "approved"
    item = KnowledgeItem(**data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _to_dict(item)


def upsert(db: Session, *, data: dict) -> dict:
    """按 code 幂等写入: 存在则更新, 不存在则创建 (用于种子知识库同步)。"""
    data = _to_snake(data)
    code = data.get("code")
    if code:
        row = db.query(KnowledgeItem).filter(KnowledgeItem.code == code).first()
        if row:
            for k, v in data.items():
                if k in ("code", "id", "created_at"):
                    continue
                setattr(row, k, v)
            row.version = (row.version or 1) + 1
            db.commit()
            db.refresh(row)
            return _to_dict(row)
    return create(db, data=data)


def update(db: Session, item_id: str, *, data: dict) -> Optional[dict]:
    row = db.query(KnowledgeItem).filter(KnowledgeItem.id == int(item_id)).first()
    if not row:
        return None
    data = _to_snake(data)
    for k, v in data.items():
        if k in ("code", "id", "created_at"):
            continue
        setattr(row, k, v)
    row.version = (row.version or 1) + 1
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def delete(db: Session, item_id: str) -> bool:
    row = db.query(KnowledgeItem).filter(KnowledgeItem.id == int(item_id)).first()
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True


def stats(db: Session) -> dict:
    total = db.query(KnowledgeItem).count()
    by_type = {}
    for t, in db.query(KnowledgeItem.type).all():
        by_type[t] = by_type.get(t, 0) + 1
    hot = db.query(KnowledgeItem).filter(KnowledgeItem.hot.is_(True)).count()
    return {"total": total, "byType": by_type, "hot": hot}


def review(db: Session, item_id: str, *, status: str, note: str = "", reviewer: str = "") -> Optional[dict]:
    """人工审核：pending -> approved / rejected。"""
    row = db.query(KnowledgeItem).filter(KnowledgeItem.id == int(item_id)).first()
    if not row:
        return None
    row.review_status = status
    row.review_note = note
    row.reviewer = reviewer
    row.reviewed_at = _now()
    db.commit()
    db.refresh(row)
    return _to_dict(row)


def list_pending(db: Session, limit: int = 200) -> list[dict]:
    rows = (
        db.query(KnowledgeItem)
        .filter(KnowledgeItem.review_status == "pending")
        .order_by(KnowledgeItem.id.desc())
        .limit(limit)
        .all()
    )
    return [_to_dict(r) for r in rows]


def _to_dict(r: KnowledgeItem) -> dict:
    return {
        "id": r.id,
        "code": r.code,
        "title": r.title,
        "category": r.category,
        "domain": r.domain,
        "type": r.type,
        "tags": r.tags or [],
        "relatedCategories": r.related_categories or [],
        "relatedDomains": r.related_domains or [],
        "relatedMetrics": r.related_metrics or [],
        "summary": r.summary or "",
        "content": r.content or "",
        "steps": r.steps or [],
        "owner": r.owner or "",
        "hot": bool(r.hot),
        "version": r.version or 1,
        "reviewStatus": r.review_status or "approved",
        "reviewer": r.reviewer or "",
        "reviewedAt": r.reviewed_at or "",
        "reviewNote": r.review_note or "",
        "createdAt": r.created_at,
        "updatedAt": r.updated_at,
    }
