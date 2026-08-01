"""运维指导书解析、章节切分与跨专业识别。

供「后端 API 一键导入」与「CLI 脚本 import_manual.py」复用。

把一本横跨多个专业的指导书，按章节 / 处置场景切分为「多条」知识库条目
(type=manual)，每条具备精准的 title / summary / steps / domain，从而显著提升
AI 运维助手的检索命中率与答案相关性（方案 C：知识切分）。

依赖:
  - 纯文本 .txt   无需额外库
  - PDF     .pdf   优先 PyMuPDF(fitz)，降级 pdfplumber
  - Word    .docx   需要 python-docx
"""
from __future__ import annotations

import os
import re

# 业务域 / 专业关键词映射 (顺序即优先级: 靠前的作为主域)
DOMAIN_MAP = [
    ("hvac_source", "暖通-冷源", ["冷源", "冷机", "chiller", "冷水机组", "冷冻泵",
                                "冷却塔", "冷凝", "蒸发", "板换", "喘振", "导叶",
                                "群控", "一次泵", "二次泵", "蓄冷", "冷冻水", "冷却水"]),
    ("hvac_terminal", "暖通-末端", ["精密空调", "末端空调", "空调", "ahu", "风机",
                                  "加湿", "除湿", "恒湿", "温湿度", "冷热通道",
                                  "送风", "回风", "静电地板", "列间空调"]),
    ("power_genset", "电力-柴发", ["柴发", "柴油发电机", "发电机组", "应急发电",
                                 "并机", "油机", "市电中断", "自启", "燃油"]),
    ("power_ups", "电力-UPS", ["ups", "蓄电池", "电池组", "逆变", "不间断",
                              "内阻", "电池", "电解液", "均充", "浮充"]),
    ("power_hv", "电力-高压", ["高压", "中压", "10kv", "35kv", "开关柜",
                             "变压器", "母联", "进线"]),
    ("power_lv", "电力-低压", ["低压", "配电", "列头柜", "pdu", "市电", "电容",
                             "断路器", "无功", "抽屉"]),
    ("sec_fire", "安防-消防", ["消防", "烟感", "温感", "火警", "气体灭火",
                             "喷淋", "防火", "手报", "极早期", "气灭", "钢瓶",
                             "疏散", "声光"]),
    ("sec_security", "安防-安防", ["门禁", "读卡", "人脸识别", "电锁", "安防",
                                "监控", "摄像头", "入侵", "周界", "探测器",
                                "视频", "球机", "枪机", "矩阵"]),
    ("bms", "楼控-BA", ["ba", "楼控", "通讯", "总线", "modbus", "bacnet",
                      "网关", "离线", "链路"]),
    ("water", "给排水", ["漏水", "给水", "排水", "水泵", "水位"]),
    ("dcim", "DCIM", ["dcim", "容量管理", "资产管理", "三维", "可视化"]),
]
DOMAIN_CAT = {dom: cat for dom, cat, _ in DOMAIN_MAP}

# 业务域 -> 中文标签 (用于 tags)
DOMAIN_LABEL = {
    "hvac_source": "冷源", "hvac_terminal": "末端空调", "power_genset": "柴油发电机",
    "power_ups": "UPS蓄电池", "power_hv": "高压", "power_lv": "低压配电",
    "sec_fire": "消防", "sec_security": "安防", "bms": "楼控BA", "water": "给排水",
    "dcim": "DCIM", "general": "通用",
}

# 章节标题判定: 编号标题若含这些主题词, 视为章节标题而非操作步骤
HEADING_TOPIC = ["系统", "监控", "控制", "设计", "原则", "架构", "能力", "操作",
                "维护", "原理", "实现", "组成", "岗位", "介绍", "概述", "目录",
                "目标", "流程", "预案", "方案", "要求", "规范", "标准", "策略",
                "模式", "架构图", "图", "表", "逻辑", "工艺", "架构及", "维护及"]
