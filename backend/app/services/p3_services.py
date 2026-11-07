"""阶段三纯业务服务 (无框架依赖, 可直接单测)。

- IPAM: 子网容量/利用率/下一可用地址
- 自动发现: 零依赖 asyncio TCP 探测 (私网段、≤/24、并发上限、超时)
- 资产商务: 保修到期筛选、盘点差异报告
- 自定义字段: 按定义做类型/必填/枚举校验
"""
from __future__ import annotations

import asyncio
import ipaddress
import itertools
from datetime import date, datetime, timezone

MAX_HOSTS = 256
MAX_ENUM_HOSTS = 4096  # 超大 IPv6 前缀不全量展开, 防止内存爆炸
PROBE_TIMEOUT = 0.5


class ValidationError(ValueError):
    """业务校验失败 (端点转 400/422)。"""


def now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


# ------------------------------------------------------------------ #
# IPAM
# ------------------------------------------------------------------ #
def _usable_addresses(net):
    """IPv4 排除网络号/广播地址; IPv6 无广播, 全部地址可用 (惰性迭代)。"""
    if net.version == 6:
        return iter(net)
    if net.num_addresses > 2:
        return net.hosts()
    return iter([net.network_address])


def _usable_count(net) -> int:
    if net.version == 6:
        return net.num_addresses
    return net.num_addresses - 2 if net.num_addresses > 2 else net.num_addresses


def _parse_used(used: list[str]) -> set:
    """宽容解析 used 列表 (可含 /掩码); 非法项忽略而不是抛异常。"""
    out = set()
    for raw in used or []:
        if not raw:
            continue
        try:
            out.add(ipaddress.ip_address(str(raw).split("/")[0]))
        except ValueError:
            continue
    return out


def _is_usable(net, ip) -> bool:
    if ip.version != net.version or ip not in net:
        return False
    if net.version == 6 or net.num_addresses <= 2:
        return True
    return ip != net.network_address and ip != net.broadcast_address


def subnet_stats(cidr: str, used: list[str]) -> dict:
    """计算子网总数/已用/可用/利用率。

    只按地址数量计算 total, 不全量展开地址 (IPv6 /64 也不会 OOM)。
    """
    net = ipaddress.ip_network(cidr, strict=True)
    total = _usable_count(net)
    used_count = sum(1 for ip in _parse_used(used) if _is_usable(net, ip))
    return {
        "cidr": str(net),
        "total": total,
        "used": used_count,
        "available": max(0, total - used_count),
        "utilization_pct": round(used_count * 100 / total, 2) if total else 0.0,
    }


def next_available(cidr: str, used: list[str]) -> str | None:
    net = ipaddress.ip_network(cidr, strict=True)
    used_set = _parse_used(used)
    for ip in itertools.islice(_usable_addresses(net), MAX_ENUM_HOSTS):
        if ip not in used_set:
            return str(ip)
    return None


# ------------------------------------------------------------------ #
# 自动发现
# ------------------------------------------------------------------ #
def validate_scan_cidr(cidr: str) -> ipaddress._BaseNetwork:
    """安全边界: 只允许 RFC1918 私网段, 最大 /24 (256 地址)。"""
    try:
        net = ipaddress.ip_network(cidr, strict=True)
    except ValueError as exc:
        raise ValidationError(f"非法 CIDR: {cidr}") from exc
    if not net.is_private:
        raise ValidationError("仅允许 RFC1918 私网段扫描")
    if net.num_addresses > MAX_HOSTS:
        raise ValidationError(f"网段过大, 上限 /24 ({MAX_HOSTS} 个地址)")
    return net


async def _probe(ip: str, port: int, sem: asyncio.Semaphore) -> bool:
    async with sem:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=PROBE_TIMEOUT
            )
            writer.close()
            try:
                await writer.wait_closed()
            except (OSError, ConnectionError):  # noqa: BLE001 - 关闭 writer 的对端断连可忽略
                pass
            return True
        except (OSError, asyncio.TimeoutError, ConnectionError):
            return False


