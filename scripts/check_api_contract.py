"""契约漂移门禁 (P1-2.4 / P2-1.2): CI 中校验前端 openapi.json 与后端路由一致。

- 使用 `backend/scripts/export_openapi.py --check --static`, 纯 stdlib, 不依赖后端运行依赖。
- 额外校验契约结构合法性与端点数量下限 (默认 100, 防止误提交 29 端点的旧契约)。

用法: python scripts/check_api_contract.py [--min-endpoints N]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "backend" / "scripts" / "export_openapi.py"
CONTRACT = ROOT / "frontend" / "openapi.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="OpenAPI 契约漂移门禁")
    parser.add_argument("--min-endpoints", type=int, default=100)
    args = parser.parse_args()

    if not CONTRACT.is_file():
        print(f"[api-contract] 缺少契约文件: {CONTRACT}")
        return 1
    try:
        doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[api-contract] 契约不是合法 JSON: {exc}")
        return 1
    if not isinstance(doc.get("paths"), dict) or not isinstance(doc.get("info"), dict):
        print("[api-contract] 契约缺少 paths / info")
        return 1

    result = subprocess.run(
        [sys.executable, str(EXPORTER), "--check", "--static"],
        cwd=str(ROOT / "backend"),
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout.rstrip())
    if result.stderr.strip():
        print(result.stderr.rstrip())
    if result.returncode != 0:
        print("[api-contract] 契约漂移: 请运行 `python backend/scripts/export_openapi.py --static` 后提交")
        return result.returncode

    operations = sum(
        1
        for ops in doc["paths"].values()
        for method in ops
        if method.lower() in {"get", "post", "put", "delete", "patch"}
    )
    if operations < args.min_endpoints:
        print(f"[api-contract] 端点数 {operations} < 下限 {args.min_endpoints}, 疑似半成品契约")
        return 1
    print(f"[api-contract] OK: {len(doc['paths'])} paths / {operations} operations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
