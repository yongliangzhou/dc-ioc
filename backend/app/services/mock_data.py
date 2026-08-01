# TODO: 旧版占位，待v2全量切换后删除
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
