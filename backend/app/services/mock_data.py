# TODO: 旧版演示数据占位。当前仍被 crud/server.py、endpoints/cabinets.py、
# endpoints/server.py 用作离线兜底 (U 位识别 / 机柜遥测)；待这三处全部切换
# 真实数据后即可删除本文件。
"""Mock 数据生成服务: 供前端独立开发联调。

说明: 使用以对象 id 为种子的随机数, 保证同一机柜多次请求曲线稳定。
"""
import math
import random
from datetime import datetime, timedelta, timezone

from app.schemas.dashboard import AlarmCount, CabinetItem, CabinetMetrics, DashboardOverview, MetricPoint
from app.services import dc_ioc_data

# ---------- 机柜基础库 (模拟 3 个机房 x 每机房若干机柜) ----------
ROOMS = ["R01", "R02", "R03"]
ROWS = ["A", "B"]


def _gen_cabinets() -> list[CabinetItem]:
    cabinets: list[CabinetItem] = []
    cid = 1
    for room in ROOMS:
        for row in ROWS:
            for n in range(1, 9):  # 每列 8 个 -> 3*2*8=48 台
                rng = random.Random(cid)
                u_used = rng.randint(20, 42)
                cabinets.append(CabinetItem(
                    id=cid, idc_id=1,
                    code=f"{room}-{row}{n:02d}",
                    room=room, row=row,
                    u_total=42, u_used=u_used,
                    rated_power_kw=10.0,
                    current_power_kw=round(rng.uniform(2, 9.5), 2),
                    status=rng.choice(["在用", "在用", "在用", "预留"]),
                ))
                cid += 1
    return cabinets


CABINETS: list[CabinetItem] = _gen_cabinets()


def dashboard_overview() -> DashboardOverview:
    k = dc_ioc_data.kpi()
    total = len(CABINETS) * 60          # 模拟: 机柜*服务器 + 其他设备
    online = int(total * 0.993)
    return DashboardOverview(
        total_devices=total,
        online_devices=online,
        online_rate=round(online / total * 100, 2),
        today_alarms=sum(k["alarms"].values()),
        pue=k["pue"],
        wue=k["wue"],
        it_load_mw=k["itLoad"],
        total_load_mw=k["totalLoad"],
        cool_load_mw=k["coolLoad"],
        availability=k["availability"],
        free_cool_hours=k["freeCoolHours"],
        alarms=AlarmCount(
            crit=k["alarms"]["crit"], warn=k["alarms"]["warn"], info=k["alarms"]["info"]
        ),
    )


def list_cabinets(page: int, size: int, room: str | None):
    data = [c for c in CABINETS if (room is None or c.room == room)]
    total = len(data)
    start = (page - 1) * size
    return total, data[start:start + size]


def _series(rng: random.Random, base: float, amp: float, n: int, now: datetime, step: timedelta, f: int = 2) -> list[MetricPoint]:
    """带轻微趋势的平滑随机游走序列。"""
    pts = []
    v = base
    for i in range(n):
        drift = math.sin(i / n * math.pi * 2) * amp * 0.4
        v = base + drift + (rng.random() - 0.5) * amp
        pts.append(MetricPoint(ts=(now - step * (n - 1 - i)).isoformat(), value=round(v, f)))
    return pts


def cabinet_metrics(cabinet_id: int, minutes: int = 60, step_sec: int = 60) -> CabinetMetrics:
    cab = next((c for c in CABINETS if c.id == cabinet_id), None)
    if cab is None:
        return None
    rng = random.Random(cabinet_id)
    now = datetime.now(timezone.utc)
    n = int(minutes * 60 / step_sec)
    step = timedelta(seconds=step_sec)
    return CabinetMetrics(
        cabinet_id=cabinet_id,
        code=cab.code,
        range_minutes=minutes,
        temperature=_series(rng, 24.5, 1.6, n, now, step),
        humidity=_series(rng, 50.0, 5.0, n, now, step, f=1),
        power_kw=_series(rng, cab.current_power_kw, 0.8, n, now, step),
    )


