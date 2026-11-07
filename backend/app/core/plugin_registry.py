"""阶段四 · 插件清单注册中心 (P4-1)。

目标: 消除「新增页面要同时改 router.py / DefaultLayout.vue 两处硬编码」中的菜单硬编码。
后端一处注册 → `GET /api/plugins/manifest` → 前端按 group 合并进导航。

清单项字段:
  id / group / path / icon / i18nKey / requiredRoles / enabled

覆盖文件: `backend/plugins.json` (可选), 结构为 `{"plugins": [...]}`,
与内置清单按 id 合并 (同名覆盖), 便于部署方不改代码启用/禁用页面。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BUILTIN_PLUGINS: list[dict] = [
    {
        "id": "cmdb-ci-relations", "group": "asset", "path": "/ops/ci-relations",
        "icon": "Cable", "i18nKey": "nav.ciRelations",
        "requiredRoles": ["admin", "operator"], "enabled": True,
    },
    {
        "id": "ipam", "group": "asset", "path": "/ops/ipam",
        "icon": "Globe", "i18nKey": "nav.ipam",
        "requiredRoles": ["admin", "operator"], "enabled": True,
    },
    {
        "id": "asset-business", "group": "asset", "path": "/ops/asset-business",
        "icon": "ClipboardList", "i18nKey": "nav.assetBusiness",
        "requiredRoles": ["admin", "operator"], "enabled": True,
    },
    {
        "id": "discovery", "group": "platform", "path": "/ops/discovery",
        "icon": "Radio", "i18nKey": "nav.discovery",
        "requiredRoles": ["admin", "operator"], "enabled": True,
    },
    {
        "id": "custom-fields", "group": "platform", "path": "/ops/custom-fields",
        "icon": "Settings2", "i18nKey": "nav.customFields",
        "requiredRoles": ["admin", "operator"], "enabled": True,
    },
]

_OVERRIDE_FILE = Path(__file__).resolve().parents[2] / "plugins.json"


def load_manifest() -> list[dict]:
    """内置清单 + 可选覆盖文件合并 (覆盖文件异常时回落内置清单, 导航永不变空)。"""
    merged = {p["id"]: dict(p) for p in BUILTIN_PLUGINS}
    if _OVERRIDE_FILE.is_file():
        try:
            raw = json.loads(_OVERRIDE_FILE.read_text(encoding="utf-8"))
            for item in raw.get("plugins", []):
                if isinstance(item, dict) and item.get("id"):
                    merged[item["id"]] = {**merged.get(item["id"], {}), **item}
        except Exception as exc:  # noqa: BLE001 - 覆盖文件损坏时不阻断启动, 已记录日志
            logger.warning("插件覆盖文件解析失败, 使用内置清单: %s", exc)
    return [p for p in merged.values() if p.get("enabled", True)]


def manifest_payload() -> dict:
    plugins = load_manifest()
    return {"version": 1, "total": len(plugins), "plugins": plugins}
