"""阶段三测试: 纯函数 (IPAM/发现/商务/自定义字段) + 端点最小闭环。"""
import pytest

from app.api.v1.endpoints import p3 as ep
from app.models import p3 as m
from app.services import p3_services as svc
from conftest import FakeUser, make_client, make_sqlite_sessionmaker

IPAM = "/api/ipam"
DISCOVERY = "/api/ops/discovery"
PROCUREMENT = "/api/ops/procurement"
STOCKTAKE = "/api/ops/stocktake"
CUSTOM = "/api/ops/custom-fields"


@pytest.fixture()
def db_factory(monkeypatch):
    SessionLocal = make_sqlite_sessionmaker(*[t.__table__ for t in (
        m.IpVlan, m.IpSubnet, m.IpAddress, m.DiscoveryCandidate,
        m.PurchaseOrder, m.StocktakeTask, m.StocktakeItem, m.CustomFieldDef,
    )])
    monkeypatch.setattr(ep, "SessionLocal", SessionLocal)
    return SessionLocal


@pytest.fixture()
def client(db_factory):
    return make_client([
        (ep.ipam_router, IPAM),
        (ep.discovery_router, DISCOVERY),
        (ep.procurement_router, PROCUREMENT),
        (ep.stocktake_router, STOCKTAKE),
        (ep.custom_field_router, CUSTOM),
    ])


# ------------------------------------------------------------------ #
# 纯函数
# ------------------------------------------------------------------ #
def test_subnet_stats_and_next_available():
    stats = svc.subnet_stats("192.168.1.0/30", ["192.168.1.1"])
    assert stats["total"] == 2 and stats["used"] == 1
    assert stats["utilization_pct"] == 50.0
    assert svc.next_available("192.168.1.0/30", ["192.168.1.1"]) == "192.168.1.2"
    assert svc.next_available("192.168.1.0/30", ["192.168.1.1", "192.168.1.2"]) is None


def test_subnet_stats_ipv6_prefix():
    stats = svc.subnet_stats("2001:db8::/126", [])
    assert stats["total"] == 4


def test_scan_cidr_security_boundary():
    assert svc.validate_scan_cidr("192.168.1.0/30")
    with pytest.raises(svc.ValidationError):
        svc.validate_scan_cidr("8.8.8.0/24")  # 公网
    with pytest.raises(svc.ValidationError):
        svc.validate_scan_cidr("10.0.0.0/16")  # 过大
    with pytest.raises(svc.ValidationError):
        svc.validate_scan_cidr("not-a-cidr")


def test_expiring_orders_and_stocktake_report():
    from datetime import date, timedelta

    soon = (date.today() + timedelta(days=5)).isoformat()
    rows = [
        {"order_no": "PO-1", "warranty_until": soon},
        {"order_no": "PO-2", "warranty_until": "2000-01-01"},
        {"order_no": "PO-3", "warranty_until": ""},
    ]
    out = svc.expiring_orders(rows, 30)
    assert [r["order_no"] for r in out] == ["PO-2", "PO-1"]
    assert out[0]["expired"] is True

    report = svc.stocktake_report(
        [{"asset_ci": "a", "result": "matched"}, {"asset_ci": "z", "result": "unexpected"}],
        ["a", "b"],
    )
    assert report["matched"] == 1
    assert report["missing"] == ["b"]
    assert report["unexpected"] == ["z"]
    assert report["coverage_pct"] == 50.0


def test_custom_value_validation():
    defs = [
        {"key": "rack_color", "type": "select", "options": ["black", "blue"], "required": True},
        {"key": "power_w", "type": "number", "options": [], "required": False},
        {"key": "buy_date", "type": "date", "options": [], "required": False},
    ]
    ok = svc.validate_custom_values(defs, {"rack_color": "blue", "power_w": "12.5", "buy_date": "2026-01-02"})
    assert ok == {"rack_color": "blue", "power_w": 12.5, "buy_date": "2026-01-02"}
    with pytest.raises(svc.ValidationError):
        svc.validate_custom_values(defs, {"unknown": "x"})
    with pytest.raises(svc.ValidationError):
        svc.validate_custom_values(defs, {"rack_color": "red"})
    with pytest.raises(svc.ValidationError):
        svc.validate_custom_values(defs, {"power_w": "abc"})
    with pytest.raises(svc.ValidationError):
        svc.validate_custom_values(defs, {"rack_color": "blue", "buy_date": "bad-date"})


