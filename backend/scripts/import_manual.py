#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运维指导书自动入库脚本 (方案 C: 按章节切分为多条)。

把一本横跨多个专业的指导书，按章节 / 处置场景切分为「多条」知识库条目
(type=manual) 入库，每条精准匹配业务域 (domain) 与专业 (category)。
解析与切分逻辑统一复用 app.services.manual_import，避免与服务端分叉。

支持输入:
  - 纯文本  .txt   (自动清洗 OCR/提取产生的逐字换行)
  - PDF     .pdf   (优先 PyMuPDF，降级 pdfplumber)
  - Word    .docx  (需要 python-docx)

用法:
  python import_manual.py --src manual.txt
  python import_manual.py --src manual.pdf --dry-run
  python import_manual.py --src manual.docx --title "xxx" --category "暖通-冷源"
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# 让脚本可直接运行: 将 backend/ 加入 path 以便 import app.*
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.services import manual_import as mi  # noqa: E402
from app.crud import knowledge as kb_crud  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402


def save_via_db(payloads: list[dict]) -> list[dict]:
    db = SessionLocal()
    try:
        existing = {it["title"] for it in kb_crud.list_items(db, limit=100000)}
        created: list[dict] = []
        skipped = 0
        for p in payloads:
            if p["title"] in existing:
                skipped += 1
                continue
            item = kb_crud.create(db, data=p)
            created.append(item)
            existing.add(item["title"])
        if skipped:
            print(f"[跳过] {skipped} 条标题已存在 (去重)")
        return created
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="运维指导书自动入库 (按章节切分为多条)")
    ap.add_argument("--src", required=True, help="源文件: .txt / .pdf / .docx")
    ap.add_argument("--title", default=None, help="覆盖文档标题")
    ap.add_argument("--category", default=None, help="覆盖主专业")
    ap.add_argument("--dry-run", action="store_true", help="只打印识别结果，不入库")
    args = ap.parse_args()

    if not os.path.exists(args.src):
        sys.exit("文件不存在: " + args.src)

    payloads = mi.build_payloads(args.src, args.title, args.category)

    print("=" * 60)
    print(f"切分得到 {len(payloads)} 条知识条目:")
    print("=" * 60)
    for i, p in enumerate(payloads, 1):
        print(f"[{i}] {p['title']}")
        print(f"    专业/域 : {p['category']} / {p['domain']}")
        print(f"    关联域  : {p['relatedDomains']}")
        print(f"    步骤数  : {len(p['steps'])}  正文: {len(p['content'])} 字符")

    if args.dry_run:
        print("\n[dry-run] 未写入数据库。完整 payloads:")
        print(json.dumps(payloads, ensure_ascii=False, indent=2))
        return

    created = save_via_db(payloads)
    print(f"\n[OK] 已入库 {len(created)} 条")
    for obj in created:
        print(f"  -> code={obj['code']} | {obj['title']} | {obj['domain']} | {obj['category']}")


if __name__ == "__main__":
    main()
