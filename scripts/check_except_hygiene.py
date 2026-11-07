"""异常卫生门禁 (P1-2.2): 防止新增模块回潮「裸 except / 静默吞异常」。

背景:
  ruff 的 E722 (裸 except:) 已由 backend/ruff.toml 的 E7 规则族启用；
  BLE001 (except Exception 且未记录日志) 若全局开启会命中大量存量模块,
  因此改为按「新增模块白名单」做 AST 门禁 —— 新代码零容忍, 存量代码不阻断。

检查规则 (每个 ExceptHandler):
  1. `except:`                       -> 直接失败 (等价于 E722)
  2. `except Exception:` 且处理器体内没有以下任一动作 -> 失败:
       - logger/logging 调用 (logger.exception / logger.warning / log.* 等)
       - raise / return / continue / break
       - 显式 `# noqa: BLE001` 注释 (在该行或处理器首行)
     仅 `pass` 或仅赋值/占位视为静默吞异常。

用法:
  python scripts/check_except_hygiene.py                 # 检查内置白名单 (缺失文件自动跳过)
  python scripts/check_except_hygiene.py --paths a.py b.py
  python scripts/check_except_hygiene.py --all app/     # 全量体检 (只报告, 退出码仍按白名单)

CI: backend 作业在 ruff 之后执行 `python ../scripts/check_except_hygiene.py`。
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# P2~P4 新增后端模块 (相对仓库根)。文件尚不存在时跳过, 便于 P1 阶段先行启用门禁。
NEW_MODULES: tuple[str, ...] = (
    "backend/app/api/v1/endpoints/ci_relation.py",
    "backend/app/crud/ci_relation.py",
    "backend/app/services/ci_relation_service.py",
    # 阶段三按层合并实现 (见 docs/IMPLEMENTATION_PLAN.md)
    "backend/app/api/v1/endpoints/p3.py",
    "backend/app/crud/p3.py",
    "backend/app/services/p3_services.py",
    "backend/app/models/p3.py",
    "backend/app/schemas/p3.py",
    "backend/app/core/plugin_registry.py",
    "backend/app/api/v1/endpoints/plugins.py",
    "backend/app/graphql/schema.py",
    "backend/app/core/tenant_context.py",
    "backend/app/core/tenant_middleware.py",
    "backend/app/db/session.py",
)

_LOG_NAMES = ("logger", "log", "logging", "LOG")
_OK_NODES = (ast.Raise, ast.Return, ast.Continue, ast.Break)


def _calls_logger(node: ast.AST) -> bool:
    for sub in ast.walk(node):
        if not isinstance(sub, ast.Call):
            continue
        func = sub.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id in _LOG_NAMES:
                return True
        if isinstance(func, ast.Name) and func.id in _LOG_NAMES:
            return True
    return False


def _has_noqa(source_lines: list[str], lineno: int, end_lineno: int) -> bool:
    for line in source_lines[max(0, lineno - 1) : max(lineno, end_lineno)]:
        if "# noqa: BLE001" in line:
            return True
    return False


def _handler_ok(handler: ast.ExceptHandler, source_lines: list[str]) -> tuple[bool, str]:
    if handler.type is None:
        return False, "裸 except: (E722)"
    if _has_noqa(source_lines, handler.lineno, handler.lineno + 1):
        return True, ""
    if _calls_logger(ast.Module(body=handler.body, type_ignores=[])):
        return True, ""
    for stmt in handler.body:
        if isinstance(stmt, _OK_NODES):
            return True, ""
        if isinstance(stmt, ast.If) and _calls_logger(stmt):
            return True, ""
    return False, "except Exception 未记录日志且未 raise/return/continue (BLE001)"


def check_file(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [f"{path}: 无法解析 ({exc})"]
    lines = source.splitlines()
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        ok, reason = _handler_ok(node, lines)
        if not ok:
            problems.append(f"{path}:{node.lineno}: {reason}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description="新增模块异常卫生门禁")
    parser.add_argument("--paths", nargs="*", default=None, help="显式指定要检查的文件")
    parser.add_argument("--all", dest="scan_all", nargs="?", const="backend/app", default=None,
                        help="额外全量体检目录 (仅报告, 不影响退出码)")
    args = parser.parse_args()

    targets = [Path(p) for p in (args.paths if args.paths is not None else NEW_MODULES)]
    existing: list[Path] = []
    for t in targets:
        p = t if t.is_absolute() else ROOT / t
        if p.is_file():
            existing.append(p)

    problems: list[str] = []
    for p in existing:
        problems.extend(check_file(p))

    print(f"[异常卫生] 检查 {len(existing)} 个新增模块, 问题 {len(problems)} 处")
    for item in problems:
        print("  -", item)

    if args.scan_all:
        scan_root = ROOT / args.scan_all
        total = 0
        if scan_root.is_dir():
            for p in scan_root.rglob("*.py"):
                found = check_file(p)
                total += len(found)
                print("  [存量体检]", found)
        print(f"[全量体检] {scan_root} 共 {total} 处 (仅报告, 不影响退出码)")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