# ------------------------------------------------------------------ #
# IPAM 端点
# ------------------------------------------------------------------ #
def test_ipam_full_closure(client):
    assert client.post(f"{IPAM}/vlans", json={"vlan_id": 100, "name": "MGMT"}).status_code == 200
    assert client.post(f"{IPAM}/vlans", json={"vlan_id": 100}).status_code == 409
    sub = client.post(f"{IPAM}/subnets", json={"cidr": "192.168.1.0/30", "vlan_id": 100}).json()
    assert sub["cidr"] == "192.168.1.0/30"
    subs = client.get(f"{IPAM}/subnets").json()
    assert subs[0]["total"] == 2 and subs[0]["utilization_pct"] == 0.0
    nxt = client.get(f"{IPAM}/subnets/{sub['id']}/next-available").json()
    assert nxt["address"] == "192.168.1.1"
    allocated = client.post(f"{IPAM}/subnets/{sub['id']}/allocate", params={"device_ci": "equipment:1"})
    assert allocated.status_code == 200 and allocated.json()["address"] == "192.168.1.1"
    assert client.post(f"{IPAM}/subnets", json={"cidr": "bad-cidr"}).status_code == 422
    stats = client.get(f"{IPAM}/stats").json()
    assert stats["vlans"] == 1 and stats["subnets"] == 1 and stats["allocated"] == 1


def test_ipam_write_requires_role(client):
    viewer = make_client([(ep.ipam_router, IPAM)], user=FakeUser(roles=("viewer",)))
    assert viewer.post(f"{IPAM}/vlans", json={"vlan_id": 200}).status_code == 403


# ------------------------------------------------------------------ #
# 自动发现端点
# ------------------------------------------------------------------ #
def test_scan_disabled_by_default(client, monkeypatch):
    monkeypatch.setattr(ep, "_discovery_enabled", lambda: False)
    assert client.post(f"{DISCOVERY}/scan", json={"cidr": "192.168.1.0/30"}).status_code == 403


def test_scan_and_confirm_staging(client, monkeypatch):
    monkeypatch.setattr(ep, "_discovery_enabled", lambda: True)

    async def fake_scan(cidr, ports, concurrency=50):
        return [{"ip": "192.168.1.1", "hostname": "", "mac": "", "open_ports": [80]}]

    monkeypatch.setattr(svc, "scan_subnet", fake_scan)
    r = client.post(f"{DISCOVERY}/scan", json={"cidr": "192.168.1.0/30", "ports": [80]})
    assert r.status_code == 200 and r.json()["created"] == 1
    rows = client.get(f"{DISCOVERY}/candidates", params={"status": "pending"}).json()
    assert len(rows) == 1 and rows[0]["status"] == "pending"

    cid = rows[0]["id"]
    confirmed = client.post(f"{DISCOVERY}/candidates/{cid}/confirm", json={"matched_ci": "cabinet:A01"})
    assert confirmed.json()["status"] == "confirmed"
    assert confirmed.json()["matched_ci"] == "cabinet:A01"
    assert client.post(f"{DISCOVERY}/candidates/{cid}/reject").status_code == 409  # 幂等保护
    assert client.get(f"{DISCOVERY}/candidates", params={"status": "pending"}).json() == []


def test_scan_rejects_public_cidr(client, monkeypatch):
    monkeypatch.setattr(ep, "_discovery_enabled", lambda: True)
    assert client.post(f"{DISCOVERY}/scan", json={"cidr": "8.8.8.0/24"}).status_code == 400


# ------------------------------------------------------------------ #
# 采购 / 盘点端点
# ------------------------------------------------------------------ #
def test_procurement_and_stocktake(client):
    from datetime import date, timedelta

    soon = (date.today() + timedelta(days=3)).isoformat()
    assert client.post(f"{PROCUREMENT}/orders", json={
        "order_no": "PO-001", "vendor": "ACME", "warranty_until": soon, "amount": 1000,
    }).status_code == 200
    expiring = client.get(f"{PROCUREMENT}/expiring", params={"days": 30}).json()
    assert len(expiring) == 1 and expiring[0]["order_no"] == "PO-001"

    task = client.post(f"{STOCKTAKE}/tasks", json={"name": "Q4 盘点", "scope": "A 区"}).json()
    tid = task["id"]
    client.post(f"{STOCKTAKE}/tasks/{tid}/items", json={"asset_ci": "a", "result": "matched"})
    client.post(f"{STOCKTAKE}/tasks/{tid}/items", json={"asset_ci": "z", "result": "unexpected"})
    report = client.get(f"{STOCKTAKE}/tasks/{tid}/report", params={"expected_cis": "a,b"}).json()
    assert report["matched"] == 1 and report["missing"] == ["b"] and report["unexpected"] == ["z"]


# ------------------------------------------------------------------ #
# 自定义字段端点
# ------------------------------------------------------------------ #
def test_custom_field_definition_crud(client):
    r = client.post(CUSTOM, json={
        "key": "rack_color", "label_zh": "机柜颜色", "type": "select",
        "options": ["black", "blue"], "required": True,
    })
    assert r.status_code == 200
    assert client.post(CUSTOM, json={"key": "rack_color", "label_zh": "重复"}).status_code == 409
    assert client.post(CUSTOM, json={"key": "Bad-Key", "label_zh": "非法"}).status_code == 422
    defs = client.get(CUSTOM).json()
    assert len(defs) == 1 and defs[0]["key"] == "rack_color"
    assert client.delete(f"{CUSTOM}/{defs[0]['id']}").status_code == 200
