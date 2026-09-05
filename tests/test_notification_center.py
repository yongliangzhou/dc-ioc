"""统一告警触达中心测试: crud / 路由 / 静默 / 去重 / 重试 / 端点。"""
import pytest

from app.api.v1.endpoints import notification as notif_ep
from app.crud import notification as notif_crud
from app.services import notification_service as svc
from conftest import FakeUser, make_client, make_sqlite_sessionmaker

_CHANNEL_DDL = """
CREATE TABLE IF NOT EXISTS notification_channel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT,
    min_level TEXT NOT NULL DEFAULT 'crit',
    quiet_start TEXT,
    quiet_end TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    updated_by TEXT DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""
_RECORD_DDL = """
CREATE TABLE IF NOT EXISTS notification_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alarm_id TEXT,
    channel_id INTEGER NOT NULL,
    channel_name TEXT,
    level TEXT NOT NULL,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'sent',
    error TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


@pytest.fixture()
def notif_db(monkeypatch):
    SessionLocal = make_sqlite_sessionmaker(pre_ddl=_CHANNEL_DDL + ";" + _RECORD_DDL)
    monkeypatch.setattr(notif_ep, "SessionLocal", SessionLocal)
    monkeypatch.setattr("app.db.session.SessionLocal", SessionLocal)
    return SessionLocal


@pytest.fixture()
def client(notif_db):
    return make_client([(notif_ep.router, "/api/ops")])


# ------------------------------------------------------------------ #
# crud / 纯函数
# ------------------------------------------------------------------ #
def test_level_routing(notif_db):
    assert notif_crud.level_at_least("crit", "crit") is True
    assert notif_crud.level_at_least("warn", "crit") is False   # warn 达不到 crit 通道
    assert notif_crud.level_at_least("crit", "warn") is True    # crit 可进 warn 通道
    assert notif_crud.level_at_least("info", "info") is True
    assert notif_crud.level_at_least("warn", "info") is True


def test_quiet_window():
    from datetime import datetime

    ch = {"quietStart": "22:00", "quietEnd": "07:00"}  # 跨零点
    assert svc._in_quiet_window(ch, datetime(2026, 9, 6, 23, 0)) is True
    assert svc._in_quiet_window(ch, datetime(2026, 9, 6, 3, 0)) is True
    assert svc._in_quiet_window(ch, datetime(2026, 9, 6, 12, 0)) is False
    ch2 = {"quietStart": "12:00", "quietEnd": "14:00"}  # 常规窗口
    assert svc._in_quiet_window(ch2, datetime(2026, 9, 6, 13, 0)) is True
    assert svc._in_quiet_window(ch2, datetime(2026, 9, 6, 15, 0)) is False
    assert svc._in_quiet_window({}, datetime(2026, 9, 6, 13, 0)) is False  # 未配置不静默


def test_deliver_retry_then_success(notif_db, monkeypatch):
    calls = {"n": 0}

    def flaky(url, payload):
        calls["n"] += 1
        if calls["n"] < 3:
            return False, "HTTP 500"
        return True, ""

    monkeypatch.setattr(svc, "_post_once", flaky)
    ch = {"id": 1, "name": "钉钉", "type": "dingtalk", "url": "https://hook.test/x"}
    status, err, retries = svc.deliver(ch, {"level": "crit", "device_id": "d", "metric_name": "m", "value": 1})
    assert status == "sent" and retries == 2 and calls["n"] == 3


def test_deliver_exhausted_retries(notif_db, monkeypatch):
    monkeypatch.setattr(svc, "_post_once", lambda url, payload: (False, "HTTP 500"))
    ch = {"id": 1, "name": "钉钉", "type": "dingtalk", "url": "https://hook.test/x"}
    status, err, retries = svc.deliver(ch, {"level": "crit"})
    assert status == "failed" and retries == svc.RETRY_MAX and "500" in err


def test_channel_without_url_fails_fast(notif_db):
    status, err, retries = svc.deliver({"id": 1, "name": "x", "type": "custom", "url": ""}, {"level": "crit"})
    assert status == "failed" and "URL" in err and retries == 0


