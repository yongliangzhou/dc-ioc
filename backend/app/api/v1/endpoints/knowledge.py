"""知识库/处置预案接口 (2.3)。"""
from __future__ import annotations

import asyncio
import os
import tempfile
from fastapi import APIRouter, Depends, HTTPException, Query, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_role
from app.crud import knowledge as kb_crud
from app.models.user import User
from app.schemas.knowledge import KnowledgeCreate, KnowledgeOut, KnowledgeUpdate, KnowledgeImportOut
from app.services import manual_import as mi

router = APIRouter()


@router.get("", response_model=dict, summary="知识库列表")
def list_knowledge(
    category: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    type: str | None = Query(default=None),
    kw: str | None = Query(default=None),
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    items = kb_crud.list_items(db, category=category, domain=domain, type=type, kw=kw, limit=limit, offset=offset)
    total = kb_crud.count(db, category=category, domain=domain, type=type, kw=kw)
    return {"total": total, "items": items, "stats": kb_crud.stats(db)}


@router.get("/related", response_model=list[KnowledgeOut], summary="按告警匹配处置预案")
def related_knowledge(
    system: str | None = Query(default=None, description="告警 system, 如 暖通-冷源"),
    domain: str | None = Query(default=None, description="告警 domain, 如 hvac_source"),
    metric: str | None = Query(default=None, description="告警 metric_name"),
    limit: int = Query(default=10, le=50),
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    """告警详情页用于关联处置预案 (告警 -> 知识库)。"""
    return kb_crud.related(db, system=system, domain=domain, metric=metric, limit=limit)


@router.get("/{item_id}", response_model=KnowledgeOut, summary="知识库详情")
def get_knowledge(item_id: str, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    item = kb_crud.get(db, item_id)
    if not item:
        raise HTTPException(404, "知识条目不存在")
    return item


@router.post("", response_model=KnowledgeOut, status_code=201, summary="新建知识条目")
def create_knowledge(
    req: KnowledgeCreate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    data = req.model_dump()
    return kb_crud.create(db, data=data)


@router.post("/import", response_model=KnowledgeImportOut, status_code=201, summary="一键导入运维指导书(按章节切分为多条)")
async def import_manual(
    file: UploadFile = File(..., description="运维指导书，支持 .txt / .pdf / .docx"),
    title: str | None = Form(default=None, description="覆盖标题"),
    category: str | None = Form(default=None, description="覆盖主专业"),
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    """把一本指导书按章节 / 处置场景切分为多条 manual 入库，每条精准匹配业务域；
    标题重复时跳过以避免重复导入。"""
    raw = await file.read()
    suffix = os.path.splitext(file.filename or "")[1].lower() or ".txt"
    if suffix not in (".txt", ".pdf", ".docx", ".doc"):
        raise HTTPException(400, "不支持的文件类型，仅支持 .txt / .pdf / .docx")
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
        # PDF/Word 解析是 CPU 密集的同步操作, 放到线程里执行,
        # 避免阻塞 uvicorn 单 worker 的事件循环 (否则大文件导入期间
        # 登录等所有请求都会排队超时)
        payloads = await asyncio.to_thread(mi.build_payloads, tmp, title, category)

        existing_titles = {it["title"] for it in kb_crud.list_items(db, limit=100000)}
        created: list[dict] = []
        skipped = 0
        detected_domains: list[str] = []
        detected_categories: list[str] = []
        for p in payloads:
            detected_domains.extend(d for d in p["relatedDomains"] if d not in detected_domains)
            detected_categories.extend(c for c in p["relatedCategories"] if c not in detected_categories)
            if p["title"] in existing_titles:
                skipped += 1
                continue
            item = kb_crud.create(db, data=p)
            created.append(item)
            existing_titles.add(item["title"])
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
    return {
        "items": created,
        "created": len(created),
        "skipped": skipped,
        "total": len(payloads),
        "detectedDomains": detected_domains,
        "detectedCategories": detected_categories,
        "note": "已按章节切分为多条 manual 入库，每条精准匹配业务域/专业",
    }


@router.put("/{item_id}", response_model=KnowledgeOut, summary="更新知识条目")
def update_knowledge(
    item_id: str,
    req: KnowledgeUpdate,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    item = kb_crud.update(db, item_id, data=data)
    if not item:
        raise HTTPException(404, "知识条目不存在")
    return item


@router.delete("/{item_id}", status_code=204, summary="删除知识条目")
def delete_knowledge(
    item_id: str,
    db: Session = Depends(get_db),
    _u: User = Depends(require_role("admin", "operator")),
):
    if not kb_crud.delete(db, item_id):
        raise HTTPException(404, "知识条目不存在")
