#!/usr/bin/env python3
"""i18n 键对齐审计: 对比 zh-CN.json 与 en-US.json 的嵌套 key 集合。

用法 (仓库根目录):
    python scripts/check_i18n_keys.py            # 打印差异清单
    python scripts/check_i18n_keys.py --json     # 以 JSON 输出 (供 CI 消费)

退出码: 有差异返回 1, 完全对齐返回 0 —— 可直接接入 CI 门禁。

判定规则:
- 递归展开两份 locale 为 "点分路径" 集合 (叶子节点为止)。
- 一侧是对象另一侧是字符串 (类型冲突) 时, 该路径同时计入双方的 "类型冲突" 清单。
- 双向报告: en 缺失 (zh 有 en 无) 与 zh 缺失 (en 有 zh 无)。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ROOT / "frontend" / "src" / "i18n" / "locales"


def flatten(obj, prefix: str = "") -> dict:
    """递归展开为 {点分路径: 叶子值}; 路径段里的点原样保留 (本项目 key 无点)。"""
    out: dict = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            path = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(flatten(v, path))
            else:
                out[path] = v
    else:
        out[prefix] = obj
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="对比 zh-CN/en-US 嵌套 key 集合")
    ap.add_argument("--json", action="store_true", help="JSON 输出 (CI 用)")
    args = ap.parse_args()

    zh = flatten(json.loads((LOCALES / "zh-CN.json").read_text(encoding="utf-8")))
    en = flatten(json.loads((LOCALES / "en-US.json").read_text(encoding="utf-8")))

    zh_keys, en_keys = set(zh), set(en)
    missing_in_en = sorted(zh_keys - en_keys)
    missing_in_zh = sorted(en_keys - zh_keys)

    # 类型冲突: 同一路径一侧是叶子另一侧是中间对象
    # (表现为: zh 有 "a.b.c" 而 en 只有 "a.b" 且其下还有子键 → "a.b" 不会出现在
    #  missing 清单里, 因为 flatten 只收集叶子; 需要用 "前缀包含" 检测)
    type_conflicts = sorted(
        k
        for k in (zh_keys & en_keys)
        if isinstance(zh.get(k), dict) or isinstance(en.get(k), dict)
    )
    # flatten 只放叶子, dict 值不会出现; 真正的类型冲突是:
    # 一侧路径 P 是叶子, 另一侧存在 P.x 的叶子
    en_only_children = {k.rsplit(".", 1)[0] for k in missing_in_zh if "." in k}
    zh_only_children = {k.rsplit(".", 1)[0] for k in missing_in_en if "." in k}
    type_conflicts = sorted(
        k for k in (en_only_children & zh_keys) | (zh_only_children & en_keys)
    )

    ok = not (missing_in_en or missing_in_zh or type_conflicts)
    result = {
        "ok": ok,
        "zh_total": len(zh_keys),
        "en_total": len(en_keys),
        "missing_in_en": missing_in_en,
        "missing_in_zh": missing_in_zh,
        "type_conflicts": type_conflicts,
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    print(f"zh-CN keys: {len(zh_keys)}  |  en-US keys: {len(en_keys)}")
    if ok:
        print("OK: 两份 locale 的 key 集合完全对齐")
        return 0

    if missing_in_en:
        print(f"\n[en-US 缺失 {len(missing_in_en)} 个]")
        for k in missing_in_en:
            print(f"  - {k}  = {json.dumps(zh[k], ensure_ascii=False)}")
    if missing_in_zh:
        print(f"\n[zh-CN 缺失 {len(missing_in_zh)} 个]")
        for k in missing_in_zh:
            print(f"  - {k}  = {json.dumps(en[k], ensure_ascii=False)}")
    if type_conflicts:
        print(f"\n[类型冲突 {len(type_conflicts)} 个]")
        for k in type_conflicts:
            print(f"  - {k}")
    print("\n结果: 不对齐, 请按清单补齐后复跑")
    return 1


if __name__ == "__main__":
    sys.exit(main())
