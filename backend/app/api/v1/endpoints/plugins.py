"""插件清单只读端点 (P4-1): GET /api/plugins/manifest。"""
from fastapi import APIRouter, Depends

from app.core.deps import get_current_user
from app.core.plugin_registry import manifest_payload

router = APIRouter(tags=["plugins"])


@router.get("", summary="前端导航插件清单")
def get_manifest(_user=Depends(get_current_user)):
    return manifest_payload()