# ---------- U 位识别演示数据 ----------
# RFID / 资产标签实测来源 (现场实时 U 位)。
_U_BRANDS = ["Dell", "HPE", "Inspur", "Huawei", "Lenovo"]
_U_BUSINESS = ["核心交易", "大数据分析", "AI 训练", "中间件", "存储集群", "网关"]


def servers_for_cabinet(cabinet_id: int, u_total: int = 42) -> list[dict]:
    """模拟 RFID / 资产标签现场实测的机柜内服务器 U 位分布。

    返回 dict 列表, 字段对齐 server ORM (snake_case), 用于前端 U 位识别。
    刻意在个别机柜制造与台账的偏差, 以演示冲突检测。
    """
    rng = random.Random(cabinet_id * 7 + 3)
    servers: list[dict] = []
    sid = cabinet_id * 100
    u = 1
    # 预留 1~2U 走线空间, 从底部往上铺
    u = rng.randint(1, 2)
    n_servers = rng.randint(6, 11)
    drift = (cabinet_id % 5) == 0  # 每 5 个机柜制造一处 U 位漂移冲突
    drifted = False
    for i in range(n_servers):
        if u > u_total - 1:
            break
        height = rng.choice([1, 1, 2, 2, 4])
        if u + height - 1 > u_total:
            height = u_total - u + 1
        if height < 1:
            break
        u_start = u
        u_end = u + height - 1
        # 漂移: 把某台设备整体下移 1U, 制造与台账不符
        if drift and not drifted and i == max(2, n_servers // 2):
            u_start += 1
            u_end += 1
            drifted = True
        sid += 1
        servers.append(
            dict(
                id=sid,
                cabinet_id=cabinet_id,
                asset_no=f"AS{cabinet_id:03d}-{sid:04d}",
                hostname=f"node-{cabinet_id:03d}-{i+1:02d}",
                ip=f"10.{(cabinet_id // 250) % 250}.{cabinet_id % 250}.{i+1}",
                brand=rng.choice(_U_BRANDS),
                model=f"R{rng.randint(4, 9)}40",
                u_start=u_start,
                u_end=u_end,
                cpu_model="Xeon Gold 6348",
                cpu_count=rng.choice([2, 4]),
                cpu_cores=rng.choice([48, 64, 96]),
                memory_gb=rng.choice([256, 512, 1024]),
                disk_desc=f"{rng.randint(2, 8)}x{rng.choice([960, 1920])}GB SSD",
                business=rng.choice(_U_BUSINESS),
                status=rng.choice(["在线", "在线", "在线", "离线"]),
                source="rfid",
            )
        )
        u = u_end + 1 + rng.choice([0, 0, 1])  # 偶尔留 1U 空隙
    return servers


def ledger_for_cabinet(cabinet_id: int, u_total: int = 42) -> list[dict]:
    """模拟电子工单 / 资产台账的规划 U 位 (基准真值)。

    大部分与 RFID 实测一致, 仅个别机柜存在规划与现场偏差 (演示冲突检测)。
    """
    rfid = servers_for_cabinet(cabinet_id, u_total)
    ledger: list[dict] = []
    for s in rfid:
        entry = dict(s)
        entry["source"] = "ledger"
        ledger.append(entry)
    # 第 5 个机柜: 台账比现场多规划一台, 制造台账不符
    if (cabinet_id % 5) == 0 and ledger:
        first = ledger[0]
        ledger.append(
            dict(
                id=cabinet_id * 1000 + 1,
                cabinet_id=cabinet_id,
                asset_no=f"AS{cabinet_id:03d}-L000",
                hostname=f"node-{cabinet_id:03d}-L",
                ip="10.0.0.0",
                brand="Lenovo",
                model="SR650",
                u_start=first["u_start"],
                u_end=first["u_start"],  # 台账认为此处只有 1U, 现场实测 2U
                cpu_model="Xeon Silver 4310",
                cpu_count=2,
                cpu_cores=24,
                memory_gb=256,
                disk_desc="2x960GB SSD",
                business="网关",
                status="在线",
                source="ledger",
            )
        )
    return ledger
