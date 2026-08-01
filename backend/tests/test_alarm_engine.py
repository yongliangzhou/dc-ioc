"""(纯内存, 无需数据库) 告警引擎单元测试。

覆盖阈值判定 (warn/crit 双向)、收敛去重、抑制 (设备维保/离线)、
规则启停、确认/关单、升级 (服务端计数器) 等核心逻辑。

注意: 阈值以 app.services.alarm_engine.DEFAULT_RULES 为准, 例如
chiller.supply_temp 的 warn/crit 上限分别为 15 / 18, 下限分别为 5 / 2。
"""
import time

import pytest

from app.services import alarm_engine as eng


@pytest.fixture(autouse=True)
def _reset():
    eng.clear_all()
    eng._disabled_rules.clear()
    eng._suppressed_devices.clear()
    yield
    eng.clear_all()
    eng._disabled_rules.clear()
    eng._suppressed_devices.clear()


# ---------------- 阈值判定 ----------------

def test_evaluate_normal_no_alarm():
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 7.5) is None


def test_evaluate_warn_high():
    # supply_temp warn.hi = 15
    a = eng.evaluate("CH-01", "chiller", "supply_temp", 16.0)
    assert a is not None and a["level"] == "warn"
    assert a["value"] == 16.0


def test_evaluate_crit_high_priority_over_warn():
    # supply_temp crit.hi = 18
    a = eng.evaluate("CH-01", "chiller", "supply_temp", 19.0)
    assert a is not None and a["level"] == "crit"


def test_evaluate_warn_low_and_crit_low():
    # return_temp warn.lo = 10, crit.lo = 5
    w = eng.evaluate("CH-01", "chiller", "return_temp", 8.0)
    assert w is not None and w["level"] == "warn"
    c = eng.evaluate("CH-02", "chiller", "return_temp", 4.0)
    assert c is not None and c["level"] == "crit"


def test_evaluate_unknown_category_or_metric():
    assert eng.evaluate("X", "no_such_cat", "supply_temp", 99) is None
    assert eng.evaluate("CH-01", "chiller", "no_such_metric", 99) is None


def test_bad_quality_skipped():
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 16.0, quality="bad") is None


# ---------------- 收敛去重 ----------------

def test_convergence_dedup():
    a1 = eng.evaluate("CH-01", "chiller", "supply_temp", 16.0)
    a2 = eng.evaluate("CH-01", "chiller", "supply_temp", 16.5)  # 窗口内重复 -> 收敛为 None
    assert a1 is not None
    assert a2 is None
    active = [a for a in eng.get_active_alarms() if a["device_id"] == "CH-01"]
    assert len(active) == 1


def test_different_level_not_converged():
    eng.evaluate("CH-01", "chiller", "supply_temp", 16.0)  # warn
    c = eng.evaluate("CH-01", "chiller", "supply_temp", 19.0)  # crit 独立桶, 不收敛
    assert c is not None and c["level"] == "crit"


# ---------------- 抑制 / 启停 ----------------

def test_suppress_device():
    eng.suppress_device("CH-01", True)
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 19.0) is None
    eng.suppress_device("CH-01", False)
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 19.0) is not None


def test_silenced_rule_skipped():
    eng.set_rule_status("chiller:supply_temp", "disabled")
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 19.0) is None
    eng.set_rule_status("chiller:supply_temp", "enabled")
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 19.0) is not None


# ---------------- 确认 / 关单 ----------------

def test_ack_and_resolve():
    a = eng.evaluate("CH-01", "chiller", "supply_temp", 16.0)
    key = a["alarm_id"]
    assert eng.ack_alarm(key) is True
    active = eng.get_active_alarms()
    assert any(x["alarm_id"] == key and x["ack_state"] == "已确认" for x in active)
    assert eng.resolve_alarm(key) is True
    assert all(x["alarm_id"] != key for x in eng.get_active_alarms())


# ---------------- 升级 (服务端计数器) ----------------

def test_escalation_after_window():
    eng.evaluate("CH-01", "chiller", "supply_temp", 16.0)  # warn
    key = "chiller:supply_temp:warn"
    assert key in eng._active_alarm_cache

    # 未到窗口: 不升级
    assert eng.check_escalations() == 0

    # 模拟时间推进超过升级窗口
    fake_now = time.time() + eng._ESCALATE_SEC + 1
    assert eng.check_escalations(now_ts=fake_now) == 1
    assert eng._active_alarm_cache[key]["level"] == "crit"
    # 幂等: 再次检查不重复升级
    assert eng.check_escalations(now_ts=fake_now + 10) == 0


def test_acked_warn_escalates_but_keeps_ack():
    eng.evaluate("CH-01", "chiller", "supply_temp", 16.0)
    key = "chiller:supply_temp:warn"
    eng.ack_alarm(key)
    fake_now = time.time() + eng._ESCALATE_SEC + 1
    assert eng.check_escalations(now_ts=fake_now) == 1
    alarm = eng._active_alarm_cache[key]
    assert alarm["level"] == "crit"
    assert alarm["ack_state"] == "已确认"


def test_crit_never_escalated():
    eng.evaluate("CH-01", "chiller", "supply_temp", 19.0)  # crit
    fake_now = time.time() + eng._ESCALATE_SEC * 2
    assert eng.check_escalations(now_ts=fake_now) == 0


# ---------------- 规则 DTO / 状态 ----------------

def test_list_rules_and_state():
    rules = eng.list_rules()
    assert len(rules) > 0
    assert all("rule_id" in r and "enabled" in r for r in rules)
    st = eng.engine_state()
    assert "active_alarms" in st
    assert st["convergence_sec"] == eng._CONVERGENCE_SEC
    assert st["escalate_sec"] == eng._ESCALATE_SEC
