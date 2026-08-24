"""Phase 2 核心模块单元测试 (无需数据库)"""


# ---- 安全模块 ----
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


def test_password():
    pw = "admin123"
    hashed = hash_password(pw)
    assert verify_password(pw, hashed), "verify_password should return True"
    assert not verify_password("wrong", hashed), "wrong password should fail"
    print("[PASS] test_password")


def test_access_token():
    token = create_access_token(subject="admin")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert "exp" in payload
    assert "iat" in payload
    assert payload["type"] == "access"
    print(f"[PASS] test_access_token (sub={payload['sub']})")


def test_refresh_token():
    token = create_refresh_token(subject="admin")
    payload = decode_token(token)
    assert payload is not None
    assert payload["type"] == "refresh"
    print("[PASS] test_refresh_token")


def test_token_types():
    at = create_access_token("user1")
    rt = create_refresh_token("user1")
    ap = decode_token(at)
    rp = decode_token(rt)
    assert ap["type"] == "access"
    assert rp["type"] == "refresh"
    print("[PASS] test_token_types")


def test_invalid_token():
    assert decode_token("garbage.token.here") is None
    assert decode_token("") is None
    print("[PASS] test_invalid_token")


# ---- 告警引擎 ----
from app.services import alarm_engine


def test_alarm_evaluate_normal():
    """正常值不触发告警"""
    alarm_engine.clear_all()
    result = alarm_engine.evaluate("dev-1", "chiller", "supply_temp", 8.0, "degC", quality="good")
    assert result is None, f"Expected None, got {result}"
    print("[PASS] test_alarm_evaluate_normal")


def test_alarm_evaluate_high():
    """越上限触发告警 (supply_temp warn.hi=15)"""
    alarm_engine.clear_all()
    result = alarm_engine.evaluate("dev-1", "chiller", "supply_temp", 16.0, "degC", quality="good")
    assert result is not None
    assert "level" in result
    assert result["level"] in ("warn", "crit")
    assert result["device_id"] == "dev-1"
    print(f"[PASS] test_alarm_evaluate_high (level={result['level']})")


def test_alarm_evaluate_low():
    """越下限触发告警 (supply_temp warn.lo=5)"""
    alarm_engine.clear_all()
    result = alarm_engine.evaluate("dev-1", "chiller", "supply_temp", 2.0, "degC", quality="good")
    assert result is not None
    assert result["level"] in ("warn", "crit")
    print(f"[PASS] test_alarm_evaluate_low (level={result['level']})")


def test_alarm_convergence():
    """收敛: 5分钟窗口内同规则重复触发被抑制为 None"""
    alarm_engine.clear_all()
    r1 = alarm_engine.evaluate("dev-2", "ups", "load_percent", 90.0, "%", quality="good")
    r2 = alarm_engine.evaluate("dev-2", "ups", "load_percent", 90.0, "%", quality="good")
    assert r1 is not None
    assert r2 is None  # 窗口内重复 -> 收敛
    print("[PASS] test_alarm_convergence")


def test_alarm_suppression():
    """设备抑制: 维护期间屏蔽告警"""
    alarm_engine.clear_all()
    alarm_engine.suppress_device("dev-3", True)
    r = alarm_engine.evaluate("dev-3", "chiller", "supply_temp", 16.0, "degC", quality="good")
    assert r is None
    alarm_engine.suppress_device("dev-3", False)
    r2 = alarm_engine.evaluate("dev-3", "chiller", "supply_temp", 16.0, "degC", quality="good")
    assert r2 is not None
    print("[PASS] test_alarm_suppression")


def test_alarm_get_active():
    alarm_engine.clear_all()
    alarm_engine.evaluate("dev-4", "chiller", "supply_temp", 16.0, "degC", quality="good")
    active = alarm_engine.get_active_alarms()
    assert len(active) >= 1
    print(f"[PASS] test_alarm_get_active ({len(active)} active)")


