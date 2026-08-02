"""5.2.3 通用文件上传接口。

提供与业务解耦的通用上传能力, 替代原先散落在各端点里的内联上传逻辑:
  - POST /api/uploads/avatar     -> 用户头像 (单文件, 图片)
  - POST /api/uploads/attachment -> 工单/知识库附件 (单文件, 任意允许类型)
  - POST /api/uploads/batch      -> 批量上传 (多文件, 返回 url 列表)

统一约定:
  - 文件保存在 $UPLOAD_DIR (默认 backend/uploads/), 按日期分子目录
  - 返回可访问的相对 URL (/uploads/<date>/<uuid>.<ext>)
  - 限制大小与扩展名, 防止任意文件上传
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.deps import get_current_user, require_role
from app.models.user import User

router = APIRouter(prefix="/uploads", tags=["uploads"])

_UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "uploads"))
_MAX_BYTES = int(os.environ.get("UPLOAD_MAX_BYTES", "10_485_760"))  # 10 MB
_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
_DOC_EXT = {".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".csv", ".zip", ".json"}


def _save(file: UploadFile, allowed: set[str]) -> str:
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext or '(无扩展名)'}")
    data = file.file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"文件超过大小限制 {_MAX_BYTES // 1024 // 1024}MB")
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    date_dir = datetime.now().strftime("%Y%m%d")
    dest_dir = os.path.join(_UPLOAD_DIR, date_dir)
    os.makedirs(dest_dir, exist_ok=True)
    name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(dest_dir, name), "wb") as f:
        f.write(data)
    return f"/uploads/{date_dir}/{name}"


@router.post("/avatar", summary="上传用户头像")
def upload_avatar(
    file: UploadFile = File(...),
    _u: User = Depends(get_current_user),
):
    url = _save(file, _IMAGE_EXT)
    return {"url": url, "filename": file.filename}


@router.post("/attachment", summary="上传业务附件(工单/知识库等)")
def upload_attachment(
    file: UploadFile = File(...),
    _u: User = Depends(require_role("admin", "operator")),
):
    url = _save(file, _IMAGE_EXT | _DOC_EXT)
    return {"url": url, "filename": file.filename}


@router.post("/batch", summary="批量上传")
def upload_batch(
    files: list[UploadFile] = File(...),
    _u: User = Depends(require_role("admin", "operator")),
):
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="单次最多上传 20 个文件")
    results = []
    for f in files:
        try:
            url = _save(f, _IMAGE_EXT | _DOC_EXT)
            results.append({"filename": f.filename, "url": url, "ok": True})
        except HTTPException as e:
            results.append({"filename": f.filename, "url": None, "ok": False, "error": e.detail})
    return {"count": len(results), "items": results}
