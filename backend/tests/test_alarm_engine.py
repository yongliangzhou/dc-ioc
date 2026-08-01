"""告警引擎单元测试 (纯内存, 无需数据库)。

覆盖原前端 alarmEngine.ts 迁移到后端的判定逻辑:
- 阈值判定 (warn/crit 双向)
- 收敛去重 (CONVERGENCE_WINDOW_SEC)
- 抑制 (设备维保/离线)
- 规则启停 (silenced)
- 升级 (ESCALATE_AFTER_SEC, 服务端计数器不随客户端刷新丢失)
"""
import time

import pytest

from app.services import alarm_engine as eng


@pytest.fixture(autouse=True)
def _reset():
    eng.clear_all()
    eng._disabled_rules.clear()
    yield
    eng.clear_all()
    eng._disabled_rules.clear()


# ---------------- 阈值判定 ----------------

def test_evaluate_normal_no_alarm():
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 7.5) is None


def test_evaluate_warn_high():
    a = eng.evaluate("CH-01", "chiller", "supply_temp", 11.0)
    assert a is not None and a["level"] == "warn"
    assert a["threshold"] == 10.0


def test_evaluate_crit_high_priority_over_warn():
    a = eng.evaluate("CH-01", "chiller", "supply_temp", 13.0)
    assert a is not None and a["level"] == "crit"
    assert a["threshold"] == 12.0


def test_evaluate_warn_low_and_crit_low():
    w = eng.evaluate("CH-01", "chiller", "cop", 4.5)
    assert w is not None and w["level"] == "warn"
    c = eng.evaluate("CH-02", "chiller", "cop", 3.5)
    assert c is not None and c["level"] == "crit"


def test_evaluate_unknown_category_or_metric():
    assert eng.evaluate("X", "no_such_cat", "supply_temp", 99) is None
    assert eng.evaluate("CH-01", "chiller", "no_such_metric", 99) is None


def test_bad_quality_skipped():
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 13.0, quality="bad") is None


# ---------------- 收敛去重 ----------------

def test_convergence_dedup():
    a1 = eng.evaluate("CH-01", "chiller", "supply_temp", 11.0)
    a2 = eng.evaluate("CH-01", "chiller", "supply_temp", 11.2)
    assert a1["is_converged"] is False
    assert a2["is_converged"] is True  # 窗口内重复 -> 收敛
    # 活跃告警仅一条
    active = [a for a in eng.get_active_alarms() if a["device_id"] == "CH-01"]
    assert len(active) == 1


def test_different_level_not_converged():
    eng.evaluate("CH-01", "chiller", "supply_temp", 11.0)   # warn
    c = eng.evaluate("CH-01", "chiller", "supply_temp", 13.0)  # crit 独立 key
    assert c["is_converged"] is False


# ---------------- 抑制 / 启停 ----------------

def test_suppress_device():
    eng.suppress_device("CH-01")
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 13.0) is None
    eng.unsuppress_device("CH-01")
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 13.0) is not None


def test_silenced_rule_skipped():
    eng.set_rule_status("chiller:supply_temp", "silenced")
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 13.0) is None
    eng.set_rule_status("chiller:supply_temp", "enabled")
    assert eng.evaluate("CH-01", "chiller", "supply_temp", 13.0) is not None


# ---------------- 确认 / 关单 ----------------

def test_ack_and_resolve():
    a = eng.evaluate("CH-01", "chiller", "supply_temp", 11.0)
    key = f"CH-01:supply_temp:{a['level']}"
    assert eng.ack_alarm(key) is True
    active = eng.get_active_alarms()
    assert any(x["id"] == key and x["state"] == "已确认" for x in active)
    assert eng.resolve_alarm(key) is True
    assert all(x["id"] != key for x in eng.get_active_alarms())


# ---------------- 升级 (服务端计数器) ----------------

def test_escalation_after_window():
    eng.evaluate("CH-01", "chiller", "supply_temp", 11.0)  # warn
    key = "CH-01:supply_temp:warn"
    assert key in eng._active_alarm_cache

    # 未到窗口: 不升级
    assert eng.check_escalations() == []

    # 模拟时间推进超过升级窗口
    fake_now = time.time() + eng.ESCALATE_AFTER_SEC + 1
    escalated = eng.check_escalations(now_ts=fake_now)
    assert len(escalated) == 1
    assert escalated[0]["level"] == "crit"
    assert escalated[0]["escalated_from"] == key
    # warn 条目退场, crit 条目登记
    assert key not in eng._active_alarm_cache
    assert "CH-01:supply_temp:crit" in eng._active_alarm_cache
    # 幂等: 再次检查不重复升级
    assert eng.check_escalations(now_ts=fake_now + 10) == []


def test_acked_warn_not_escalated():
    eng.evaluate("CH-01", "chiller", "supply_temp", 11.0)
    key = "CH-01:supply_temp:warn"
    eng.ack_alarm(key)
    fake_now = time.time() + eng.ESCALATE_AFTER_SEC + 1
    assert eng.check_escalations(now_ts=fake_now) == []
    assert key in eng._active_alarm_cache  # 已确认: 保持 warn


def test_crit_never_escalated():
    eng.evaluate("CH-01", "chiller", "supply_temp", 13.0)  # crit
    fake_now = time.time() + eng.ESCALATE_AFTER_SEC * 2
    assert eng.check_escalations(now_ts=fake_now) == []


# ---------------- 规则 DTO / 状态 ----------------

def test_list_rules_and_state():
    rules = eng.list_rules()
    assert len(rules) > 0
    assert all("id" in r and "status" in r for r in rules)
    st = eng.engine_state()
    assert st["totalRules"] == len(rules)
    assert st["enabledCount"] + st["silencedCount"] == st["totalRules"]


def test_rules_aligned_with_thing_models():
    result = eng.validate_alignment()
    assert result["aligned"] is True, f"规则与物模型不对齐: {result}"