def test_alarm_unknown_category():
    """未配置规则的设备类别不触发告警"""
    alarm_engine.clear_all()
    r = alarm_engine.evaluate("dev-9", "unknown_cat", "temp", 100.0, "degC", quality="good")
    assert r is None
    print("[PASS] test_alarm_unknown_category")


def test_alarm_bad_quality_skip():
    """质量差的数据点跳过告警"""
    alarm_engine.clear_all()
    r = alarm_engine.evaluate("dev-1", "chiller", "supply_temp", 16.0, "degC", quality="bad")
    assert r is None
    print("[PASS] test_alarm_bad_quality_skip")


def test_alarm_critical_threshold():
    """临界阈值触发 crit 级别 (supply_temp crit.lo=2)"""
    alarm_engine.clear_all()
    r = alarm_engine.evaluate("dev-1", "chiller", "supply_temp", 0.5, "degC", quality="good")
    assert r is not None
    assert r["level"] == "crit"
    print(f"[PASS] test_alarm_critical_threshold (level={r['level']})")


def test_evaluate_batch():
    """批量评估 (逐条 evaluate 的便捷封装)"""
    alarm_engine.clear_all()
    points = [
        {"device_id": "d1", "category": "chiller", "metric_name": "supply_temp", "value": 16.0, "unit": "degC", "quality": "good"},
        {"device_id": "d2", "category": "chiller", "metric_name": "supply_temp", "value": 8.0, "unit": "degC", "quality": "good"},
        {"device_id": "d3", "category": "ups", "metric_name": "load_percent", "value": 92.0, "unit": "%", "quality": "good"},
    ]
    alarms = [p for p in (alarm_engine.evaluate(**point) for point in points) if p is not None]
    assert len(alarms) == 2  # d1 和 d3 触发, d2 为正常值
    print(f"[PASS] test_evaluate_batch ({len(alarms)} alarms from {len(points)} points)")


# ---- WebSocket 广播器 ----
import asyncio
from app.services import ws_broadcaster


async def test_ws_broadcaster_setup():
    ws_broadcaster.setup_alarm_notify()
    assert len(ws_broadcaster._connections) == 0
    print("[PASS] test_ws_broadcaster_setup")


# ---- 依赖注入 (deps.py) 导入检查 ----
from app.core.deps import RoleChecker, PermissionChecker, require_role, require_permission


def test_deps_imports():
    checker1 = RoleChecker("admin")
    checker2 = PermissionChecker("alarm:write")
    assert checker1 is not None
    assert checker2 is not None
    assert require_role("admin") is not None
    assert require_permission("alarm:write") is not None
    print("[PASS] test_deps_imports")


# ---- Schemas 导入检查 ----
from app.schemas.auth import LoginRequest


def test_schemas_imports():
    req = LoginRequest(username="admin", password="admin123")
    assert req.username == "admin"
    assert req.password == "admin123"
    print("[PASS] test_schemas_imports")


# ---- Run all ----
if __name__ == "__main__":
    print("=== Phase 2 Core Tests ===\n")

    print("-- Security --")
    test_password()
    test_access_token()
    test_refresh_token()
    test_token_types()
    test_invalid_token()

    print("\n-- Alarm Engine --")
    test_alarm_evaluate_normal()
    test_alarm_evaluate_high()
    test_alarm_evaluate_low()
    test_alarm_convergence()
    test_alarm_suppression()
    test_alarm_get_active()
    test_alarm_unknown_category()
    test_alarm_bad_quality_skip()
    test_alarm_critical_threshold()
    test_evaluate_batch()

    print("\n-- WebSocket Broadcaster --")
    asyncio.run(test_ws_broadcaster_setup())

    print("\n-- Dependencies & Schemas --")
    test_deps_imports()
    test_schemas_imports()

    print("\n=== All Phase 2 core tests passed! ===")
