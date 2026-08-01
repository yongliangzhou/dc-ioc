#!/usr/bin/env python3
"""外部采集器对接示例 (标准数据契约 v1)。

演示如何把一个「自有设备」按 API_CONTRACT.md 的契约注册到 DC-IOC 平台,
并持续上报实时测点。可直接运行, 用于验证 external 域链路 (设备注册 → 测点上报 → WS 实时推送)。

前置:
  - 后端已启动 (默认 http://127.0.0.1:8000)
  - 若生产环境已配置 EXTERNAL_COLLECTOR_TOKEN, 需通过 --token 传入
  - 如需鉴权写端点, 本示例仅演示设备注册/上报 (无需用户 JWT)
  - 注: 在 Docker Desktop (Windows) 上从宿主机直接 POST 带 body 的请求偶尔会被 NAT 丢弃
    (GET 正常)。若遇连接中断, 请在后端容器内执行, 或经前端容器 (compose 网络) 调用。

用法:
  python examples/collector_demo.py --base-url http://127.0.0.1:8000 --token <collector_token> --interval 5
"""
from __future__ import annotations

import argparse
import random
import time
from datetime import datetime, timezone

try:
    import requests
except ImportError:  # pragma: no cover
    raise SystemExit("需要 requests: pip install requests")


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def register(base_url: str, token: str | None, device: dict) -> bool:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Collector-Token"] = token
    r = requests.post(f"{base_url}/api/external/device/register", json=device, headers=headers, timeout=10)
    print(f"[register] {device['device_id']} -> {r.status_code} {r.text[:120]}")
    return r.status_code == 200


def upload(base_url: str, token: str | None, device_id: str, metrics: list[dict]) -> bool:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["X-Collector-Token"] = token
    payload = [dict(device_id=device_id, timestamp=iso_now(), **m) for m in metrics]
    r = requests.post(f"{base_url}/api/external/metrics/upload", json=payload, headers=headers, timeout=10)
    print(f"[upload]   {device_id} points={len(payload)} -> {r.status_code} {r.text[:120]}")
    return r.status_code == 200


def drift(prev: float, lo: float, hi: float, step: float = 0.4) -> float:
    v = prev + random.uniform(-step, step)
    return round(max(lo, min(hi, v)), 2)


def main() -> None:
    ap = argparse.ArgumentParser(description="DC-IOC 外部采集器对接示例")
    ap.add_argument("--base-url", default="http://127.0.0.1:8000")
    ap.add_argument("--token", default=None, help="EXTERNAL_COLLECTOR_TOKEN (生产环境必填)")
    ap.add_argument("--interval", type=float, default=5.0, help="上报间隔(秒)")
    ap.add_argument("--rounds", type=int, default=0, help="上报轮数(0=无限)")
    args = ap.parse_args()

    # 1) 注册一台自有冷水机组 (类别需与后端物模型配置中的 category 对齐)
    #    契约硬约束必填: device_id / ip / sn / model
    device = {
        "device_id": "DEMO-CHILLER-01",
        "name": "示例冷水机组A",
        "category": "chiller",
        "domain": "hvac_source",
        "protocol": "modbus",
        "manufacturer": "DemoVendor",
        "model": "CDH-500",
        "ip": "10.0.0.99",
        "sn": "SN-DEMO-CHILLER-01",
        "location": "机房一层冷站",
        "tags": ["demo", "modbus"],
    }
    register(args.base_url, args.token, device)

    # 2) 持续上报实时测点 (与 mock_collector 的 chiller 测点对齐, 便于复用告警规则)
    state = {"supply_temp": 9.5, "return_temp": 15.5, "power_kw": 470.0,
             "flow_rate": 280.0, "load_ratio": 65.0, "cop_est": 6.2}
    round_n = 0
    try:
        while args.rounds == 0 or round_n < args.rounds:
            round_n += 1
            state["supply_temp"] = drift(state["supply_temp"], 7.0, 12.0)
            state["return_temp"] = drift(state["return_temp"], 13.0, 19.0)
            state["power_kw"] = drift(state["power_kw"], 380.0, 560.0, 4.0)
            state["flow_rate"] = drift(state["flow_rate"], 240.0, 320.0, 3.0)
            state["load_ratio"] = drift(state["load_ratio"], 40.0, 90.0, 2.0)
            state["cop_est"] = round(state["power_kw"] / max(state["power_kw"] * 0.16, 1.0), 2)
            metrics = [
                {"metric_name": "supply_temp", "value": state["supply_temp"], "unit": "℃", "quality": "good"},
                {"metric_name": "return_temp", "value": state["return_temp"], "unit": "℃", "quality": "good"},
                {"metric_name": "power_kw", "value": state["power_kw"], "unit": "kW", "quality": "good"},
                {"metric_name": "flow_rate", "value": state["flow_rate"], "unit": "m3/h", "quality": "good"},
                {"metric_name": "load_ratio", "value": state["load_ratio"], "unit": "%", "quality": "good"},
                {"metric_name": "cop_est", "value": state["cop_est"], "unit": "", "quality": "good"},
                {"metric_name": "run_state", "value": "运行", "quality": "good"},
            ]
            upload(args.base_url, args.token, device["device_id"], metrics)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n[stop] 已停止示例采集器")


if __name__ == "__main__":
    main()