# 排除: 课程目标式的「了解/掌握…」清单项不当作章节
OBJ_VERB = ["了解", "掌握", "熟悉", "具备", "理解", "能够", "会", "懂得"]

# 指标关键词 -> metric_name (用于告警关联 relatedMetrics)
METRIC_MAP = [
    ("supply_temp", ["出水温度", "冷冻水出水", "供冷温度"]),
    ("return_temp", ["回水温度", "冷冻水回水"]),
    ("evap_temp", ["蒸发温度", "蒸发压力"]),
    ("cond_temp", ["冷凝温度", "冷凝压力"]),
    ("humidity", ["湿度", "相对湿度"]),
    ("voltage", ["电压", "母线电压"]),
    ("current", ["电流", "负载电流"]),
    ("temperature", ["温度", "温升"]),
    ("power", ["功率", "负荷"]),
    ("soc", ["电量", "soc", "容量"]),
    ("flow", ["流量", "水流量"]),
    ("pressure", ["压力", "压差"]),
]

# 标题行正则
_RE_ZH_PART = re.compile(r"^\s*第\s*[一二三四五六七八九十百零\d]+\s*[章节篇部]")
_RE_ZH_SEQ = re.compile(r"^\s*[一二三四五六七八九十]+\s*[、.．]\s*[\u4e00-\u9fff]")
_RE_ZH_ORDER = re.compile(r"^\s*[（(][一二三四五六七八九十]+\s*[）)]\s*[\u4e00-\u9fff]")
_RE_SUB = re.compile(r"^\s*(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s+([\u4e00-\u9fffA-Za-z][^\n]{0,60})$")
_RE_TOP = re.compile(r"^\s*(\d{1,2})\s*[.、]\s*([\u4e00-\u9fffA-Za-z][^\n]{0,60})$")
_RE_PLAIN_TITLE = re.compile(r"^[\u4e00-\u9fffA-Za-z][\u4e00-\u9fff\w\-/]{3,28}$")


