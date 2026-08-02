"""静态 AST 提取 API 端点 -> backend/api_endpoints.md (无需运行环境)。"""
import os
import ast
import glob

EP_DIR = os.path.join(os.path.dirname(__file__), "app", "api", "v1", "endpoints")
OUT = os.path.join(os.path.dirname(__file__), "api_endpoints.md")

HTTP = {"get", "post", "put", "delete", "patch"}


def _extract_perms(node):
    out = []
    if isinstance(node, ast.Call):
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
        if name in ("require_role", "require_auth", "require_permission"):
            out.append(name)
        for a in node.args:
            out.extend(_extract_perms(a))
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "Depends":
        out.extend(_extract_perms(node.args[0]) if node.args else [])
    return out


rows = []
for fpath in sorted(glob.glob(os.path.join(EP_DIR, "*.py"))):
    if os.path.basename(fpath) == "__init__.py":
        continue
    src = open(fpath, encoding="utf-8").read()
    tree = ast.parse(src)
    router_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and isinstance(node.value, ast.Call):
                    fn = node.value.func
                    if isinstance(fn, ast.Name) and fn.id == "APIRouter":
                        router_names.add(t.id)
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                    and isinstance(dec.func.value, ast.Name) and dec.func.value.id in router_names
                    and dec.func.attr in HTTP):
                path_arg = dec.args[0] if dec.args else None
                if not isinstance(path_arg, ast.Constant):
                    continue
                path = path_arg.value
                perms = []
                for kw in dec.keywords:
                    if kw.arg == "dependencies":
                        val = kw.value
                        if isinstance(val, (ast.List, ast.Tuple)):
                            for elt in val.elts:
                                perms.extend(_extract_perms(elt))
                rows.append((dec.func.attr.upper(), path, ",".join(sorted(set(perms))) or "-"))

rows.sort(key=lambda r: (r[1], r[0]))
content = "# 后端 API 端点清单（静态提取）\n\n"
content += "> `python gen_api.py` 静态 AST 扫描 `app/api/v1/endpoints/*.py`。\n\n"
content += "| 方法 | 路径 | 权限依赖 |\n|------|------|-----------|\n"
content += "\n".join(f"| {m:6} | {p} | {perm} |" for m, p, perm in rows) + "\n"

with open(OUT, "w", encoding="utf-8") as f:
    f.write(content)
print(f"OK: {len(rows)} 个 API 端点 -> {OUT}")
