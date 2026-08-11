"""Dify 知识库检索客户端（RAG 接入层）。

职责：把「知识库检索」从本地关键词打分升级为 Dify 向量召回，但保持对离线/异常的
强鲁棒性——任何异常都会被调用方捕获并回退到本地关键词打分，绝不阻断问答。

设计对齐 assistant_service.py 现有风格：
- 标准库 urllib 实现，无第三方依赖；
- 复用 LLM_TIMEOUT 思路设置超时；
- 失败抛异常（不静默返回空），由 assistant_service._retrieve 兜底。
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger("dify_client")


def dify_configured() -> bool:
    """是否已配置 Dify（API Key + 知识库 ID）。"""
    return bool(settings.DIFY_API_KEY and settings.DIFY_DATASET_ID)


def _retrieve_url() -> str:
    base = settings.DIFY_BASE_URL.rstrip("/")
    return f"{base}/datasets/{settings.DIFY_DATASET_ID}/retrieve"


def _timeout() -> int:
    try:
        return int(getattr(settings, "LLM_TIMEOUT", None) or 15)
    except (TypeError, ValueError):
        return 15


def dify_retrieve(question: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    """调用 Dify Knowledge API 召回片段。

    返回结构（归一化后）：
    [
      {
        "content": str,            # 召回的文本片段
        "score": float,            # Dify 返回的相似度分数（已尽量归一化到 0~1）
        "title": str,              # 文档标题（若有）
        "doc_id": str,             # 文档 id（若有）
        "metadata": dict,          # 文档元数据（若有）
      },
      ...
    ]

    任一异常都会向上抛出，由调用方 (_retrieve) 兜底到本地关键词打分。
    """
    if not dify_configured():
        raise RuntimeError("Dify 未配置 (缺少 DIFY_API_KEY 或 DIFY_DATASET_ID)")

    top_k = top_k or settings.DIFY_RETRIEVE_TOP_K
    url = _retrieve_url()
    payload = {
        "query": question,
        "retrieval_model": {
            "top_k": top_k,
            "score_threshold": 0.0,
        },
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {settings.DIFY_API_KEY}",
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=_timeout()) as resp:
        latency = round(time.time() - t0, 3)
        j = json.loads(resp.read().decode("utf-8"))

    records: List[Dict[str, Any]] = []
    # Dify 返回结构: {"data": {"records": [{"score":..., "content":..., "document": {...}}]}}
    records_raw = j.get("data", {}).get("records", []) if isinstance(j.get("data"), dict) else []
    for r in records_raw:
        if not isinstance(r, dict):
            continue
        doc = r.get("document") or {}
        content = r.get("content") or ""
        score = r.get("score")
        try:
            score = float(score) if score is not None else 0.0
        except (TypeError, ValueError):
            score = 0.0
        # 部分 Dify 版本返回的是余弦相似度（可能 >1），归一化到 0~1 方便统一阈值处理
        norm_score = min(max(score, 0.0), 1.0)
        records.append(
            {
                "content": content,
                "score": norm_score,
                "title": (doc.get("name") or doc.get("title") or "") if isinstance(doc, dict) else "",
                "doc_id": (doc.get("id") or "") if isinstance(doc, dict) else "",
                "metadata": doc.get("metadata") or {} if isinstance(doc, dict) else {},
            }
        )
    logger.info("Dify 检索成功: 命中 %d 条 (latency=%.3fs)", len(records), latency)
    return records
