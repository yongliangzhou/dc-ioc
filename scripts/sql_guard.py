#!/usr/bin/env python3
"""[S-08] SQL 注入静态门禁。

目标: 防止在代码中出现「把外部输入拼进原生 SQL」的危险写法。
项目约定使用 SQLAlchemy ORM 或 `text("... :param")` 参数化查询, 禁止:

  1. f-string 插值进 SQL 调用, 例如:
        db.execute(text(f"SELECT * FROM t WHERE id = {user_id}"))   # 致命
  2. 字符串拼接 (+ / % / .format) 拼出 SQL:
        db.execute(text("SELECT * FROM t WHERE id = " + uid))        # 致命

以下情况**允许**(需显式豁免注释 `# sql-guard-ignore`):
  - 拼接内容为代码字面量常量 (如物化视图名、固定白名单表/列名), 非用户输入。

用法:
    python scripts/sql_guard.py                 # 扫描 backend/app
    python scripts/sql_guard.py backend/app x.py # 指定路径
    exit code: 0 通过 / 1 发现致命问题
"""
from __future__ import annotations

import sys
from pathlib import Path

# SQL 调用前缀 (后接 `(` 且第一个参数疑似拼接/插值)
_SQL_CALL_RE = __import__("re").compile(
    r"""(?:text|execute|session\.execute|conn\.execute)\s*\("""
)
# f-string 作为 SQL 调用首参
_FSTRING_RE = __import__("re").compile(r'''\((?:\s*f["']|f["'])''')
# 字符串拼接: 同行的文本 + 运算符, 且上下文含 SQL 关键字
_CONCAT_RE = __import__("re").compile(
    r"(\+\s*[\"']|[\"']\s*\+|\%\s*\(|\.format\s*\()"
)
_SQL_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "FROM", "WHERE")

_IGNORE_MARK = "sql-guard-ignore"
_DEFAULT_PATHS = ["backend/app"]


def _looks_like_sql(line: str) -> bool:
    up = line.upper()
    return any(kw in up for kw in _SQL_KEYWORDS)


def scan_file(path: Path) -> list[str]:
    """返回该文件内的致命问题行 (格式: '<rel>:<ln>  <msg>')。"""
    problems: list[str] = None  # type: ignore
    problems = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return problems
    for ln, raw in enumerate(text.splitlines(), 1):
        line = raw.rstrip("\n")
        if _IGNORE_MARK in line:
            continue
        if not _SQL_CALL_RE.search(line):
            continue
        # 规则1: f-string 插值进 SQL 调用
        if _FSTRING_RE.search(line):
            problems.append(f"{path}:{ln}  f-string 插值进 SQL 调用 (疑似注入)")
            continue
        # 规则2: 字符串拼接且上下文像 SQL
        if _CONCAT_RE.search(line) and _looks_like_sql(line):
            problems.append(f"{path}:{ln}  SQL 字符串拼接 (+/%/.format), 疑似注入")
    return problems


def main(argv: list[str]) -> int:
    roots = argv[1:] or _DEFAULT_PATHS
    targets: list[Path] = []
    for r in roots:
        p = Path(r)
        if p.is_dir():
            targets.extend(p.rglob("*.py"))
        elif p.is_file():
            targets.append(p)
    all_problems: list[str] = []
    for f in targets:
        all_problems.extend(scan_file(f))
    if all_problems:
        print("[SQL-GUARD] FAIL: found suspicious SQL concatenation:")
        for p in all_problems:
            print("   " + p)
        print(
            "\nFix: use parameterized query text(\"SELECT ... WHERE id = :uid\", {\"uid\": uid}); "
            "if it is truly a code-literal concat, append `# sql-guard-ignore` with a reason."
        )
        return 1
    print("[SQL-GUARD] PASS: no dangerous SQL concatenation detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
