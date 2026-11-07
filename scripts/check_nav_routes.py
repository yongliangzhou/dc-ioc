"""导航 ↔ 路由一致性门禁 (P4-1.3)。

静态解析三个来源:
- frontend/src/router/index.ts        : 全部 `path: '...'`
- frontend/src/layouts/DefaultLayout.vue : 静态 nav 项 (含 children)
- frontend/src/plugins/manifest.ts   : 插件清单 (含离线回退清单)

默认只在「死链」(菜单指向不存在的路由) 时失败; `--strict` 同时把
「孤儿路由」(有路由无菜单入口) 视为失败, 用于发版前人工核对。

用法: python scripts/check_nav_routes.py [--strict] [--json]
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "frontend" / "src" / "router" / "index.ts"
LAYOUT = ROOT / "frontend" / "src" / "layouts" / "DefaultLayout.vue"
MANIFEST = ROOT / "frontend" / "src" / "plugins" / "manifest.ts"

IGNORED_ROUTES = {"/", "/login", ":path"}


def _paths(path: Path, pattern: str, prefix_slash: bool) -> set[str]:
    src = path.read_text(encoding="utf-8")
    out = set()
    for raw in re.findall(pattern, src):
        p = raw.strip()
        if not p or p.startswith(":") or "{" in p:
            continue
        if prefix_slash and not p.startswith("/"):
            p = "/" + p
        if p in IGNORED_ROUTES:
            continue
        out.add(p)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="导航/路由一致性门禁")
    parser.add_argument("--strict", action="store_true", help="孤儿路由也视为失败")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    routes = _paths(ROUTER, r"path:\s*'([^']+)'", prefix_slash=True)
    nav = _paths(LAYOUT, r"path:\s*'(/[^']+)'", prefix_slash=False)
    plugins = _paths(MANIFEST, r"path:\s*'(/[^']+)'", prefix_slash=False)
    entries = nav | plugins

    dead = sorted(entries - routes)
    orphan = sorted(routes - entries)
    result = {
        "routes": len(routes),
        "nav_static": len(nav),
        "nav_plugins": len(plugins),
        "dead_links": dead,
        "orphan_routes": orphan,
        "ok": not dead and (not args.strict or not orphan),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"[nav-routes] 路由 {len(routes)} / 静态菜单 {len(nav)} / 插件菜单 {len(plugins)}")
        print(f"[nav-routes] 死链 {len(dead)}: {dead}")
        print(f"[nav-routes] 孤儿路由 {len(orphan)}: {orphan}")
        print("[nav-routes] 结果:", "OK" if result["ok"] else "FAIL")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
