"""上架模拟器 (capacity_whatif) 纯函数推演测试。"""
import pytest

from app.services.capacity_whatif import simulate

BASE = {
    "_source": "generated",
    "dims": [
        {"id": "机柜空间", "used": 1200, "total": 3600, "unit": "U"},
        {"id": "电力容量", "used": 12.5, "total": 36.0, "unit": "MW"},
        {"id": "制冷容量", "used": 10.0, "total": 40.0, "unit": "MW"},
        {"id": "承重容量", "used": 33.3, "total": 100.0, "unit": "%"},
        {"id": "网络端口", "used": 2400, "total": 57600, "unit": "口"},
    ],
}


def _dim(result, dim_id):
    return next(d for d in result["dims"] if d["id"] == dim_id)


def test_power_delta_is_kw_per_rack():
    r = simulate(BASE, cabinets=50, kw_per_cabinet=12, months_horizon=24)
    p = _dim(r, "电力容量")
    assert p["addedByRacks"] == 0.6            # 50 × 12kW = 600kW = 0.6MW
    assert p["usedAfter"] == pytest.approx(13.1, abs=0.01)
    # 制冷跟随 IT 负载 ×1.25
    c = _dim(r, "制冷容量")
    assert c["addedByRacks"] == pytest.approx(0.75, abs=0.001)


def test_space_delta_42u_and_bottleneck():
    r = simulate(BASE, cabinets=50, kw_per_cabinet=12, months_horizon=24)
    s = _dim(r, "机柜空间")
    assert s["addedByRacks"] == 2100           # 50 × 42U
    assert s["pctAfter"] == pytest.approx(91.7, abs=0.1)
    # 空间余量最小 → 瓶颈
    assert r["bottleneck"] == "机柜空间"
    assert s["reach85Month"] == "now"          # 91.7% 已超 85% 预警线
    assert s["reach100Month"] and s["reach100Month"] != "now"


def test_reach_month_null_within_horizon():
    # 电力仅 36.4% 占用, 24 个月 (年增 7%) 到不了 85%
    r = simulate(BASE, cabinets=50, kw_per_cabinet=12, months_horizon=24)
    assert _dim(r, "电力容量")["reach85Month"] is None
    assert _dim(r, "电力容量")["reach100Month"] is None


def test_reach_month_now_when_already_over():
    # 电力接近满容: 35.5/36 = 98.6%, 再上 50 柜 ×12kW = +0.6 → 100.3% 已超
    base = {"_source": "generated", "dims": [
        {"id": "电力容量", "used": 35.5, "total": 36.0, "unit": "MW"},
        {"id": "机柜空间", "used": 100, "total": 3600, "unit": "U"},
    ]}
    r = simulate(base, cabinets=50, kw_per_cabinet=12, months_horizon=24)
    p = _dim(r, "电力容量")
    assert p["pctAfter"] > 100
    assert p["reach100Month"] == "now"
    assert p["headroomPercent"] == 0.0
    assert r["bottleneck"] == "电力容量"
    assert any("100%" in s or "超限" in s for s in r["suggestions"])


def test_growth_extrapolation_reaches_warn():
    # 电力 29/36 = 80.6%, +0.6 → 82.2%, 年增 7% → 约 6 个月触及 85%
    base = {"_source": "real", "dims": [
        {"id": "电力容量", "used": 29.0, "total": 36.0, "unit": "MW"},
    ]}
    r = simulate(base, cabinets=50, kw_per_cabinet=12, months_horizon=36)
    p = _dim(r, "电力容量")
    assert p["reach85Month"] not in (None, "now")
    # 月份字符串可解析且晚于当前月
    assert len(p["reach85Month"]) == 7 and p["reach85Month"][4] == "-"


def test_suggestions_present_and_high_density_hint():
    r = simulate(BASE, cabinets=50, kw_per_cabinet=25, months_horizon=24)
    assert r["suggestions"]
    assert any("25" in s for s in r["suggestions"])  # 高密度提示 (>20kW)


def test_unknown_dim_gets_zero_delta_and_default_growth():
    base = {"_source": "generated", "dims": [{"id": "未知维度", "used": 10, "total": 100, "unit": "x"}]}
    r = simulate(base, cabinets=100, kw_per_cabinet=10, months_horizon=12)
    d = _dim(r, "未知维度")
    assert d["addedByRacks"] == 0.0 and d["usedAfter"] == 10.0
    # 默认年增 5%: 12 个月到不了 85%
    assert d["reach100Month"] is None


def test_empty_dims():
    r = simulate({"dims": []}, cabinets=10, kw_per_cabinet=8, months_horizon=12)
    assert r["dims"] == [] and r["bottleneck"] == "" and r["suggestions"]


def test_input_clamped_by_endpoint_bounds_are_service_agnostic():
    # 服务层不截断 (截断在端点层), 但对极端值也应稳定
    r = simulate(BASE, cabinets=0, kw_per_cabinet=0, months_horizon=6)
    assert _dim(r, "电力容量")["usedAfter"] == pytest.approx(12.5, abs=0.01)