def extract_text(src: str) -> str:
    """读取源文件文本。PDF/Word 缺失解析库时抛 RuntimeError。"""
    ext = os.path.splitext(src)[1].lower()
    if ext == ".txt":
        with open(src, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF  # type: ignore

            doc = fitz.open(src)
            try:
                parts = [page.get_text("text") for page in doc]
            finally:
                doc.close()
            return "\n".join(parts)
        except ImportError:
            try:
                import pdfplumber  # type: ignore
            except ImportError:
                raise RuntimeError("解析 PDF 需要 PyMuPDF 或 pdfplumber，请先执行: pip install pymupdf")
            parts = []
            with pdfplumber.open(src) as pdf:  # type: ignore
                for pg in pdf.pages:
                    parts.append(pg.extract_text() or "")
            return "\n".join(parts)
    if ext in (".docx", ".doc"):
        try:
            import docx  # type: ignore
        except ImportError:
            raise RuntimeError("解析 Word 需要 python-docx，请先执行: pip install python-docx")
        return "\n".join(p.text for p in docx.Document(src).paragraphs)  # type: ignore
    raise RuntimeError("不支持的文件类型: " + ext)


def _is_garbage(line: str) -> bool:
    """丢弃 OCR/提取产生的乱码行 (如二进制流被误识别为文字)。"""
    s = line.strip()
    if not s:
        return True
    # 竖排页眉/页脚单字噪声 (阿 里 云 全 球 培 训 中 心)
    if len(s) <= 2 and re.fullmatch(r"[\u4e00-\u9fff]", s):
        return True
    if "\ufffd" in s:
        return True
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", s):
        return True
    # 安全字符 = 中文 + 常见 ASCII 字母数字与标点
    safe = sum(1 for ch in s if ("\u4e00" <= ch <= "\u9fff") or (ch.isascii() and (ch.isalnum() or ch in ".-/()（）：:、,，;； ")))
    if len(s) > 3 and safe < len(s) * 0.6:
        return True
    return False


def clean_text(raw: str) -> str:
    """清洗 OCR/提取工具产生的逐字换行、页码标记与乱码。"""
    out: list[str] = []
    for ln in raw.splitlines():
        s = ln.strip()
        if not s:
            continue
        if re.match(r"^=+\s*PAGE\s+\d+\s*=+$", s, re.I):
            continue
        if s in ("‹#›",):  # PPT 分页符
            continue
        if _is_garbage(s):
            continue
        out.append(s)
    text = "\n".join(out)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def detect_domains(text: str) -> list[tuple[str, str]]:
    """基于关键词字典识别涉及的业务域与专业。"""
    found: list[tuple[str, str]] = []
    low = text.lower()
    for dom, cat, kws in DOMAIN_MAP:
        if any(kw.lower() in low for kw in kws):
            found.append((dom, cat))
    return found


def detect_metrics(text: str) -> list[str]:
    low = text.lower()
    return [name for name, kws in METRIC_MAP if any(kw.lower() in low for kw in kws)]


def derive_title(text: str, src: str) -> str:
    for line in text.splitlines():
        s = line.strip()
        if s and not re.match(r"^=+", s) and len(s) >= 4:
            return s[:60]
    return os.path.splitext(os.path.basename(src))[0]


def extract_steps(text: str, max_n: int = 30) -> list[str]:
    """提取正文中的编号步骤 (一级/二级序号)，排除课程目标式清单项与项目符号噪声。"""
    steps: list[str] = []
    for m in re.finditer(r"^\s*(\d+(?:\.\d+)*)\s+([^\n]{4,60})", text, re.M):
        t = m.group(2).strip()
        if t[:1] in ("•", "·", "-", "—", "*", "、"):
            continue
        if any(t.startswith(v) for v in OBJ_VERB):
            continue
        steps.append(t)
        if len(steps) >= max_n:
            break
    return steps


def _classify_heading(line: str, next_line) -> tuple[str, str] | None:
    """判断一行是否为章节标题，返回 (类型, 清洗后的标题)。"""
    s = line.strip()
    if not s or _is_garbage(s):
        return None
    if s in ("课程目录", "目录", "CONTENTS"):
        return ("toc", s)
    if _RE_ZH_PART.match(s):
        return ("zh_part", s)
    if _RE_ZH_SEQ.match(s) or _RE_ZH_ORDER.match(s):
        return ("zh_seq", s)
    m = _RE_SUB.match(s)
    if m:
        return ("sub", m.group(2).strip())
    m = _RE_TOP.match(s)
    if m:
        title = m.group(2).strip()
        if any(title.startswith(v) for v in OBJ_VERB):
            return None  # 课程目标清单项, 不当作章节
        if any(w in title for w in HEADING_TOPIC):
            return ("top", title)
        return None  # 形如 "1. 确认市电失电" 的操作步骤, 不是章节
    m = _RE_PLAIN_TITLE.match(s)
    if m and next_line is not None and next_line.strip().startswith(("•", "·", "-", "—", "*")):
        return ("plain", s)
    return None


def split_sections(text: str, min_body: int = 30) -> list[dict]:
    """按章节标题把正文切分为若干 (heading, body) 片段。

    对 PPT/培训讲义类文档 (正文以图表为主、可提取文字稀少) 做「薄章节合并」:
    正文不足 min_body 字符的片段, 其标题与正文并入上一个真实片段, 避免出现
    大量空壳条目; 同时保留其标题关键词以提升检索命中率。
    """
    lines = text.split("\n")
    raw: list[dict] = []
    cur: dict | None = None
    for i, line in enumerate(lines):
        nxt = lines[i + 1] if i + 1 < len(lines) else None
        h = _classify_heading(line, nxt)
        if h:
            if cur:
                raw.append(cur)
            cur = {"heading": h[1], "body": []}
        else:
            if cur is None:
                cur = {"heading": "", "body": []}
            cur["body"].append(line)
    if cur:
        raw.append(cur)

    sections: list[dict] = []
    for sec in raw:
        body = "\n".join(l for l in sec["body"] if l.strip())
        body = re.sub(r"[ \t]{2,}", " ", body).strip()
        sections.append({"heading": sec["heading"], "body": body})

    merged: list[dict] = []
    for sec in sections:
        if sec["body"] and len(sec["body"]) >= min_body:
            merged.append(sec)
        elif merged:
            prev = merged[-1]
            add = (sec["heading"] + " " + sec["body"]).strip()
            prev["body"] = (prev["body"] + "\n" + add).strip()
            if sec["heading"] and not prev["heading"]:
                prev["heading"] = sec["heading"]
        else:
            # 首个片段即使偏薄也保留为概述
            merged.append(sec)
    return merged


def build_payloads(src: str, title: str | None = None, category: str | None = None) -> list[dict]:
    """把一本指导书按章节切分为多条知识库条目载荷 (方案 C 核心)。

    返回列表, 每条对应一个章节/处置场景, 具备精准的 title / summary / steps / domain。
    """
    raw = extract_text(src)
    text = clean_text(raw)
    doc_title = title or derive_title(text, src)
    sections = split_sections(text)

    payloads: list[dict] = []
    for sec in sections:
        heading = sec["heading"]
        body = sec["body"]
        if not body:
            continue
        if heading in ("课程目录", "目录", "CONTENTS"):  # 跳过纯目录噪音
            continue

        found = detect_domains(body)
        domains = [d for d, _ in found]
        main_domain = domains[0] if domains else "general"
        main_category = category or DOMAIN_CAT.get(main_domain, "综合")

        summary = re.sub(r"\s+", " ", body)[:200]
        steps = extract_steps(body)

        # 标签: 业务域中文标签 + 章节标题里的实词
        tags = [DOMAIN_LABEL.get(main_domain, "通用")]
        h_clean = re.sub(r"^\s*[\d.、（）()第章节篇部]+", "", heading).strip()
        if 2 <= len(h_clean) <= 14:
            tags.append(h_clean)
        tags = list(dict.fromkeys(tags))[:6]

        sec_title = (doc_title + " · " + heading) if heading and heading != doc_title else (heading or doc_title)
        payloads.append({
            "title": sec_title[:120],
            "category": main_category,
            "domain": main_domain,
            "type": "manual",
            "summary": summary,
            "content": body,
            "steps": steps,
            "tags": tags,
            "relatedDomains": domains[:4],
            "relatedCategories": [main_category],
            "relatedMetrics": detect_metrics(body),
            "owner": "auto-import",
            "hot": False,
        })

    # 兜底: 完全切不出章节时, 退化为整本一条 (保持旧行为)
    if not payloads and text.strip():
        found = detect_domains(text)
        domains = [d for d, _ in found]
        main_domain = domains[0] if domains else "general"
        main_category = category or DOMAIN_CAT.get(main_domain, "综合")
        payloads.append({
            "title": doc_title[:120],
            "category": main_category,
            "domain": main_domain,
            "type": "manual",
            "summary": re.sub(r"\s+", " ", text)[:200],
            "content": text,
            "steps": extract_steps(text),
            "tags": [DOMAIN_LABEL.get(main_domain, "通用")],
            "relatedDomains": domains[:4],
            "relatedCategories": [main_category],
            "relatedMetrics": detect_metrics(text),
            "owner": "auto-import",
            "hot": False,
        })
    return payloads


def build_payload(src: str, title: str | None = None, category: str | None = None) -> dict:
    """兼容旧调用方: 返回整本切分后的首条 (多为概述/前言)。"""
    ps = build_payloads(src, title, category)
    return ps[0] if ps else {}
