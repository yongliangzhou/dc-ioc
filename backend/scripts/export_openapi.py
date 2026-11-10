"""导出全量 OpenAPI 契约 (阶段二 P2-1)。

两种模式:
1. dynamic (默认, 首选): 导入 `app.main:app` 调用 `app.openapi()`, 得到含完整
   request/response Schema 的契约 —— CI 里 `pip install -r requirements.txt` 后走这条。
2. static (回退): 纯 stdlib AST 扫描 `app/api/v1/router.py` + `endpoints/*.py`,
   组合出覆盖全部 (method, path) 的合法 OpenAPI 3.1 文档 —— 本地/CI 未装齐依赖时
   也能生成与校验契约, 不会静默产出 29 端点的旧文件。

产物: backend/openapi.json + frontend/openapi.json (orval 的输入)。

用法:
    python scripts/export_openapi.py                 # 生成 (dynamic 优先)
    python scripts/export_openapi.py --static       # 强制静态提取
    python scripts/export_openapi.py --check        # 只比对, 不写文件 (契约漂移门禁)
    python scripts/export_openapi.py --check --static
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
ENDPOINT_DIR = BACKEND / "app" / "api" / "v1" / "endpoints"
ROUTER_FILE = BACKEND / "app" / "api" / "v1" / "router.py"
FRONTEND_CONTRACT = REPO / "frontend" / "openapi.json"
BACKEND_CONTRACT = BACKEND / "openapi.json"
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}


def _const(node: ast.AST, default=None):
    return node.value if isinstance(node, ast.Constant) else default


def _kw(call: ast.Call, name: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _app_version() -> str:
    src = (BACKEND / "app" / "main.py").read_text(encoding="utf-8")
    m = re.search(r'version\s*=\s*"([\d.]+)"', src)
    return m.group(1) if m else "0.14.0"


def dynamic_openapi() -> dict | None:
    """导入 FastAPI app 生成完整契约; 依赖缺失时返回 None 由静态模式接管。"""
    os.environ.setdefault("APP_ENV", "test")
    os.environ.setdefault("SECRET_KEY", "contract-export-key-32-chars-minimum!!")
    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))
    try:
        from app.main import app  # noqa: PLC0415 - 延迟导入, 允许静态模式无依赖运行
    except Exception as exc:  # noqa: BLE001 - 依赖缺失/启动时检查失败时降级为静态提取
        print(f"[export-openapi] dynamic 模式不可用 ({type(exc).__name__}: {exc}), 使用 static 模式")
        return None
    return app.openapi()


def _router_includes() -> list[dict]:
    """解析 router.py 的 include_router: (module, router_var, prefix, tags)。"""
    tree = ast.parse(ROUTER_FILE.read_text(encoding="utf-8"), filename=str(ROUTER_FILE))
    includes: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr != "include_router" or not node.args:
            continue
        first = node.args[0]
        if not isinstance(first, ast.Attribute) or not isinstance(first.value, ast.Name):
            continue
        tags_node = _kw(node, "tags")
        tags = []
        if isinstance(tags_node, (ast.List, ast.Tuple)):
            tags = [str(_const(e, "")) for e in tags_node.elts if _const(e, None) is not None]
        includes.append({
            "module": first.value.id,
            "router_var": first.attr,
            "prefix": str(_const(_kw(node, "prefix"), "") or ""),
            "tags": tags,
        })
    return includes


def _routes_of(module: str) -> dict[str, list[dict]]:
    """解析某端点模块, 按 router 变量名分组返回 (method, path, summary)。"""
    path = ENDPOINT_DIR / f"{module}.py"
    if not path.is_file():
        return {}
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    router_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            fn = node.value.func
            if isinstance(fn, ast.Name) and fn.id == "APIRouter":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        router_names.add(target.id)
    routes: dict[str, list[dict]] = {name: [] for name in router_names}
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            owner = dec.func.value
            if not isinstance(owner, ast.Name) or owner.id not in router_names:
                continue
            method = dec.func.attr.lower()
            if method not in HTTP_METHODS or not dec.args:
                continue
            route_path = _const(dec.args[0], None)
            if not isinstance(route_path, str):
                continue
            summary = str(_const(_kw(dec, "summary"), "") or node.name)
            routes[owner.id].append({
                "method": method,
                "path": route_path,
                "summary": summary,
                "operation_id": f"{node.name}_{module}",
            })
    return routes


def _normalize(prefix: str, route: str) -> str:
    full = f"/api/{prefix.strip('/')}/{route.lstrip('/')}"
    full = re.sub(r"/{2,}", "/", full)
    return full.rstrip("/") or "/api"


def static_openapi() -> dict:
    """纯 AST 生成覆盖全部端点的 OpenAPI 3.1 文档 (Schema 为通用 object)。

    静态模式无法解析 Pydantic response_model；对已在前端消费、且需要字段级契约
    的端点在此登记 Schema 覆盖，保证重新导出时字段定义不会丢失（决策 1）。
    """
    def response_schema(full: str) -> dict:
        if full == "/api/cabinets":
            cabinet_item = {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "idc_id": {"type": "integer"},
                    "code": {"type": "string"},
                    "room": {"type": "string"},
                    "row": {"type": "string"},
                    "u_total": {"type": "integer"},
                    "u_used": {"type": "integer"},
                    "rated_power_kw": {"type": "number"},
                    "current_power_kw": {"type": "number"},
                    "cooling_capability": {"type": "string", "description": "制冷方式: 风冷/液冷/背板/无"},
                    "cooling_capacity_kw": {"type": "number", "description": "机柜额定制冷容量 kW"},
                    "status": {"type": "string"},
                },
            }
            return {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "page": {"type": "integer"},
                    "size": {"type": "integer"},
                    "items": {"type": "array", "items": cabinet_item},
                },
            }
        return {"type": "object"}

    paths: dict[str, dict] = {}
    for inc in _router_includes():
        routes = _routes_of(inc["module"]).get(inc["router_var"], [])
        for r in routes:
            full = _normalize(inc["prefix"], r["path"])
            params = [
                {"name": name, "in": "path", "required": True, "schema": {"type": "string"}}
                for name in re.findall(r"\{(\w+)(?::[^}]+)?\}", full)
            ]
            operation = {
                "tags": inc["tags"] or [inc["module"]],
                "summary": r["summary"],
                "operationId": r["operation_id"],
                "parameters": params,
                "responses": {
                    "200": {
                        "description": "Successful Response",
                        "content": {"application/json": {"schema": response_schema(full)}},
                    }
                },
            }
            paths.setdefault(full, {})[r["method"]] = operation
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "DC-IOC Platform API (static contract)",
            "version": _app_version(),
            "description": "由 scripts/export_openapi.py 静态 AST 提取; 安装完整依赖后 dynamic 模式会补充完整 Schema。",
        },
        "paths": dict(sorted(paths.items())),
        "components": {"schemas": {}},
    }


def path_set(doc: dict) -> set[tuple[str, str]]:
    return {
        (method.upper(), path)
        for path, ops in (doc.get("paths") or {}).items()
        for method in ops
        if method.lower() in HTTP_METHODS
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="导出/校验全量 OpenAPI 契约")
    parser.add_argument("--static", action="store_true", help="强制静态 AST 提取")
    parser.add_argument("--check", action="store_true", help="只比对已提交契约, 不写文件")
    args = parser.parse_args()

    doc = None if args.static else dynamic_openapi()
    mode = "dynamic" if doc is not None else "static"
    doc = doc if doc is not None else static_openapi()
    print(f"[export-openapi] mode={mode}, paths={len(doc.get('paths', {}))}, "
          f"operations={len(path_set(doc))}")

    if args.check:
        if not FRONTEND_CONTRACT.is_file():
            print(f"[export-openapi] 缺少已提交契约: {FRONTEND_CONTRACT}")
            return 1
        committed = json.loads(FRONTEND_CONTRACT.read_text(encoding="utf-8"))
        current, old = path_set(doc), path_set(committed)
        added, missing = sorted(current - old), sorted(old - current)
        print(f"[export-openapi] 新增端点 {len(added)} / 缺失端点 {len(missing)}")
        for item in added[:20]:
            print("  +", item)
        for item in missing[:20]:
            print("  -", item)
        return 1 if missing else 0

    payload = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    BACKEND_CONTRACT.write_text(payload, encoding="utf-8")
    FRONTEND_CONTRACT.write_text(payload, encoding="utf-8")
    print(f"[export-openapi] 已写入 {BACKEND_CONTRACT} 与 {FRONTEND_CONTRACT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
