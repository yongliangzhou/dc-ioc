"""告警→工单自动桥测试: 级别过滤 / 幂等 / 回写 / SQLite 真实建单。"""
import pytest

from app.core.config import settings
from app.crud import ticket as ticket_crud
from app.models.ticket import Ticket
from app.services import alarm_ticket_bridge as bridge


@pytest.fixture(autouse=True)
def _enable(monkeypatch):
    monkeypatch.setattr(settings, "ALARM_AUTO_TICKET_ENABLED", True)
    monkeypatch.setattr(settings, "ALARM_AUTO_TICKET_MIN_LEVEL", "crit")


def _alarm(level="crit", alarm_id="chiller:supply_temp:crit", **kw):
    d = {"alarm_id": alarm_id, "level": level, "device_id": "CH-01", "category": "chiller",
         "metric_name": "supply_temp", "value": 15, "unit": "℃", "rule_id": "R1"}
    d.update(kw)
    return d


@pytest.fixture()
def sqlite_tickets(monkeypatch):
    """Ticket 模型为纯通用类型 (String PK + JSON 列), SQLite 可直接建表。"""
    SessionLocal = make_sqlite_sessionmaker(Ticket.__table__)
    monkeypatch.setattr("app.db.session.SessionLocal", SessionLocal)
    return SessionLocal


@pytest.fixture()
def no_ack(monkeypatch):
    """ack_alarm 写穿引擎态需要真实引擎内存态, 测试中打桩。"""
    calls = {"ack": []}
    monkeypatch.setattr("app.services.alarm_engine.ack_alarm", lambda aid: calls["ack"].append(aid) or True)
    return calls


# conftest 里 make_sqlite_sessionmaker 已由 sys.path 注入后可用
from conftest import make_sqlite_sessionmaker  # noqa: E402


def test_level_below_min_skipped(sqlite_tickets, no_ack, monkeypatch):
    created = []
    monkeypatch.setattr(ticket_crud, "create_ticket", lambda *a, **k: created.append(k) or None)
    bridge.auto_ticket_handler(_alarm(level="warn"))  # warn < crit
    assert created == []


def test_disabled_skipped(sqlite_tickets, no_ack, monkeypatch):
    monkeypatch.setattr(settings, "ALARM_AUTO_TICKET_ENABLED", False)
    created = []
    monkeypatch.setattr(ticket_crud, "create_ticket", lambda *a, **k: created.append(k) or None)
    bridge.auto_ticket_handler(_alarm())
    assert created == []


def test_idempotent_when_open_ticket_exists(sqlite_tickets, no_ack, monkeypatch):
    created = []
    monkeypatch.setattr(ticket_crud, "create_ticket", lambda *a, **k: created.append(k) or None)
    # 该告警已有未关单工单 → 跳过
    monkeypatch.setattr(ticket_crud, "find_open_by_alarm", lambda db, aid: object())
    bridge.auto_ticket_handler(_alarm())
    assert created == []


def test_auto_creates_ticket_and_acks(sqlite_tickets, no_ack):
    db = sqlite_tickets()
    try:
        bridge.auto_ticket_handler(_alarm())
        t = ticket_crud.find_open_by_alarm(db, "chiller:supply_temp:crit")
        assert t is not None
        assert t.source == "auto-alarm" and t.source_alarm_id == "chiller:supply_temp:crit"
        assert t.lv == "crit" and t.state == "open"
        assert t.sla == "1h" and t.owner == "待分配"
        assert "[自动工单]" in t.title
        assert no_ack["ack"] == ["chiller:supply_temp:crit"]
        # 再次通知 → 幂等跳过 (真实 crud 查询路径)
        before = db.query(Ticket).count()
        bridge.auto_ticket_handler(_alarm())
        assert db.query(Ticket).count() == before
    finally:
        db.close()


def test_level_at_min_boundary_creates(sqlite_tickets, no_ack):
    db = sqlite_tickets()
    try:
        bridge.auto_ticket_handler(_alarm(level="crit", alarm_id="chiller:x:crit"))
        assert ticket_crud.find_open_by_alarm(db, "chiller:x:crit") is not None
    finally:
        db.close()


def test_create_failure_swallowed(sqlite_tickets, no_ack, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr(ticket_crud, "create_ticket", boom)
    # 不抛异常即通过 (告警主链路不受建单失败影响)
    bridge.auto_ticket_handler(_alarm(alarm_id="chiller:y:crit"))


# ------------------------------------------------------------------ #
# find_open_by_alarm 真实 CRUD 语义 (含终态过滤)
# ------------------------------------------------------------------ #
def test_find_open_by_alarm_filters_closed_states(sqlite_tickets):
    db = sqlite_tickets()
    try:
        t1 = ticket_crud.create_ticket(db, title="t1", sys="暖通空调", lv="crit", owner="待分配",
                                       source="auto-alarm", source_alarm_id="A-100")
        # 已关单 → find_open 应返回 None
        ticket_crud.transition_ticket(db, t1.id, "done", "tester", "处理完成")
        assert ticket_crud.find_open_by_alarm(db, "A-100") is None
        # 新告警建第二张单 → 可查到
        ticket_crud.create_ticket(db, title="t2", sys="暖通空调", lv="crit", owner="待分配",
                                  source="auto-alarm", source_alarm_id="A-101")
        found = ticket_crud.find_open_by_alarm(db, "A-101")
        assert found is not None and found.title == "t2"
    finally:
        db.close()