async def scan_subnet(cidr: str, ports: list[int], concurrency: int = 50) -> list[dict]:
    """并发 TCP 端口探测; 只返回至少有一个开放端口的主机 (待确认区候选)。"""
    net = validate_scan_cidr(cidr)
    sem = asyncio.Semaphore(min(concurrency, 50))
    hosts = [str(h) for h in net.hosts()] if net.num_addresses > 2 else [str(net.network_address)]
    tasks = [(ip, port, asyncio.create_task(_probe(ip, port, sem))) for ip in hosts for port in ports]
    results = await asyncio.gather(*(t for _, _, t in tasks), return_exceptions=True)
    open_map: dict[str, list[int]] = {}
    for (ip, port, _), ok in zip(tasks, results, strict=False):
        if ok is True:
            open_map.setdefault(ip, []).append(port)
    return [
        {"ip": ip, "hostname": "", "mac": "", "open_ports": sorted(ports)}
        for ip, ports in sorted(open_map.items())
    ]


# ------------------------------------------------------------------ #
# 采购 / 盘点
# ------------------------------------------------------------------ #
def expiring_orders(rows: list[dict], days: int = 30) -> list[dict]:
    """筛选 N 天内保修到期 (或已过期) 的合同, 按到期日升序。"""
    today = date.today()
    out = []
    for row in rows:
        raw = (row.get("warranty_until") or "").strip()
        if not raw:
            continue
        try:
            until = date.fromisoformat(raw[:10])
        except ValueError:
            continue
        remain = (until - today).days
        if remain <= days:
            out.append({**row, "days_remaining": remain, "expired": remain < 0})
    return sorted(out, key=lambda r: r["days_remaining"])


def stocktake_report(items: list[dict], expected_cis: list[str]) -> dict:
    """实盘差异报告: 已核对 / 缺失 / 多出 / 覆盖率。"""
    marked = {(i["asset_ci"], i["result"]) for i in items}
    matched = {ci for ci, result in marked if result == "matched"}
    missing = [ci for ci in expected_cis if ci not in matched]
    unexpected = sorted(ci for ci, result in marked if result == "unexpected")
    total = len(expected_cis)
    return {
        "expected_total": total,
        "marked_total": len(items),
        "matched": len(matched),
        "missing": sorted(missing),
        "unexpected": unexpected,
        "coverage_pct": round(len(matched) * 100 / total, 2) if total else 0.0,
    }


# ------------------------------------------------------------------ #
# 自定义字段
# ------------------------------------------------------------------ #
def validate_custom_values(defs: list[dict], values: dict) -> dict:
    """按定义校验值: 未知 key 拒绝, 类型/必填/枚举逐项检查, 返回归一化后的值。"""
    by_key = {d["key"]: d for d in defs}
    unknown = sorted(set(values) - set(by_key))
    if unknown:
        raise ValidationError(f"未定义的自定义字段: {', '.join(unknown)}")
    out: dict = {}
    for key, definition in by_key.items():
        raw = values.get(key)
        if raw in (None, ""):
            if definition.get("required"):
                raise ValidationError(f"必填字段缺失: {key}")
            continue
        ftype = definition.get("type")
        if ftype == "number":
            try:
                out[key] = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValidationError(f"字段 {key} 必须是数字") from exc
        elif ftype == "date":
            try:
                date.fromisoformat(str(raw)[:10])
            except ValueError as exc:
                raise ValidationError(f"字段 {key} 必须是 YYYY-MM-DD 日期") from exc
            out[key] = str(raw)[:10]
        elif ftype == "select":
            options = [str(o) for o in (definition.get("options") or [])]
            if str(raw) not in options:
                raise ValidationError(f"字段 {key} 取值不在可选项内")
            out[key] = str(raw)
        else:
            out[key] = str(raw)
    return out