# ------------------------------------------------------------------ #
# 路由层 dispatch_sync (mock crud 读写)
# ------------------------------------------------------------------ #
@pytest.fixture()
def route_env(monkeypatch):
    """替换 crud 读写为内存假体, 并捕获 create_record 调用。"""
    records: list[dict] = []
    seen_alarm_channel: set = set()

    _channels = [
        {"id": 1, "name": "crit 通道", "type": "dingtalk", "url": "u1", "minLevel": "crit", "enabled": True,
         "quietStart": None, "quietEnd": None},
        {"id": 2, "name": "info 通道", "type": "email", "url": "u2", "minLevel": "info", "enabled": True,
         "quietStart": "00:00", "quietEnd": "23:59"},  # 永久静默
        {"id": 3, "name": "停用通道", "type": "custom", "url": "u3", "minLevel": "info", "enabled": False},
    ]

    def fake_list_channels(db, enabled_only=False):
        return [c for c in _channels if c["enabled"]] if enabled_only else _channels

    monkeypatch.setattr(notif_crud, "list_channels", fake_list_channels)
    monkeypatch.setattr(notif_crud, "is_duplicated",
                        lambda db, alarm_id, cid, w=10: (alarm_id, cid) in seen_alarm_channel)
    monkeypatch.setattr(notif_crud, "create_record",
                        lambda db, data: records.append(data) or {"id": len(records)})
    monkeypatch.setattr(svc, "deliver",
                        lambda ch, alarm: ("sent", "", 0))
    return {"records": records, "seen": seen_alarm_channel}


def test_dispatch_routes_by_level(notif_db, route_env, monkeypatch):
    monkeypatch.setattr("app.db.session.SessionLocal", notif_db)
    alarm = {"alarm_id": "A1", "level": "crit", "device_id": "d", "metric_name": "m", "value": 1, "unit": ""}
    svc.dispatch_sync(alarm)
    st = {(r["channel_id"], r["status"]) for r in route_env["records"]}
    assert (1, "sent") in st          # crit 通道收到 crit
    assert (2, "muted") in st         # info 通道收到 crit 但处于静默窗口 → muted 留痕
    assert all(r["channel_id"] != 3 for r in route_env["records"])  # 停用通道不出现


def test_dispatch_dedup_second_round(notif_db, route_env, monkeypatch):
    monkeypatch.setattr("app.db.session.SessionLocal", notif_db)
    alarm = {"alarm_id": "A2", "level": "crit", "device_id": "d", "metric_name": "m", "value": 1, "unit": ""}
    svc.dispatch_sync(alarm)
    first = [r for r in route_env["records"] if r["channel_id"] == 1]
    assert first and first[0]["status"] == "sent"
    # 去重落库逻辑: 第一次 sent 后, is_duplicated 假体由测试侧标记
    route_env["seen"].add(("A2", 1))
    svc.dispatch_sync(alarm)
    second = [r for r in route_env["records"] if r["channel_id"] == 1 and r.get("status") == "dedup"]
    assert second, "第二次同告警同通道应记 dedup 留痕"


# ------------------------------------------------------------------ #
# 端点 (SQLite 真实落库)
# ------------------------------------------------------------------ #
def test_channel_crud_endpoints(client):
    r = client.get("/api/ops/notifications/channels")
    assert r.status_code == 200 and r.json() == []

    r2 = client.post("/api/ops/notifications/channels",
                     json={"type": "dingtalk", "name": "值班钉钉群", "url": "https://hook/x",
                           "minLevel": "crit", "enabled": True})
    assert r2.status_code == 200
    cid = r2.json()["id"]

    r3 = client.put(f"/api/ops/notifications/channels/{cid}", json={"minLevel": "warn", "enabled": False})
    assert r3.status_code == 200 and r3.json()["minLevel"] == "warn" and r3.json()["enabled"] is False

    # 写权限
    viewer = make_client([(notif_ep.router, "/api/ops")], user=FakeUser(roles=("viewer",)))
    assert viewer.post("/api/ops/notifications/channels", json={"type": "custom", "name": "x"}).status_code == 403
    assert viewer.delete(f"/api/ops/notifications/channels/{cid}").status_code == 403

    assert client.delete(f"/api/ops/notifications/channels/{cid}").json()["deleted"] is True
    assert client.delete(f"/api/ops/notifications/channels/{cid}").status_code == 404


def test_test_send_endpoint(client):
    cid = client.post("/api/ops/notifications/channels",
                      json={"type": "custom", "name": "网关", "url": "https://hook/test"}).json()["id"]
    monkeypatched = svc.deliver
    # URL 不可达 → failed 但端点本身 200 (结果在 body 与记录里)
    r = client.post("/api/ops/notifications/test", json={"channelId": cid, "title": "t", "message": "m"})
    assert r.status_code == 200
    assert r.json()["channelId"] == cid
    assert r.json()["status"] in ("sent", "failed")
    # 记录留痕 (含失败)
    recs = client.get("/api/ops/notifications/records", params={"channelId": cid}).json()
    assert recs["total"] >= 1
    # 停用通道测试 → 400
    client.put(f"/api/ops/notifications/channels/{cid}", json={"enabled": False})
    assert client.post("/api/ops/notifications/test", json={"channelId": cid}).status_code == 400
    # 不存在的通道 → 404
    assert client.post("/api/ops/notifications/test", json={"channelId": 9999}).status_code == 404
