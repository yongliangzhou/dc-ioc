"""AI 运维助手：基于知识库检索的处置问答引擎 (RAG-lite)。

策略：
1. 对问题 + 上下文做分词（中文单字/二元 + 英文词），与知识库条目做重叠打分。
2. 取 Top-N 命中条目，抽取其处置步骤与摘要，组合成结构化处置建议。
3. 若配置了 LLM（环境变量 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL），则把检索到的
   知识上下文交给大模型做自然语言润色（标准库 urllib 实现，无第三方依赖）；任何异常
   都会回退到检索生成，保证离线可用。
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.knowledge import KnowledgeItem
from app.services.dify_client import dify_configured, dify_retrieve

logger = logging.getLogger("assistant")

# ---------------------------------------------------------------------------
# [自定义模型] 免费大模型注册表
# 经由 NVIDIA NIM 免费层实测（chat/completions 返回 200）校验通过的模型。
# 默认内置以下 9 个；可通过环境变量 LLM_MODELS 以逗号分隔覆盖（例如追加
# 自有部署/第三方兼容端点模型）。激活模型在运行时可热切换，无需重启服务。
# ---------------------------------------------------------------------------
def _default_models() -> List[Dict[str, Any]]:
    return [
        {"id": "meta/llama-3.1-8b-instruct", "name": "Llama 3.1 8B", "vendor": "Meta", "note": "轻量·响应快·默认"},
        {"id": "nvidia/nemotron-mini-4b-instruct", "name": "Nemotron Mini 4B", "vendor": "NVIDIA", "note": "极小·低延迟"},
        {"id": "meta/llama-3.3-70b-instruct", "name": "Llama 3.3 70B", "vendor": "Meta", "note": "强推理·较慢"},
        {"id": "nvidia/llama-3.3-nemotron-super-49b-v1", "name": "Nemotron Super 49B", "vendor": "NVIDIA", "note": "均衡·强综合能力"},
        {"id": "openai/gpt-oss-20b", "name": "GPT-OSS 20B", "vendor": "OpenAI", "note": "开源·推理友好"},
        {"id": "openai/gpt-oss-120b", "name": "GPT-OSS 120B", "vendor": "OpenAI", "note": "强推理·较慢"},
        {"id": "z-ai/glm-5.2", "name": "GLM 5.2", "vendor": "Z.ai", "note": "中文能力强"},
        {"id": "minimaxai/minimax-m3", "name": "MiniMax M3", "vendor": "MiniMax", "note": "中文·长上下文"},
        {"id": "stepfun-ai/step-3.7-flash", "name": "Step 3.7 Flash", "vendor": "StepFun", "note": "中文·快速"},
    ]


def _load_models() -> List[Dict[str, Any]]:
    """模型注册表：环境变量 LLM_MODELS 覆盖默认；否则使用内置已验证免费模型。"""
    env = (os.getenv("LLM_MODELS") or "").strip()
    if env:
        ids = [m.strip() for m in env.split(",") if m.strip()]
        # 保留内置已知的名称/厂商信息，未知 id 仅给占位
        known = {m["id"]: m for m in _default_models()}
        out: List[Dict[str, Any]] = []
        for i in ids:
            out.append(known.get(i, {"id": i, "name": i.split("/")[-1], "vendor": i.split("/")[0], "note": "自定义"}))
        return out
    return _default_models()


# 模块级注册表（进程内）与运行时激活模型
_MODEL_REGISTRY: List[Dict[str, Any]] = _load_models()
_ACTIVE_MODEL: str = os.getenv("LLM_MODEL") or (_MODEL_REGISTRY[0]["id"] if _MODEL_REGISTRY else "")


def get_models() -> List[Dict[str, Any]]:
    """返回模型列表（含当前激活标记）。"""
    return [
        {**m, "selected": m["id"] == _ACTIVE_MODEL}
        for m in _MODEL_REGISTRY
    ]


def get_active_model() -> str:
    return _ACTIVE_MODEL


def set_active_model(model_id: str) -> bool:
    """切换运行时激活模型（热更新，无需重启）。返回是否成功。"""
    global _ACTIVE_MODEL
    if not any(m["id"] == model_id for m in _MODEL_REGISTRY):
        return False
    _ACTIVE_MODEL = model_id
    return True


def check_model_status(model: str) -> Dict[str, Any]:
    """探测指定模型的真实推理可用性（最小 chat 调用）。"""
    cfg = _llm_config()
    if not cfg["configured"]:
        return {"configured": False, "model": model, "reachable": False,
                "http_status": None, "latency": None, "model_available": None,
                "detail": "未配置 LLM_API_KEY，无法调用大模型。"}
    url = cfg["base_url"] + "/chat/completions"
    payload = {"model": model, "messages": [{"role": "user", "content": "ping"}],
               "max_tokens": 1, "temperature": 0}
    data = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=min(cfg["timeout"], 20)) as resp:
            return {"configured": True, "model": model, "reachable": True,
                    "http_status": resp.status, "latency": round(time.time() - t0, 3),
                    "model_available": True, "detail": "可用：Key 有效、网络可达、模型已授权。"}
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")[:300]
        except Exception:  # noqa: BLE001
            pass
        if e.code in (401, 403):
            detail = f"Key 失效或额度用尽（HTTP {e.code}）。"
        elif e.code == 404:
            detail = f"该模型对当前账号未授权/未部署（HTTP 404）：{body}"
        else:
            detail = f"推理调用返回 HTTP {e.code}：{body}"
        return {"configured": True, "model": model, "reachable": False,
                "http_status": e.code, "latency": round(time.time() - t0, 3),
                "model_available": False, "detail": detail}
    except Exception as e:  # noqa: BLE001
        return {"configured": True, "model": model, "reachable": False,
                "http_status": None, "latency": round(time.time() - t0, 3),
                "model_available": None, "detail": f"探测异常（{type(e).__name__}）：{e}。"}

_CJK = re.compile(r"[一-鿿]+")
_ASCII = re.compile(r"[a-z0-9]+")
_STOP = set("的吗了呢吧啊嘛呀哦呃?？!！，,。.、；;:：\"'（）()【】[]{}<>《》 \t\n\r　—-…·")


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    low = text.lower()
    tokens: List[str] = _ASCII.findall(low)
    for run in _CJK.findall(low):
        # 中文仅取二元组（单字噪声太大，如「机/电/发」在多数条目中出现）
        if len(run) == 1:
            continue
        for i in range(len(run) - 1):
            tokens.append(run[i : i + 2])
    return [t for t in tokens if t and t not in _STOP and len(t) <= 12]


def _item_blob(item: KnowledgeItem) -> str:
    parts = [
        item.code or "",
        item.title or "",
        item.category or "",
        item.summary or "",
        item.content or "",
        " ".join(item.tags or []),
        " ".join(item.related_domains or []),
        " ".join(item.related_categories or []),
        " ".join(item.related_metrics or []),
        " ".join(item.steps or []),
    ]
    return " ".join(filter(None, parts))


def _score_item(item: KnowledgeItem, q_tokens: set, ctx_tokens: set, ctx: Optional[Dict[str, Any]]):
    """返回 (score, strong)：strong 表示问题与条目「身份字段」(标题/标签/摘要/业务域) 的重叠数。"""
    identity = " ".join(
        filter(
            None,
            [
                item.title or "",
                item.code or "",
                item.category or "",
                " ".join(item.tags or []),
                item.summary or "",
                " ".join(item.related_domains or []),
                " ".join(item.related_categories or []),
                " ".join(item.related_metrics or []),
            ],
        )
    ).lower()
    full = _item_blob(item).lower()
    id_tokens = set(_tokenize(identity))
    full_tokens = set(_tokenize(full))
    if not full_tokens:
        return 0.0, 0
    strong = sum(1 for t in q_tokens if t in id_tokens)
    weak = sum(1 for t in q_tokens if t in full_tokens)
    score = strong * 6.0 + weak * 1.0

    # 业务域强匹配加成
    if ctx and ctx.get("domain"):
        doms = set(item.related_domains or [])
        doms.add((item.domain or "").lower())
        if ctx["domain"].lower() in doms:
            score += 4.0
    # 测点匹配加成
    if ctx and ctx.get("metric"):
        if ctx["metric"].lower() in set(m.lower() for m in (item.related_metrics or [])):
            score += 2.0
    return score, strong


def _retrieve(db: Session, question: str, ctx: Optional[Dict[str, Any]], top_k: int = 5):
    items = db.query(KnowledgeItem).all()
    q_tokens = set(_tokenize(question))
    ctx_text = " ".join(str(v) for v in (ctx or {}).values() if v)
    ctx_tokens = set(_tokenize(ctx_text))
    scored = []
    for it in items:
        s, strong = _score_item(it, q_tokens, ctx_tokens, ctx)
        if s > 0:
            scored.append((s, strong, it))
    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[:top_k], q_tokens


def _dedupe_steps(items: List[KnowledgeItem], limit: int = 8) -> List[str]:
    seen = set()
    out: List[str] = []
    for it in items:
        for step in it.steps or []:
            key = step.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(key)
            if len(out) >= limit:
                return out
    return out


def _dedupe_dify_steps(hits: List[Dict[str, Any]], limit: int = 8) -> List[str]:
    """从 Dify 召回片段的 content 中, 粗略抽取带有序号/换行分隔的处置步骤。"""
    if not hits:
        return []
    seen = set()
    out: List[str] = []
    for h in hits:
        content = (h.get("content") or "").replace("\r", "\n")
        for line in content.split("\n"):
            line = line.strip().lstrip("0123456789.、)） ").strip()
            if not line or len(line) < 4:
                continue
            if line in seen:
                continue
            seen.add(line)
            out.append(line)
            if len(out) >= limit:
                return out
    return out


def _grounded_answer(question: str, items: List[KnowledgeItem], no_match: bool) -> str:
    if no_match or not items:
        return (
            "当前知识库暂未检索到与您描述情况直接匹配的处置预案。建议初级运维人员：\n"
            "1) 首先确认现场人身安全与设备运行状态，切勿盲目操作电气设备或复位保护；\n"
            "2) 立即按《应急预案(EOP)》上报当班班长 / 对应专业工程师；\n"
            "3) 在「知识库 / 处置预案」中按系统（暖通 / 电力 / 消防 / 安防）检索相关 SOP 与应急条目；\n"
            "4) 补充更多现场信息（报警代码、设备编号、测点数值、发生时间）后可再次提问以获得更精准的预案。"
        )
    titles = "、".join(it.title for it in items[:3])
    lines = [
        f"您描述的现场情况已匹配到知识库中的 {len(items)} 条处置预案（含：{titles} 等）。",
        "请按以下优先级稳妥处置：",
    ]
    steps = _dedupe_steps(items)
    for i, step in enumerate(steps, 1):
        lines.append(f"{i}) {step}")
    lines.append(
        "安全提示：涉及电气倒闸、柴发并机、消防气体灭火、设备就地复位等操作时，"
        "务必执行双人确认并严格遵循对应 EOP；遇人身风险先撤离、再上报。"
    )
    return "\n".join(lines)


def _llm_config() -> Dict[str, Any]:
    """读取大模型接入配置，含可调控的超时/重试环境变量。"""
    api_key = os.getenv("LLM_API_KEY")
    try:
        timeout = int(os.getenv("LLM_TIMEOUT", "30"))
    except ValueError:
        timeout = 30
    try:
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "1"))
    except ValueError:
        max_retries = 1
    return {
        "configured": bool(api_key),
        "api_key": api_key,
        "base_url": os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        "model": _ACTIVE_MODEL or os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "timeout": timeout,
        "max_retries": max_retries,
    }


def _call_llm(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """调用大模型润色，返回结构化结果：

    {
        "text": Optional[str],          # 成功时的回答文本，失败为 None
        "error": Optional[str],         # 失败原因（HTTP 状态码 / 异常类型），成功为 None
        "http_status": Optional[int],   # 透传 HTTP 状态码（如 401/403/404），无则为 None
        "latency": float,               # 单次请求耗时（秒）
    }

    设计要点：失败不再被静默吞掉，而是带上明确原因（Key 失效 / 网络不通 / 模型下线 /
    超时），便于前端与运维一眼定位。鉴权失败、模型不存在为硬错误，立即返回不重试；
    网络抖动 / 超时按 LLM_MAX_RETRIES 进行有限重试。
    """
    cfg = _llm_config()
    if not cfg["api_key"]:
        return {"text": None, "error": "未配置 LLM_API_KEY，无法调用大模型", "http_status": None, "latency": 0.0}
    url = cfg["base_url"] + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    last_error = "未知错误"
    last_status: Optional[int] = None
    latency = 0.0
    for attempt in range(cfg["max_retries"] + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=cfg["timeout"]) as resp:
                latency = round(time.time() - t0, 3)
                j = json.loads(resp.read().decode("utf-8"))
                return {
                    "text": j["choices"][0]["message"]["content"].strip(),
                    "error": None,
                    "http_status": resp.status,
                    "latency": latency,
                }
        except urllib.error.HTTPError as e:
            latency = round(time.time() - t0, 3)
            body = ""
            try:
                body = e.read().decode("utf-8", "ignore")
            except Exception:  # noqa: BLE001
                pass
            last_error = f"HTTP {e.code} {e.reason}"
            last_status = e.code
            # 把 NIM 返回的错误体也带上，便于定位（如模型 id 不存在）
            if body:
                last_error += f" | {body[:300]}"
            # 鉴权失败 / 模型不存在属于硬错误，重试无意义
            if e.code in (401, 403, 404):
                break
        except (urllib.error.URLError, KeyError, IndexError, ValueError) as e:
            latency = round(time.time() - t0, 3)
            last_error = f"{type(e).__name__}: {e}"
        except Exception as e:  # noqa: BLE001
            latency = round(time.time() - t0, 3)
            last_error = f"{type(e).__name__}: {e}"
    logger.warning("LLM 调用失败（回退检索生成）: %s", last_error)
    return {"text": None, "error": last_error, "http_status": last_status, "latency": latency}


def check_llm_status(model: Optional[str] = None) -> Dict[str, Any]:
    """探测大模型「真实推理」可用性，供运维一键自查 (/ops/assistant/status)。

    直接发起一次最小化的 chat/completions 调用（max_tokens=1），因为 /models 目录
    里列出≠账号有权调用（NVIDIA NIM 常见 404 "Function not found for account"）。
    - HTTP 200：Key 有效、网络可达、且模型对账号已授权；
    - 401/403：Key 失效或额度用尽；
    - 404（Function not found for account）：该模型对当前账号未授权/未部署，需换模型 id；
    - 连接异常：网络不通/需配置代理/被防火墙拦截。
    """
    cfg = _llm_config()
    target_model = model or cfg["model"]
    if not cfg["configured"]:
        return {
            "configured": False,
            "base_url": cfg["base_url"],
            "model": target_model,
            "reachable": False,
            "http_status": None,
            "latency": None,
            "model_available": None,
            "detail": "未配置 LLM_API_KEY，助手仅使用本地知识库检索生成。",
        }
    url = cfg["base_url"] + "/chat/completions"
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 1,
        "temperature": 0,
    }
    data = json.dumps(payload).encode("utf-8")
    headers = {"Authorization": f"Bearer {cfg['api_key']}", "Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=min(cfg["timeout"], 20)) as resp:
            return {
                "configured": True,
                "base_url": cfg["base_url"],
                "model": target_model,
                "reachable": True,
                "http_status": resp.status,
                "latency": round(time.time() - t0, 3),
                "model_available": True,
                "detail": "大模型推理可用：Key 有效、网络可达、模型对账号已授权。",
            }
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "ignore")[:300]
        except Exception:  # noqa: BLE001
            pass
        if e.code in (401, 403):
            detail = f"Key 失效或额度用尽（HTTP {e.code}）。"
        elif e.code == 404:
            detail = f"该模型对当前账号未授权/未部署（HTTP 404）：{body}"
        else:
            detail = f"推理调用返回 HTTP {e.code}：{body}"
        return {
            "configured": True,
            "base_url": cfg["base_url"],
            "model": target_model,
            "reachable": False,
            "http_status": e.code,
            "latency": round(time.time() - t0, 3),
            "model_available": False,
            "detail": detail,
        }
    except urllib.error.URLError as e:
        return {
            "configured": True,
            "base_url": cfg["base_url"],
            "model": target_model,
            "reachable": False,
            "http_status": None,
            "latency": round(time.time() - t0, 3),
            "model_available": None,
            "detail": f"无法连接大模型端点（{type(e).__name__}）：网络不通/需配置代理/被防火墙拦截。",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "configured": True,
            "base_url": cfg["base_url"],
            "model": target_model,
            "reachable": False,
            "http_status": None,
            "latency": round(time.time() - t0, 3),
            "model_available": None,
            "detail": f"探测异常（{type(e).__name__}）：{e}。",
        }


def check_dify_status() -> Dict[str, Any]:
    """探测 Dify RAG 检索层可用性，供运维一键自查 (/ops/assistant/status)。

    直接发起一次 retrieve 调用（query="状态自检"）验证：Key 有效、知识库存在、网络可达。
    """
    if not dify_configured():
        return {
            "configured": False,
            "base_url": settings.DIFY_BASE_URL,
            "dataset_id": settings.DIFY_DATASET_ID,
            "reachable": False,
            "retrieved": 0,
            "detail": "未配置 DIFY_API_KEY/DIFY_DATASET_ID，助手走本地关键词检索兜底。",
        }
    try:
        recs = dify_retrieve("状态自检", top_k=1)
        return {
            "configured": True,
            "base_url": settings.DIFY_BASE_URL,
            "dataset_id": settings.DIFY_DATASET_ID,
            "reachable": True,
            "retrieved": len(recs),
            "detail": "Dify 知识库检索可用：Key 有效、知识库存在、网络可达。",
        }
    except Exception as e:  # noqa: BLE001
        return {
            "configured": True,
            "base_url": settings.DIFY_BASE_URL,
            "dataset_id": settings.DIFY_DATASET_ID,
            "reachable": False,
            "retrieved": 0,
            "detail": f"Dify 检索探测失败（{type(e).__name__}）：{e}。问答将回退本地关键词检索。",
        }


def _build_situation(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """[B6] 构建实时态势上下文: 活跃告警 + (若携带 device_id) 该设备实时测点。

    全部走内存热路径 (alarm_engine 活跃缓存 / external 内存最新值), 无额外 DB 开销。
    """
    situation: Dict[str, Any] = {
        "active_alarm_count": 0,
        "active_alarms": [],
        "device_metrics": None,
    }
    # 活跃告警 (收敛去重后的实时活跃告警)
    try:
        from app.services import alarm_engine

        alarms = alarm_engine.get_active_alarms(limit=50)
        situation["active_alarm_count"] = len(alarms)
        situation["active_alarms"] = [
            {
                "device_id": a.get("device_id"),
                "metric": a.get("metric_name"),
                "value": a.get("value"),
                "level": a.get("level"),
                "ts": a.get("ts"),
                "rule_id": a.get("rule_id"),
            }
            for a in alarms[:20]
        ]
    except Exception:  # noqa: BLE001
        pass
    # 设备实时测点 (前端携带 device_id 时)
    dev = ctx.get("device_id") if ctx else None
    if dev:
        try:
            from app.crud import external as external_crud

            latest = external_crud.latest_metrics(dev)
            if latest:
                situation["device_metrics"] = [
                    {
                        "metric": m,
                        "value": (v.get("value") if isinstance(v, dict) else v),
                        "unit": (v.get("unit") if isinstance(v, dict) else ""),
                        "ts": (v.get("ts") if isinstance(v, dict) else None),
                    }
                    for m, v in list(latest.items())[:20]
                ]
        except Exception:  # noqa: BLE001
            pass
    return situation


def _situation_to_text(situation: Dict[str, Any]) -> str:
    lines: List[str] = []
    for a in situation.get("active_alarms", []):
        if a.get("device_id"):
            lines.append(
                f"{a.get('level', 'warn')}级告警 设备{a['device_id']} "
                f"测点{a.get('metric')}={a.get('value')}"
            )
    for m in situation.get("device_metrics", []) or []:
        lines.append(f"实时测点 {m.get('metric')}={m.get('value')}{m.get('unit') or ''}")
    return " ".join(lines)


def answer(db: Session, question: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    question = (question or "").strip()
    ctx = context or {}
    # [B6] 注入实时态势上下文 (活跃告警 + 设备实时测点)
    situation = _build_situation(ctx)
    situation_text = _situation_to_text(situation)
    # 将态势文本并入检索上下文 (参与弱匹配打分), 提升与当前告警/测点相关预案的命中率
    ctx_for_retrieval = {**ctx, "_situation": situation_text} if situation_text else ctx
    if not question:
        return {
            "question": question,
            "answer": "请描述您遇到的现场情况或告警（例如：冷机出现喘振声如何处理），AI 助手将基于知识库给出处置建议。",
            "steps": [],
            "refs": [],
            "model": "rag-grounded",
            "grounded": True,
            "noMatch": False,
            "situation": situation,
        }

    # ---------- [Dify RAG] 检索优先走 Dify 向量召回, 失败/未命中回退本地关键词打分 ----------
    dify_hits: List[Dict[str, Any]] = []
    dify_error: Optional[str] = None
    if dify_configured():
        try:
            raw = dify_retrieve(question, top_k=settings.DIFY_RETRIEVE_TOP_K)
            # 按归一化分数阈值过滤, 避免低质召回污染上下文
            dify_hits = [h for h in raw if h.get("score", 0) >= 0.1]
            logger.info("Dify 检索命中 %d 条有效片段", len(dify_hits))
        except Exception as e:  # noqa: BLE001
            dify_error = f"{type(e).__name__}: {e}"
            logger.warning("Dify 检索失败, 回退本地关键词打分: %s", dify_error)

    scored, _ = _retrieve(db, question, ctx_for_retrieval)
    # 放宽命中门槛（A+B 修复）：身份字段(strong)命中始终纳入；
    # 仅正文(weak)命中时要求 score>=2.0（≥2 个二元词重叠），在抑制噪声的同时
    # 避免「冷机喘振怎么办」这类正文语义提问全部走兜底。scored 已按 (score,strong) 降序，
    # 强匹配条目仍自然排在弱匹配之前。
    items = [it for s, strong, it in scored if strong > 0 or s >= 2.0]

    refs = [{"code": it.code, "title": it.title, "type": it.type} for it in items]
    # [Dify RAG] 把 Dify 召回片段来源一并标注, 便于前端展示"知识来源"
    if dify_hits:
        for h in dify_hits:
            refs.append(
                {
                    "code": h.get("doc_id") or "dify",
                    "title": h.get("title") or "Dify 知识片段",
                    "type": "dify",
                    "score": round(h.get("score", 0.0), 3),
                }
            )
    # [Dify RAG] Dify 片段也参与去重步骤提取 (若有结构化步骤文本)
    dify_steps = _dedupe_dify_steps(dify_hits)
    steps = _dedupe_steps(items)
    if not steps:
        steps = dify_steps
    no_match = len(items) == 0 and len(dify_hits) == 0
    grounded_text = _grounded_answer(question, items, no_match)

    cfg = _llm_config()
    model = "rag-grounded"
    final_answer = grounded_text
    grounded = True
    llm_error: Optional[str] = None

    # 若配置了大模型，将检索到的知识（本地知识库 + Dify 召回）+ 实时态势作为上下文交给 LLM 润色
    if (items or dify_hits) and cfg["configured"]:
        local_ctx = "\n\n".join(
            f"[{it.code}] {it.title}（类型:{it.type}）\n摘要:{it.summary}\n处置步骤:"
            + "；".join(it.steps or [])
            + f"\n详情:{(it.content or '')[:4000]}"
            for it in items
        )
        dify_ctx = "\n\n".join(
            f"[Dify 知识片段] {h.get('title') or ''}（相关度:{round(h.get('score',0),3)}）\n"
            f"{h.get('content') or ''}"
            for h in dify_hits
        )
        kb_parts = []
        if local_ctx:
            kb_parts.append("【本地知识库】\n" + local_ctx)
        if dify_ctx:
            kb_parts.append("【Dify 知识库召回】\n" + dify_ctx)
        kb_ctx = "\n\n".join(kb_parts)
        system = (
            "你是数据中心运维辅助助手，面向初级运维人员。只能依据给定的知识库条目与实时态势作答，"
            "给出清晰、可执行的处置步骤，并强调安全与上报要求；不得编造知识库以外的步骤。"
        )
        situation_block = situation_text or "（当前无活跃告警与实时测点上下文）"
        user = (
            f"现场情况：{question}\n\n"
            f"当前实时态势：\n{situation_block}\n\n"
            f"可参考知识库：\n{kb_ctx}\n\n请给出处置建议。"
        )
        result = _call_llm(system, user)
        if result["text"]:
            final_answer = result["text"]
            model = "llm:" + cfg["model"]
            grounded = False
        else:
            # 大模型调用失败，已回退本地知识库；把原因透出，避免"静默不可用"
            llm_error = result["error"]

    return {
        "question": question,
        "answer": final_answer,
        "steps": steps,
        "refs": refs,
        "model": model,
        "grounded": grounded,
        "noMatch": no_match,
        "situation": situation,
        "llm_error": llm_error,
        "dify": {
            "enabled": dify_configured(),
            "retrieved": len(dify_hits),
            "error": dify_error,
        },
    }
